import asyncio
import base64
from collections import defaultdict, namedtuple
from datetime import datetime
import functools
import logging

from dateutil.tz import tzlocal
import hashlib
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
import w3lib.url

from . import cancel_futures
from .db import AsyncCursorIterator
from .pubsub import PubSub
from .url_extractor import extract_urls


logger = logging.getLogger(__name__)
FrontierItem = namedtuple('FrontierItem', ['url', 'cost'])


class CrawlManager:
    ''' Responsible for creating and managing crawl jobs. '''

    def __init__(self, db_pool, rate_limiter):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._rate_limiter = rate_limiter
        self._running_jobs = dict()

    async def cancel_job(self, job_id):
        ''' Cancel a paused or running job. '''
        try:
            await self._running_jobs[job_id].cancel()
        except KeyError:
            # This job is already paused.
            cancel_query = (
                r.table('crawl_job')
                 .get(job_id)
                 .update({'status':'cancelled'})
            )
            async with self._db_pool.connection() as conn:
                await cancel_query.run(conn)

    async def pause_all_jobs(self):
        ''' Pause all currently running jobs. '''

        running_jobs = list(self._running_jobs.values())
        tasks = list()

        for job in running_jobs:
            tasks.append(asyncio.ensure_future(job.pause()))

        await asyncio.gather(*tasks)

    async def pause_job(self, job_id):
        ''' Pause a single job. '''
        await self._running_jobs[job_id].pause()

    async def resume_job(self, job_id):
        ''' Resume a single job. '''
        job_query = r.table('crawl_job').get(job_id).pluck('name', 'status')
        async with self._db_pool.connection() as conn:
            job_data = await job_query.run(conn)
            name = job_data['name']
            status = job_data['status']
            seeds = []
        # Create a new job object to hold a pre-existing crawl. This is a bit
        # hacky.
        job = _CrawlJob(self._db_pool, self._rate_limiter, name, seeds)
        job.id = job_id
        job._status = status
        self._running_jobs[job.id] = job
        job_task = asyncio.ensure_future(job.run())
        job_task.add_done_callback(functools.partial(self._cleanup_job, job))

    async def start_job(self, name, seeds):
        '''
        Create a new job with a given name and seeds.

        Returns a job ID.
        '''

        job = _CrawlJob(self._db_pool, self._rate_limiter, name, seeds)
        await job.save()
        self._running_jobs[job.id] = job
        job_task = asyncio.ensure_future(job.run())
        job_task.add_done_callback(functools.partial(self._cleanup_job, job))
        return job.id

    async def startup_check(self):
        ''' Do some sanity checks at startup. '''

        logger.info('Doing startup check...')

        # If the server was previously killed, then some jobs may still be in
        # the 'running' state even though they clearly aren't running. We mark
        # those jobs as 'cancelled' since killing the jobs may have left them in
        # an inconsistent state that can't be repaired.
        count = 0
        startup_query = r.table('crawl_job').get_all('running', index='status')
        async with self._db_pool.connection() as conn:
            cursor = await startup_query.run(conn)
            async for job in AsyncCursorIterator(cursor):
                # Cancel the job.
                await (
                    r.table('crawl_job')
                     .get(job['id'])
                     .update({'status':'cancelled'})
                     .run(conn)
                )
                # And clear its frontier. (this is pretty hacky)
                dummy_job = _CrawlJob(self._db_pool, self._rate_limiter, '', [])
                dummy_job.id = job['id']
                await dummy_job.clear_frontier()
                count += 1

        if count > 0:
            logger.warning(
                '%d jobs have been cancelled by the startup check.', count
            )

    def _cleanup_job(self, job, future):
        ''' Remove a job from _running_jobs when it completes. '''
        try:
            # Trigger any exception.
            future.result()
        except asyncio.CancelledError:
            pass
        del self._running_jobs[job.id]


