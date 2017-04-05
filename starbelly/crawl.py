import asyncio
import base64
from collections import defaultdict, namedtuple
from datetime import datetime
import functools
import gzip
import hashlib
import logging

from dateutil.tz import tzlocal
import hashlib
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
import w3lib.url

from . import cancel_futures, daemon_task
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
                 .update({'run_state':'cancelled'})
            )
            async with self._db_pool.connection() as conn:
                await cancel_query.run(conn)

    async def count_jobs(self):
        ''' Return the number of jobs that exist. '''
        async with self._db_pool.connection() as conn:
            count = await r.table('crawl_job').count().run(conn)
        return count

    async def list_jobs(self, limit=10, offset=0):
        '''
        List up to `limit` jobs, starting at row number `offset`, ordered by
        start date.
        '''

        query = (
            r.table('crawl_job')
             .order_by(index=r.desc('started_at'))
             .skip(offset)
             .limit(limit)
        )

        jobs = list()

        async with self._db_pool.connection() as conn:
            cursor = await query.run(conn)
            async for job in AsyncCursorIterator(cursor):
                jobs.append(job)

        return jobs

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
        job_query = r.table('crawl_job').get(job_id).pluck('name', 'run_state')
        async with self._db_pool.connection() as conn:
            job_data = await job_query.run(conn)
            name = job_data['name']
            run_state = job_data['run_state']
            seeds = []
        # Create a new job object to hold a pre-existing crawl. This is a bit
        # hacky.
        job = _CrawlJob(self._db_pool, self._rate_limiter, name, seeds)
        job.id = job_id
        job._run_state = run_state
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
        startup_query = r.table('crawl_job').get_all('running', index='run_state')
        async with self._db_pool.connection() as conn:
            cursor = await startup_query.run(conn)
            async for job in AsyncCursorIterator(cursor):
                # Cancel the job.
                await (
                    r.table('crawl_job')
                     .get(job['id'])
                     .update({'run_state':'cancelled'})
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

    def __init__(self, db_pool, rate_limiter, name, seeds, max_cost=10):
        ''' Constructor. '''
        self.id = None
        self.name = name
        self.seeds = seeds
        self.policy = None

        self._db_pool = db_pool
        self._frontier_seen = set()
        self._frontier_size = 0
        self._insert_item_lock = asyncio.Lock()
        self._insert_item_sequence = 0
        self._max_cost = max_cost
        self._pending_count = 0
        self._rate_limiter = rate_limiter
        self._run_state = 'pending'
        self._stopped = asyncio.Future()
        self._task = None

    async def cancel(self):
        '''
        Cancel this job.

        A cancelled job is similar to a paused job but cannot be resumed.
        '''

        logger.info('Canceling crawl id={}…'.format(self.id[:8]))
        await self._set_run_state('cancelled')
        await self._stop(graceful=False)
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
        await self._set_run_state('paused')
        await self._stop(graceful=True)
        logger.info('Crawl id={} has been paused.'.format(self.id[:8]))

    async def run(self):
        ''' The main loop for a job. '''
        self._task = asyncio.Task.current_task()

        try:
            new_data = {}
            frontier_item = None

            if self._run_state == 'pending':
                seeds = [FrontierItem(url=seed, cost=0) for seed in self.seeds]
                await self._add_frontier_items(seeds)
                self._run_state = 'running'
                new_data['started_at'] = datetime.now(tzlocal())
            elif self._run_state == 'paused':
                await self._reload_frontier()
                self._run_state = 'running'
            else:
                raise Exception('Cannot start or resume a job with run_state={}'
                    .format(self._run_state))

            new_data['run_state'] = self._run_state

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
                self._pending_count += 1
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
            'run_state': self._run_state,
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
        Add a list of `FrontierItem`s to the frontier.

        If a URL has been seen before, then that item is silently ignored.
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
        ''' Update state to indicate this job is complete. '''

        await self._stop()
        self._run_state = 'completed'
        completed_at = datetime.now(tzlocal())

        new_data = {
            'run_state': self._run_state,
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
        try:
            await self._save_item(crawl_item)
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
        finally:
            self._pending_count -= 1

        if self._pending_count == 0 and self._frontier_size == 0:
            # If this is the last item in this crawl, then the crawl is
            # complete. The crawl won't exit until all _handle_download()
            # coroutines finish, so we run this as a separate task.
            logger.info('Job %s has no more items pending.', self.id[:8])
            daemon_task(self._complete())

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
        count how many items are in it.
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
            .between((self.id, r.minval),
                     (self.id, r.maxval),
                     index='cost_index')
            .order_by(index='cost_index')
            .pluck('url_hash')
        )

        sequence_query = (
            r.table('crawl_job')
             .get(self.id)
             .get_field('item_count')
        )

        async with self._db_pool.connection() as conn:
            self._frontier_size = await frontier_query.count().run(conn)
            self._insert_item_sequence = await sequence_query.run(conn)
            for query in (item_query, frontier_query):
                cursor = await query.run(conn)
                async for item in AsyncCursorIterator(cursor):
                    self._frontier_seen.add(bytes(item['url_hash']))

        logger.info('Reloading frontier for crawl=%s is complete.', self.id[:8])

    async def _save_item(self, crawl_item):
        ''' Save a crawl item to the database. '''
        async with self._insert_item_lock:
            async with self._db_pool.connection() as conn:
                if crawl_item.exception is None:
                    duration = crawl_item.duration.total_seconds()
                    is_success = crawl_item.status_code // 100 == 2
                else:
                    duration = None
                    is_success = False

                compress_body = self._should_compress_body(crawl_item)

                if compress_body:
                    body = gzip.compress(crawl_item.body)
                else:
                    body = crawl_item.body

                body_hash = hashlib.blake2b(body, digest_size=32) \
                                   .digest()

                item_data = {
                    'body_id': body_hash,
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

                body_data = {
                    'id': body_hash,
                    'body': body,
                    'is_compressed': compress_body,
                }

                body = await r.table('crawl_item_body').get(body_hash).run(conn)

                if body is None:
                    await r.table('crawl_item_body').insert(body_data).run(conn)

                await r.table('crawl_item').insert(item_data).run(conn)
                self._insert_item_sequence += 1

    async def _set_run_state(self, run_state):
        ''' Set the job's run state. '''

        self._run_state = run_state

        async with self._db_pool.connection() as conn:
            table = r.table('crawl_job')
            query = table.get(self.id).update({'run_state': run_state})
            await query.run(conn)

    def _should_compress_body(self, crawl_item):
        '''
        Returns true if the crawl item body should be compressed.

        This is pretty naive right now (only compress text/* responses), but we
        can make it smarter in the future.
        '''
        should_compress = False

        if crawl_item.headers is not None \
            and 'text/' in crawl_item.headers.get('Content-Type', ''):
            should_compress = True

        return should_compress

    async def _stop(self, graceful=True):
        '''
        Stop the job.

        If ``graceful`` is ``True``, then this will wait for the job's open
        downloads to finish before returning, and items removed from the rate
        limiter will be placed back into the crawl frontier.
        '''
        if self._task is not None:
            await cancel_futures(self._task)

        removed_items = await self._rate_limiter.remove_job(self.id, graceful)
        self._pending_count = 0
        self._frontier_size = 0
        self._frontier_seen.clear()

        if graceful and len(removed_items) > 0:
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
        self.status_code = status_code

    def set_start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = datetime.now(tzlocal())
