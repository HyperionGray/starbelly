from collections import OrderedDict
from datetime import datetime, timezone
import logging

from robotexclusionrulesparser import RobotExclusionRulesParser
from rethinkdb import RethinkDB
from yarl import URL
import trio

from .downloader import DownloadRequest


r = RethinkDB()
logger = logging.getLogger(__name__)


class RobotsTxtManager:
    ''' Store and manage robots.txt files. '''
    def __init__(self, db_pool, max_age=24*60*60, max_cache=1e3):
        '''
        Constructor.

        :param db_pool: A DB connection pool.
        :param int max_age: The maximum age before a robots.txt is downloaded
            again.
        :param int max_cache: The maximum number of robots.txt files to cache
            in memory.
        '''
        self._db_pool = db_pool
        self._events = dict()
        self._cache = OrderedDict()
        self._max_age = max_age
        self._max_cache = max_cache

    async def is_allowed(self, url, policy, downloader):
        '''
        Return True if ``url`` is allowed by the applicable robots.txt file.

        This fetches the applicable robots.txt if we don't have a recent copy
        of it cached in memory or in the database. The ``policy`` is used if a
        robots.txt file needs to be fetched from the network.

        :param str url: Check this URL to see if the robots.txt and accompanying
            policy permit access to it.
        :param Policy policy:
        :param Downloader downloader:
        :rtype: bool
        '''
        if policy.robots_txt.usage == 'IGNORE':
            # No need to fetch robots.txt.
            return True

        robots_url = str(URL(url).with_path('robots.txt')
                                 .with_query(None)
                                 .with_fragment(None))

        # Check if cache has a current copy of robots.txt.
        try:
            robots = self._cache[robots_url]
            if robots.is_older_than(self._max_age):
                del self._cache[robots_url]
                robots = None
            else:
                self._cache.move_to_end(robots_url)
        except KeyError:
            robots = None

        # Do we need to fetch robots into cache?
        if robots is None:
            try:
                # If another task is fetching it, then just wait for that task.
                await self._events[robots_url].wait()
                robots = self._cache[robots_url]
            except KeyError:
                # Create a new task to fetch it.
                self._events[robots_url] = trio.Event()
                robots = await self._get_robots(robots_url, downloader)
                event = self._events.pop(robots_url)
                event.set()

        # Note: we only check the first user agent.
        user_agent = policy.user_agents.get_first_user_agent()
        robots_decision = robots.is_allowed(user_agent, url)
        if policy.robots_txt.usage == 'OBEY':
            return robots_decision
        return not robots_decision

    async def _get_robots(self, robots_url, downloader):
        '''
        Locate and return a robots.txt file.

        Looks for non-expired robots.txt file first in database then request
        from network. Wherever the robots file is found, it is placed into the
        cache and then returned.

        If we get a copy from the network, then we also store a copy in the
        database. If we cannot get a copy from the network (e.g. 404 error) and
        we have a database copy, then we update the database copy's expiration.
        If we cannot get a copy from database or network, then we create a
        permissive robots.txt and use that instead.

        :param str url: Fetch the file at this URL.
        :param Downloader downloader:
        :rtype: RobotsTxt
        '''
        # Check DB. If not there (or expired), check network.
        now = datetime.now(timezone.utc)
        robots_doc = await self._get_robots_from_db(robots_url)

        if robots_doc is None or \
                (now - robots_doc['updated_at']).seconds > self._max_age:
            robots_file = await self._get_robots_from_net(robots_url,
                downloader)
        else:
            robots_file = None

        if robots_doc is None:
            # No local copy: create a new local copy. If robots_file is None, it
            # will be treated as a permissive RobotsTxt.
            logger.info('Saving new robots.txt file: %s', robots_url)
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
            logger.info('Updating robots.txt file: %s', robots_url)
            if robots_file is not None:
                robots_doc['file'] = robots_file
            else:
                del robots_doc['file']

            robots_doc['updated_at'] = now
            del robots_doc['url']

        # Upsert robots_docs.
        await self._save_robots_to_db(robots_doc)

        # Add to cache before completing the future to avoid race condition.
        self._cache[robots_url] = robots
        self._cache.move_to_end(robots_url)
        if len(self._cache) > self._max_cache:
            self._cache.popitem(last=False)
        return robots

    async def _get_robots_from_db(self, robots_url):
        '''
        Get robots document from the database.

        Returns None if it doesn't exist in the database.

        :param str robots_url: The URL of the robots.txt file.
        :returns: A database document.
        :rtype: dict
        '''
        query = r.table('robots_txt').get_all(robots_url, index='url').nth(0)

        async with self._db_pool.connection() as conn:
            try:
                db_robots = await query.run(conn)
            except r.ReqlNonExistenceError:
                db_robots = None

        return db_robots

    async def _get_robots_from_net(self, robots_url, downloader):
        '''
        Get robots.txt file from the network.

        Returns None if the file cannot be fetched (e.g. 404 error).

        :param str robots_url: Fetch the robots.txt file at this URL.
        :param Downloader downloader:
        :returns: Contents of robots.txt file or None if it couldn't be
            downloaded.
        :rtype: str
        '''

        logger.info('Fetching robots.txt: %s', robots_url)
        request = DownloadRequest(frontier_id=None, job_id=None, method='GET',
            url=robots_url, form_data=None, cost=0)
        response = await downloader.download(request, skip_mime=True)

        if response.status_code == 200 and response.body is not None:
            # There are no invalid byte sequences in latin1 encoding, so this
            # should always succeed.
            robots_file = response.body.decode('latin1')
        else:
            robots_file = None

        return robots_file

    async def _save_robots_to_db(self, robots_doc):
        async with self._db_pool.connection() as conn:
            await (
                r.table('robots_txt')
                 .insert(robots_doc, conflict='update')
                 .run(conn)
            )


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
            # The parser never throws an exception, it just ignores things that
            # it doesn't understand.
            self._robots.parse(robots_doc['file'])

    def is_allowed(self, user_agent, url):
        '''
        Return True if ``url`` is allowed by this robots.txt file.

        :param str user_agent: The user agent that want to access the URL.
        :param str url: The URL that the user agent wants to access.
        :rtype: bool
        '''
        return self._robots.is_allowed(user_agent, url)

    def is_older_than(self, age):
        '''
        Return True if this robots file is older than ``age``.

        :param datetime age: A timezone-aware datetime.
        :rtype: bool
        '''
        return (datetime.now(timezone.utc) - self._updated_at).seconds >= age
