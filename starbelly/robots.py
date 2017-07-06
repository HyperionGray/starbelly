import asyncio
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import aiohttp
import async_timeout
from dateutil.tz import tzlocal
import logging
from robotexclusionrulesparser import RobotExclusionRulesParser
import rethinkdb as r

from . import VERSION
from .downloader import DownloadRequest


logger = logging.getLogger(__name__)


class RobotsTxtManager:
    ''' Store and manage robots.txt files. '''
    def __init__(self, db_pool, rate_limiter, max_age=24*60*60, max_cache=1e3):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._cache = OrderedDict()
        self._rate_limiter = rate_limiter
        self._max_age = max_age
        self._max_cache = max_cache
        self._robots_futures = dict()
        self._user_agent = f'Starbelly {VERSION}'

    async def is_allowed(self, url, policy):
        '''
        Return True if ``url`` is allowed by the applicable robots.txt file.

        This fetches the applicable robots.txt if we don't have a recent copy
        of it cached in memory or in the database. The ``policy`` is used if a
        robots.txt file needs to be fetched from the network.
        '''

        robots_url = self._get_robots_url(url)

        # Check if cache has a current copy of robots.txt.
        if robots_url in self._cache:
            robots = self._cache[robots_url]
            if robots.is_older_than(self._max_age):
                robots = None
                del self._cache[robots_url]
            else:
                self._cache.move_to_end(robots_url)
        else:
            robots = None

        # If not in cache, get it from DB or network. _get_robots() will add
        # the object to the cache.
        if robots is None:
            robots = await self._get_robots(robots_url, policy)

        return robots.is_allowed(self._user_agent, url)

    async def _get_robots(self, robots_url, policy):
        '''
        Get a ``RobotsTxt`` that is applicable for ``url``.

        Looks for non-expired robots.txt file first in database then request
        from network. Wherever the robots file is found, it is placed into the
        cache and then returned.

        If we get a copy from the network, then we also store a copy in the
        database. If we cannot get a copy from the network (e.g. 404 error) and
        we have a database copy, then we update the database copy's expiration.
        If we cannot get a copy from database or network, then we create a
        permissive robots.txt and use that instead.
        '''

        # If another task is already fetching this robots file, then just wait
        # for it to finish.
        if robots_url in self._robots_futures:
            return await self._robots_futures[robots_url]

        # Otherwise, this task creates a future (for other tasks to use) and
        # then tries to locate a suitable RobotsTxt.
        robots_future = asyncio.Future()
        self._robots_futures[robots_url] = robots_future

        # Check DB. If not there (or expired), check network.
        now = datetime.now(tzlocal())
        robots_doc = await self._get_robots_from_db(robots_url)

        if robots_doc is None or \
            (now - robots_doc['updated_at']).seconds > self._max_age:

            robots_file = await self._get_robots_from_net(robots_url, policy)
        else:
            robots_file = None

        if robots_doc is None:
            # No local copy: create a new local copy. If robots_file is None, it
            # will be treated as a permissive RobotsTxt.
            logger.debug('Saving new robots.txt file: %s', robots_url)
            robots_doc = {
                'file': robots_file,
                'updated_at': now,
                'url': robots_url,
            }
            robots = RobotsTxt(robots_doc)
        else:
            # If we have a network copy, use that to update local copy.
            # Otherwise, just update the local copy's timestamp.
            robots = RobotsTxt(robots_doc)
            logger.debug('Updating robots.txt file: %s', robots_url)
            if robots_file is not None:
                robots_doc['file'] = robots_file
            else:
                del robots_doc['file']

            robots_doc['updated_at'] = now
            del robots_doc['url']

        # Upsert robots_docs.
        async with self._db_pool.connection() as conn:
            await (
                r.table('robots_txt')
                 .insert(robots_doc, conflict='update')
                 .run(conn)
            )

        # Enforce maximum cache size.
        if len(self._cache) == self._max_cache:
            self._cache.popitem(last=False)

        # Add to cache before completing the future to avoid race condition.
        self._cache[robots_url] = robots
        robots_future = self._robots_futures.pop(robots_url)
        robots_future.set_result(robots)
        return robots

    def _get_robots_url(self, url):
        '''
        Construct a robots.txt URL that is applicable for ``url``.

        This preserves scheme, hostname, and port. It changes the path to
        'robots.txt' and removes the query string and fragment.
        '''
        robots_url = urlparse(url)._replace(
            path='robots.txt',
            params=None,
            query=None,
            fragment=None
        )
        return urlunparse(robots_url)

    async def _get_robots_from_db(self, robots_url):
        '''
        Get robots document from the database.

        Returns None if it doesn't exist in the database.
        '''
        query = r.table('robots_txt').get_all(robots_url, index='url').nth(0)

        async with self._db_pool.connection() as conn:
            try:
                db_robots = await query.run(conn)
            except r.ReqlNonExistenceError:
                db_robots = None

        return db_robots

    async def _get_robots_from_net(self, robots_url, policy):
        '''
        Get robots.txt file from the network.

        Returns None if the file cannot be fetched (e.g. 404 error).
        '''

        logger.info('Fetching robots.txt: %s', robots_url)
        # Bit of a hack here to work with rate DownloadRequest API: create a
        # queue that we only use one time. This should really be one queue that
        # all tasks access through this instance.
        output_queue = asyncio.Queue()
        download_request = DownloadRequest(
            job_id='robots_txt',
            url=robots_url,
            cost=0,
            policy=policy,
            output_queue=output_queue
        )
        await self._rate_limiter.push(download_request)
        response = await output_queue.get()

        if response.status_code == 200 and response.body is not None:
            try:
                robots_file = response.body.decode('latin1')
            except UnicodeDecodeError as ude:
                logger.error('Robots.txt has invalid encoding: %s (%s)',
                    robots_url, ude)
                robots_file = None
        else:
            robots_file = None

        return robots_file


class RobotsTxt:
    '''
    Wrapper around robots.txt parser that adds the date the file was fetched.

    If the ``robots_file`` is None or cannot be parsed, then it's treated as a
    highly permissive robots.txt.
    '''
    def __init__(self, robots_doc):
        ''' Initialize from database document representation. '''
        self._updated_at = robots_doc['updated_at']
        self._robots = RobotExclusionRulesParser()

        if robots_doc['file'] is not None:
            try:
                self._robots.parse(robots_doc['file'])
            except:
                pass

    def is_allowed(self, user_agent, url):
        ''' Return True if ``url`` is allowed by this robots.txt file. '''
        return self._robots.is_allowed(user_agent, url)

    def is_older_than(self, age):
        ''' Return True if this robots file is older than ``age``. '''
        return (datetime.now(tzlocal()) - self._updated_at).seconds > age
