import asyncio
import base64
from collections import defaultdict
from datetime import datetime
import logging

from dateutil.tz import tzlocal
import hashlib
import rethinkdb as r
import w3lib.url

from . import raise_future_exception
from .pubsub import PubSub
from .url_extractor import extract_urls


logger = logging.getLogger(__name__)


class CrawlManager:
    ''' Responsible for creating and managing crawl jobs. '''

    def __init__(self, db_pool, rate_limiter):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._rate_limiter = rate_limiter
        self._running_jobs = dict()

    async def load_job(id_):
        ''' Load a crawl job from the database. '''

        #TODO

    async def pause_all_jobs(self):
        ''' Pause all currently running jobs. '''

        running_jobs = list(self._running_jobs.values())
        tasks = list()

        for job in running_jobs:
            tasks.append(asyncio.ensure_future(job.pause()))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def start_job(self, name, seeds):
        '''
        Create a new job with a given name and seeds.

        Returns a job ID.
        '''

        def cleanup_job(future):
            ''' Remove a job from _running_jobs when it completes. '''
            del self._running_jobs[future.result()]

        job = _CrawlJob(self._db_pool, self._rate_limiter, name, seeds)
        await job.save()
        job.run().add_done_callback(cleanup_job)
        self._running_jobs[job.id] = job
        return job.id


