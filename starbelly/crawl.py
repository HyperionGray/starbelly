import asyncio
import base64
from collections import defaultdict
from datetime import datetime
import logging
from urllib.parse import urljoin, urlparse

from dateutil.tz import tzlocal
import lxml.html
import rethinkdb as r

from . import raise_future_exception
from .frontier import Frontier
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class CrawlJob:
    ''' Implements core crawling behavior. '''

    _running_jobs = dict()

    def __init__(self, name, db_pool, downloader, rate_limiter, seeds,
                 max_depth=1):
        ''' Constructor. '''
        self.id = None
        self.name = name
        self.seeds = seeds
        self.policy = None

        self._db_pool = db_pool
        self._downloader = downloader
        self._download_tasks = dict()
        self._frontier = Frontier(rate_limiter)
        self._insert_item_lock = asyncio.Lock()
        self._insert_item_sequence = 1
        self._max_depth = max_depth
        self._short_id = None # First 4 octets of id, for readability.
        self._status = 'pending'

    @staticmethod
    async def load_job(id_):
        ''' Load a crawl job from the database. '''

        #TODO

    @classmethod
    def pause_all_jobs(cls):
        '''
        Pause all currently running jobs.

        This will allow current downloads to finish.
        '''

        running_jobs = list(cls._running_jobs.values())

        for job in running_jobs:
            job.cancel()

        return asyncio.gather(
            *running_jobs,
            return_exceptions=True
        )

    async def save_job(self):
        ''' Insert or update job metadata in database. '''

        job_data = {
            'name': self.name,
            'seeds': self.seeds,
            'policy': self.policy,
            'status': self._status,
            'started_at': None,
            'completed_at': None,
            'duration': None,
            'item_count': 0,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {}
        }

        async with self._db_pool.connection() as conn:
            if self.id is None:
                result = await r.table('crawl_job').insert(job_data).run(conn)
                self.id = result['generated_keys'][0]
                self._short_id = self.id[:8]
            else:
                data['id'] = self.id
                r.table('crawl_job').update(data).run(conn)

    def start(self):
        '''
        Starts the crawl.

        Returns a future that fires when the crawl finishes.
        '''
        task = asyncio.ensure_future(self._run())
        self.__class__._running_jobs[self] = task
        return task

    async def _handle_download(self, dl_task):
        '''
        A coroutine that waits for a download task to finish and then processes
        the result.
        '''

        crawl_item = await dl_task

        # Note that all item writes for a single job are serialized so that we
        # can insert an incrementing sequence number.
        async with self._insert_item_lock:
            async with self._db_pool.connection() as conn:
                item_data = {
                    'body': crawl_item.body,
                    'completed_at': crawl_item.completed_at,
                    'crawl_id': self.id,
                    'depth': crawl_item.depth,
                    'duration': crawl_item.duration.total_seconds(),
                    'exception': crawl_item.exception,
                    'headers': crawl_item.headers,
                    'insert_sequence': self._insert_item_sequence,
                    'is_success': crawl_item.status_code // 100 == 2,
                    'started_at': crawl_item.started_at,
                    'status_code': crawl_item.status_code,
                    'url': crawl_item.url,
                }
                await r.table('crawl_item').insert(item_data).run(conn)
                self._insert_item_sequence += 1
                self._downloader.release_slot()

        await self._update_job_stats(crawl_item)

        # If successful, extract links.
        if crawl_item.exception is None and \
           self._status == 'running' and \
           crawl_item.depth < self._max_depth:

            for new_url in self._parse_urls(crawl_item):
                parsed = urlparse(new_url)
                if parsed.hostname == 'markhaa.se' and parsed.path.endswith('.html'): #TODO
                    self._frontier.add_item(
                        CrawlItem(new_url, depth=crawl_item.depth + 1)
                    )

        # Cleanup download task.
        del self._download_tasks[crawl_item]
        self._frontier.complete_item(crawl_item)

        # If this is the last item in this crawl, then the crawl is complete.
        if len(self._frontier) == 0 and len(self._download_tasks) == 0:
            await self._set_completed()

    def _parse_urls(self, crawl_item):
        '''
        Extract links from a crawl item.

        TODO move into new link extractor class
        '''
        doc = lxml.html.document_fromstring(crawl_item.body)
        for link in doc.iterlinks():
            new_url = urljoin(crawl_item.url, link[2])
            yield new_url

    async def _run(self):
        ''' Main crawling logic. '''

        logger.info('Crawl id={} starting...'.format(self._short_id))
        await self._set_running()

        try:
            while True:
                crawl_item = await self._frontier.get_item()
                dl_task = await self._downloader.schedule_download(crawl_item)
                handler = asyncio.ensure_future(self._handle_download(dl_task))
                self._download_tasks[crawl_item] = handler
                raise_future_exception(handler)
        except asyncio.CancelledError:
            if self._status != 'completed':
                logger.info('Crawl id={} is pausing...'.format(self._short_id))
                if len(self._download_tasks) > 0:
                    logger.info(
                        'Crawl id={} is waiting for {} downloads to finish...'
                        .format(self._short_id, len(self._download_tasks))
                    )
                    await asyncio.gather(*self._download_tasks.values())
                    logger.info(
                        'Crawl id={} all remaining downloads are finished.'
                        .format(self._short_id)
                    )
                await self._set_paused()

        logger.info('Crawl id={} has stopped.'.format(self._short_id))
        del self.__class__._running_jobs[self]

    async def _set_completed(self):
        ''' Update status to indicate this job is complete. '''

        self._status = 'completed'
        completed_at = datetime.now(tzlocal())

        new_data = {
            'status': self._status,
            'completed_at': completed_at,
            'duration': completed_at - r.row['started_at'],
        }

        async with self._db_pool.connection() as conn:
            query = r.table('crawl_job').get(self.id).update(new_data)
            await query.run(conn)

        self.__class__._running_jobs[self].cancel()
        logger.info('Crawl id={} is complete.'.format(self._short_id))

    async def _set_paused(self):
        ''' Update status to indicate this job is paused. '''

        self._status = 'paused'

        new_data = {'status': self._status}

        async with self._db_pool.connection() as conn:
            query = r.table('crawl_job').get(self.id).update(new_data)
            await query.run(conn)

        logger.info('Crawl id={} is paused.'.format(self._short_id))

    async def _set_running(self):
        ''' Update status to indicate this job is running. '''

        new_data = {}

        if self._status == 'pending':
            for seed in self.seeds:
                self._frontier.add_item(CrawlItem(seed, depth=0))
            self._status = 'running'
            new_data['started_at'] = datetime.now(tzlocal())
        elif self._status == 'paused':
            self._status = 'running'
        else:
            raise Exception('Cannot start or resume a crawl: status={}'
                .format(self._status))

        new_data['status'] = self._status

        async with self._db_pool.connection() as conn:
            query = r.table('crawl_job').get(self.id).update(new_data)
            await query.run(conn)

        logger.info('Crawl id={} is running.'.format(self._short_id))

    async def _update_job_stats(self, crawl_item):
        '''
        Update job stats with the result of this crawl item.

        This function *should* make an atomic change to the database, e.g.
        no competing task can partially update stats at the same time as this
        task.
        '''
        status = str(crawl_item.status_code)
        status_first_digit = status[0]
        new_data = {'item_count': r.row['item_count'] + 1}

        if crawl_item.exception is None:
            if 'http_status_counts' not in new_data:
                new_data['http_status_counts'] = {}

            # Increment count for status. (Assume zero if it doesn't exist yet).
            new_data['http_status_counts'][status] = (
                1 + r.branch(
                    r.row['http_status_counts'].has_fields(status),
                    r.row['http_status_counts'][status],
                    0
                )
            )

            if status_first_digit == '2':
                new_data['http_success_count'] = r.row['http_success_count'] + 1
            else:
                new_data['http_error_count'] = r.row['http_error_count'] + 1
        else:
            new_data['exception_count'] = r.row['exception_count'] + 1

        query = r.table('crawl_job').get(self.id).update(new_data)

        async with self._db_pool.connection() as conn:
            await query.run(conn)

class CrawlItem:
    ''' Represents a resource to be crawled and the result of crawling it. '''

    def __init__(self, url, depth):
        ''' Constructor. '''
        self.body = None
        self.completed_at = None
        self.depth = depth
        self.exception = None
        self.headers = None
        self.parsed_url = urlparse(url)
        self.started_at = None
        self.status_code = None
        self.url = url

    def set_response(self, status_code, headers, body):
        ''' Update state from HTTP response. '''
        self.body = body
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.headers = headers
        self.status = 'complete'
        self.status_code = status_code

    def set_start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = datetime.now(tzlocal())