class _CrawlJob:
    ''' Manages job state and crawl frontier. '''

    def __init__(self, db_pool, rate_limiter, name, seeds, max_cost=2):
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
        self._rate_limiter = rate_limiter
        self._status = 'pending'
        self._stopped = asyncio.Future()
        self._task = None

    async def cancel(self):
        '''
        Cancel this job.

        A cancelled job is similar to a paused job but cannot be resumed.
        '''

        logger.info('Canceling crawl id={}…'.format(self.id[:8]))
        await self._set_status('cancelled')
        await self._stop(finish_downloads=False)
        await self.clear_frontier()
        logger.info('Crawl id={} has been cancelled.'.format(self.id[:8]))

    async def clear_frontier(self):
        ''' Clear `crawl_frontier` table for a specified job ID. '''
        async with self._db_pool.connection() as conn:
            await (
                r.table('crawl_frontier')
                 .between((self.id, r.minval),
                          (self.id, r.maxval),
                          index='cost_index')
                 .delete()
                 .run(conn)
            )


    async def pause(self):
        '''
        Pause this job.

        A paused job may be resumed later.
        '''

        logger.info('Pausing crawl id={}…'.format(self.id[:8]))
        await self._set_status('paused')
        await self._stop(finish_downloads=True)
        logger.info('Crawl id={} has been paused.'.format(self.id[:8]))

    async def run(self):
        ''' The main loop for a job. '''
        self._task = asyncio.Task.current_task()

        try:
            new_data = {}
            frontier_item = None

            if self._status == 'pending':
                seeds = [FrontierItem(url=seed, cost=0) for seed in self.seeds]
                await self._add_frontier_items(seeds)
                self._status = 'running'
                new_data['started_at'] = datetime.now(tzlocal())
            elif self._status == 'paused':
                await self._reload_frontier()
                self._status = 'running'
            else:
                raise Exception('Cannot start or resume a job with status={}'
                    .format(self._status))

            new_data['status'] = self._status

            async with self._db_pool.connection() as conn:
                query = r.table('crawl_job').get(self.id).update(new_data)
                await query.run(conn)

            logger.info('Job id={} is running...'.format(self.id[:8]))

            while True:
                frontier_item = await self._next_frontier_item()
                crawl_item = _CrawlItem(self.id, self._handle_download,
                    frontier_item)
                await self._rate_limiter.push(crawl_item)
                frontier_item = None
        except asyncio.CancelledError:
            # Put the frontier item back on the frontier
            if frontier_item is not None:
                async with self._db_pool.connection() as conn:
                    await r.table('crawl_frontier').insert(frontier_item) \
                           .run(conn)
        finally:
            self._task = None

    async def save(self):
        ''' Insert job metadata in database. '''

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
            else:
                data['id'] = self.id
                r.table('crawl_job').update(data).run(conn)

    async def _add_frontier_items(self, frontier_items):
        '''
        Add a list of extracted URLs to the frontier with the specified cost.

        If the URL has been seen before, it is silently ignored.
        '''
        insert_items = list()

        for frontier_item in frontier_items:
            if frontier_item.cost > self._max_cost:
                continue

            url_can = w3lib.url.canonicalize_url(frontier_item.url)
            hash_ = hashlib.blake2b(url_can.encode('ascii'), digest_size=16)
            url_hash = hash_.digest()

            if url_hash not in self._frontier_seen:
                logger.debug('Adding URL %s (cost=%0.2f)',
                    frontier_item.url, frontier_item.cost)
                insert_items.append({
                    'cost': frontier_item.cost,
                    'job_id': self.id,
                    'url': frontier_item.url,
                    'url_can': url_can,
                    'url_hash': url_hash,
                })
            self._frontier_seen.add(url_hash)

        if len(insert_items) > 0:
            async with self._db_pool.connection() as conn:
                self._frontier_size += len(insert_items)
                await r.table('crawl_frontier').insert(insert_items).run(conn)

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

        logger.info('Crawl id={} is complete.'.format(self.id[:8]))

    async def _handle_download(self, crawl_item):
        ''' A coroutine that processes a downloaded item. '''

        # Note that all item writes for a single job are serialized so that we
        # can insert an incrementing sequence number.
        async with self._insert_item_lock:
            async with self._db_pool.connection() as conn:
                if crawl_item.exception is None:
                    duration = crawl_item.duration.total_seconds()
                    is_success = crawl_item.status_code // 100 == 2
                else:
                    duration = None
                    is_success = False

                item_data = {
                    'body': crawl_item.body,
                    'completed_at': crawl_item.completed_at,
                    'cost': crawl_item.cost,
                    'duration': duration,
                    'exception': crawl_item.exception,
                    'headers': crawl_item.headers,
                    'insert_sequence': self._insert_item_sequence,
                    'is_success': is_success,
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

        # Remove item from frontier.
        async with self._db_pool.connection() as conn:
            await r.table('crawl_frontier').get(crawl_item.frontier_id) \
                   .delete().run(conn)
            self._frontier_size -= 1

        # Extract links.
        if crawl_item.exception is None:
            extracted = extract_urls(crawl_item)
            new_cost = crawl_item.cost + 1
            frontier_items = [FrontierItem(url, new_cost) for url in extracted]
            await self._add_frontier_items(frontier_items)

        if self._status == 'running' and self._frontier_size == 0:
            # If this is the last item in this crawl, then the crawl is
            # complete.
            await self._complete()

    async def _next_frontier_item(self):
        '''
        Get the next highest priority item from the frontier.

        If no item is available, then suspend until an item is added to the
        frontier.
        '''
        next_url_query = (
            r.table('crawl_frontier')
             .between((self.id, r.minval),
                     (self.id, r.maxval),
                     index='cost_index')
             .order_by(index='cost_index')
             .nth(0)
             .delete(return_changes=True)
        )

        # Get next URL, if there is one, or wait for a URL to be added.
        while True:
            async with self._db_pool.connection() as conn:
                try:
                    response = await asyncio.shield(next_url_query.run(conn))
                    result = response['changes'][0]['old_val']
                    break
                except ReqlNonExistenceError:
                    await asyncio.sleep(1)

        logger.debug('Popped %s', result['url'])
        return result

    async def _reload_frontier(self):
        '''
        When un-pausing a crawl, we need to reload the `_frontier_seen` set and
        reload the frontier
        '''

        logger.info('Reloading frontier for crawl=%s (this may take a few '
                    'seconds)', self.id[:8])

        item_query = (
            r.table('crawl_item')
            .between((self.id, r.minval),
                     (self.id, r.maxval),
                     index='sync_index')
            .order_by(index='sync_index')
            .pluck('url_hash')
        )

        frontier_query = (
            r.table('crawl_frontier')
            .between((False, self.id, r.minval),
                     (False, self.id, r.maxval),
                     index='cost_index')
            .order_by(index='cost_index')
            .pluck('url_hash')
        )

        async with self._db_pool.connection() as conn:
            for query in (item_query, frontier_query):
                cursor = await query.run(conn)
                async for item in AsyncCursorIterator(cursor):
                    self._frontier_seen.add(item['url_hash'])

        logger.info('Reloading frontier for crawl=%s is complete.', self.id[:8])

    async def _set_status(self, status):
        ''' Set job status. '''

        self._status = status

        async with self._db_pool.connection() as conn:
            table = r.table('crawl_job')
            query = table.get(self.id).update({'status': status})
            await query.run(conn)

    async def _stop(self, finish_downloads=True):
        '''
        Stop the job.

        If ``finish_downloads`` is ``True``, then this will wait for the
        job's open downloads to finish before returning. Items removed from
        the rate limiter will be placed back into the crawl frontier.
        '''
        if self._task is not None:
            await cancel_futures(self._task)
        removed_items = await self._rate_limiter.remove_job(
            self.id, finish_downloads)

        #TODO Finish_downloads is a bad name, it really means "pause" vs "cancel"
        if finish_downloads:
            insert_items = list()

            for removed_item in removed_items:
                insert_items.append({
                    'cost': removed_item.cost,
                    'job_id': self.id,
                    'url': removed_item.url,
                    'url_can': removed_item.url_can,
                    'url_hash': removed_item.url_hash,
                })

            logger.info('Putting %d items back in frontier.', len(insert_items))
            async with self._db_pool.connection() as conn:
                await r.table('crawl_frontier').insert(insert_items).run(conn)

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

    def __init__(self, job_id, download_callback, frontier_item):
        '''
        Constructor.

        A ``frontier_item`` is a document from the crawl_frontier table.
        '''

        self.job_id = job_id
        self.download_callback = download_callback
        self.completed = asyncio.Future()

        # These members are persistent.
        self.body = None
        self.completed_at = None
        self.cost = frontier_item['cost']
        self.duration = None
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

    def set_start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = datetime.now(tzlocal())