class _CrawlJob:
    ''' Manages job state and crawl frontier. '''

    def __init__(self, db_pool, rate_limiter, name, seeds, max_cost=1):
        ''' Constructor. '''
        self.id = None
        self.name = name
        self.seeds = seeds
        self.policy = None

        self._db_pool = db_pool
        self._frontier_seen = set()
        self._frontier_size = 0
        self._insert_item_lock = asyncio.Lock()
        self._insert_item_sequence = 1
        self._max_cost = max_cost
        self._pending_downloads = dict()
        self._rate_limiter = rate_limiter
        self._short_id = None # First 4 octets of id, for readability.
        self._status = 'pending'
        self._stopped = asyncio.Future()
        self._task = None

    async def cancel(self):
        '''
        Cancel this job.

        A canceled job is similar to a paused job but cannot be resumed.
        '''

        logger.info('Crawl id={} is canceling...'.format(self._short_id))
        await self._stop()
        await self._set_status('canceled')
        logger.info('Crawl id={} is canceled.'.format(self._short_id))

    async def pause(self):
        '''
        Pause this job.

        A paused job may be resumed later.
        '''

        logger.info('Crawl id={} is pausing...'.format(self._short_id))
        await self._stop()
        await self._set_status('paused')
        logger.info('Crawl id={} is paused.'.format(self._short_id))

    def run(self):
        ''' Main loop for job. '''
        self._task = asyncio.ensure_future(self._run())
        raise_future_exception(self._task)
        return self._stopped

    async def save(self):
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

    async def _add_frontier_url(self, url, cost):
        '''
        Add a URL to the frontier with the specified cost.

        If the URL has been seen before, it is silently ignored.
        '''
        url_can = w3lib.url.canonicalize_url(url)
        hash_ = hashlib.blake2b(url_can.encode('ascii'), digest_size=16)
        url_hash = hash_.digest()

        if url_hash not in self._frontier_seen:
            logger.debug('Adding URL %s (cost=%0.2f)', url, cost)
            self._frontier_seen.add(url_hash)

            frontier_item = {
                'cost': cost,
                'job_id': self.id,
                'queued': False,
                'url': url,
                'url_can': url_can,
                'url_hash': url_hash,
            }

            async with self._db_pool.connection() as conn:
                self._frontier_size += 1
                await r.table('crawl_frontier').insert(frontier_item).run(conn)

    async def _complete(self):
        ''' Update status to indicate this job is complete. '''

        await self._stop()
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

        logger.info('Crawl id={} is complete.'.format(self._short_id))

    async def _download_completed(self, crawl_item_completed_future):
        ''' A coroutine that processes a downloaded item. '''

        crawl_item = await crawl_item_completed_future

        # Note that all item writes for a single job are serialized so that we
        # can insert an incrementing sequence number.
        async with self._insert_item_lock:
            async with self._db_pool.connection() as conn:
                item_data = {
                    'body': crawl_item.body,
                    'completed_at': crawl_item.completed_at,
                    'cost': crawl_item.cost,
                    'duration': crawl_item.duration.total_seconds(),
                    'exception': crawl_item.exception,
                    'headers': crawl_item.headers,
                    'insert_sequence': self._insert_item_sequence,
                    'is_success': crawl_item.status_code // 100 == 2,
                    'job_id': self.id,
                    'started_at': crawl_item.started_at,
                    'status_code': crawl_item.status_code,
                    'url': crawl_item.url,
                    'url_can': crawl_item.url_can,
                    'url_hash': crawl_item.url_hash,
                }
                await r.table('crawl_item').insert(item_data).run(conn)
                self._insert_item_sequence += 1

        await self._update_job_stats(crawl_item)

        # If successful, extract URLs.
        if crawl_item.exception is None and self._status == 'running':
            for new_url in extract_urls(crawl_item):
                new_item_cost = crawl_item.cost + 1
                if new_item_cost <= self._max_cost:
                    await self._add_frontier_url(new_url, new_item_cost)

        # Cleanup download task.
        del self._pending_downloads[crawl_item]
        async with self._db_pool.connection() as conn:
            await r.table('crawl_frontier').get(crawl_item.frontier_id) \
                   .delete().run(conn)
            self._frontier_size -= 1

        # If this is the last item in this crawl, then the crawl is complete.
        if self._frontier_size == 0:
            await self._complete()

    def _download_started(self, crawl_item_started_future):
        ''' Called when a download starts. '''
        crawl_item = crawl_item_started_future.result()
        dl_task = asyncio.ensure_future(
            self._download_completed(crawl_item.completed)
        )
        raise_future_exception(dl_task)
        self._pending_downloads[crawl_item] = dl_task

    async def _next_frontier_item(self):
        '''
        Get the next highest priority item from the frontier.

        If no item is available, then suspend until an item is added to the
        frontier.
        '''

        frontier = r.table('crawl_frontier')

        next_url_query = (
            frontier
            .between((False, self.id, r.minval),
                     (False, self.id, r.maxval),
                     index='cost_index')
            .order_by(index='cost_index')
            .limit(1)
        )

        change_query = (
            frontier
            .filter({'queued': False, 'job_id': self.id})
            .changes()
            .pluck('new_val')
        )

        # Get next URL, if there is one, or wait for a URL to be added.
        async with self._db_pool.connection() as conn:
            result = None
            cursor = await next_url_query.run(conn)
            while await cursor.fetch_next():
                result = await cursor.next()

            if result is None:
                feed = await change_query.run(conn)
                while await feed.fetch_next():
                    change = await feed.next()
                    result = change['new_val']
                    break

            await frontier.get(result['id']).update({'queued':True}).run(conn)

        logger.debug('Popped %s', result['url'])
        return result

    async def _run(self):
        ''' The main loop for a job. '''

        try:
            new_data = {}

            if self._status == 'pending':
                for seed in self.seeds:
                    await self._add_frontier_url(seed, cost=0)
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

            logger.info('Crawl id={} is running...'.format(self._short_id))

            while True:
                frontier_item = await self._next_frontier_item()
                crawl_item = _CrawlItem(frontier_item)
                crawl_item.started.add_done_callback(self._download_started)
                await self._rate_limiter.push(crawl_item)
        except asyncio.CancelledError:
            # We expect to be canceled when this job stops running
            pass

    async def _set_status(self, status):
        ''' Set job status. '''

        self._status = status

        async with self._db_pool.connection() as conn:
            table = r.table('crawl_job')
            query = table.get(self.id).update({'status': status})
            await query.run(conn)

    async def _stop(self):
        ''' Stop the job. '''

        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        pending_count = len(self._pending_downloads)

        if pending_count > 0:
            logger.info(
                'Crawl id={} is waiting for {} downloads to finish...'
                .format(self._short_id, len(pending_count))
            )
            download_tasks = self._pending_downloads.values()
            await asyncio.gather(*download_tasks)
            logger.info(
                'Crawl id={} downloads have finished.'
                .format(self._short_id)
            )

        logger.info('Crawl id={} has stopped running.'.format(self._short_id))
        self._stopped.set_result(self.id)

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


class _CrawlItem:
    ''' Represents a resource to be crawled and the result of crawling it. '''

    def __init__(self, frontier_item):
        '''
        Constructor.

        A ``frontier_item`` is a document from the crawl_frontier table.
        '''
        # These members are used for coordination with the job.
        self.started = asyncio.Future()
        self.completed = asyncio.Future()

        # These members are persistent.
        self.body = None
        self.completed_at = None
        self.cost = frontier_item['cost']
        self.exception = None
        self.frontier_id = frontier_item['id']
        self.headers = None
        self.started_at = None
        self.status_code = None
        self.url = frontier_item['url']
        self.url_can = frontier_item['url_can']
        self.url_hash = frontier_item['url_hash']

    def set_response(self, status_code, headers, body):
        ''' Update state from HTTP response. '''
        self.body = body
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.headers = headers
        self.status = 'complete'
        self.status_code = status_code
        self.completed.set_result(self)

    def set_start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = datetime.now(tzlocal())
        self.started.set_result(self)
