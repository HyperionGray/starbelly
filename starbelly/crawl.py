import asyncio
import base64
from collections import defaultdict, namedtuple
from datetime import datetime
import functools
import gzip
import hashlib
import logging

import cchardet as chardet
from dateutil.tz import tzlocal
import hashlib
import mimeparse
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
import w3lib.url

from . import cancel_futures, daemon_task, VERSION
from .db import AsyncCursorIterator
from .policy import Policy
from .pubsub import PubSub
from .url_extractor import extract_urls


logger = logging.getLogger(__name__)
FrontierItem = namedtuple('FrontierItem', ['url', 'cost'])


class CrawlManager:
    ''' Responsible for creating and managing crawl jobs. '''

    def __init__(self, db_pool, rate_limiter, robots_txt_manager):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._rate_limiter = rate_limiter
        self._robots_txt_manager = robots_txt_manager
        self._running_jobs = dict()

    async def cancel_job(self, job_id):
        ''' Cancel a paused or running job. '''
        try:
            await self._running_jobs[job_id].cancel()
        except KeyError:
            # This job is already paused.
            cancel_query = (
                r.table('job')
                 .get(job_id)
                 .update({'run_state':'cancelled',
                          'completed_at': datetime.now(tzlocal())})
            )
            async with self._db_pool.connection() as conn:
                await cancel_query.run(conn)

    async def count_jobs(self):
        ''' Return the number of jobs that exist. '''
        async with self._db_pool.connection() as conn:
            count = await r.table('job').count().run(conn)
        return count

    async def delete_job(self, job_id):
        ''' Delete a job. '''
        job_query = r.table('job').get(job_id).pluck('run_state')
        delete_items_query = (
            r.table('crawl_item')
             .between((job_id, r.minval),
                      (job_id, r.maxval),
                      index='sync_index')
             .delete()
        )
        delete_job_query = r.table('job').get(job_id).delete()

        async with self._db_pool.connection() as conn:
            job = await job_query.run(conn)

            if job['run_state'] not in ('completed', 'cancelled'):
                raise Exception('Can only delete cancelled/completed jobs.')

            await delete_items_query.run(conn)
            await delete_job_query.run(conn)

    async def get_job(self, job_id):
        ''' Get data for the specified job. '''
        async with self._db_pool.connection() as conn:
            job = await r.table('job').get(job_id).run(conn)
        return job

    async def get_job_items(self, job_id, include_success, include_error,
                            include_exception, limit, offset):
        ''' Get items from a job. '''
        items = list()
        filters = []

        if include_success:
            filters.append(r.row['is_success'] == True)

        if include_error:
            filters.append((r.row['is_success'] == False) &
                           (~r.row.has_fields('exception')))

        if include_exception:
            filters.append((r.row['is_success'] == False) &
                           (r.row.has_fields('exception')))

        if len(filters) == 0:
            raise Exception('You must set at least one include_* flag to true.')

        def get_body(item):
            return {
                'join': r.branch(
                    item.has_fields('body_id'),
                    r.table('crawl_item_body').get(item['body_id']),
                    None
                )
            }

        base_query = (
            r.table('crawl_item')
             .between((job_id, r.minval),
                      (job_id, r.maxval),
                      index='sync_index')
             .filter(r.or_(*filters))
        )

        query = (
             base_query
             .skip(offset)
             .limit(limit)
             .merge(get_body)
             .without('body_id')
        )


        async with self._db_pool.connection() as conn:
            total_count = await base_query.count().run(conn)
            cursor = await query.run(conn)
            async for item in AsyncCursorIterator(cursor):
                items.append(item)

        return total_count, items

    async def list_jobs(self, limit=10, offset=0):
        '''
        List up to `limit` jobs, starting at row number `offset`, ordered by
        start date.
        '''

        query = (
            r.table('job')
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
        async with self._db_pool.connection() as conn:
            job_data = await r.table('job').get(job_id).run(conn)
        # Create a new job object to hold a pre-existing crawl. This is a bit
        # hacky.
        policy = Policy(job_data['policy'], VERSION, job_data['seeds'],
            self._robots_txt_manager)
        job = _CrawlJob(self._db_pool, self._rate_limiter, job_data['id'],
            job_data['seeds'], policy, job_data['name'])
        job.id = job_id
        job.item_count = job_data['item_count']
        job._run_state = job_data['run_state']
        job._started_at = job_data['started_at']
        self._running_jobs[job.id] = job
        job_task = asyncio.ensure_future(job.run())
        job_task.add_done_callback(functools.partial(self._cleanup_job, job))

    async def start_job(self, seeds, policy_id, name):
        '''
        Create a new job with a given seeds, policy, and name.

        Returns a job ID.
        '''

        job_data = {
            'name': name,
            'seeds': seeds,
            'run_state': 'pending',
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
            policy = await r.table('policy').get(policy_id).run(conn)
            job_data['policy'] = policy
            result = await r.table('job').insert(job_data).run(conn)

        policy = Policy(policy, VERSION, seeds, self._robots_txt_manager)
        job_id = result['generated_keys'][0]
        job = _CrawlJob(self._db_pool, self._rate_limiter, job_id, seeds,
            policy, name)
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
        startup_query = r.table('job').filter({'run_state': 'running'})
        async with self._db_pool.connection() as conn:
            cursor = await startup_query.run(conn)
            async for job in AsyncCursorIterator(cursor):
                # Cancel the job.
                await (
                    r.table('job')
                     .get(job['id'])
                     .update({'run_state': 'cancelled',
                              'completed_at': datetime.now(tzlocal())})
                     .run(conn)
                )
                # And clear its frontier.
                await (
                    r.table('frontier')
                     .between((job['id'], r.minval),
                              (job['id'], r.maxval),
                              index='cost_index')
                     .delete()
                     .run(conn)
                )

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

    def __init__(self, db_pool, rate_limiter, id_, seeds, policy, name):
        ''' Constructor. '''
        self.id = id_
        self.item_count = 0
        self.name = name
        self.policy = policy
        self.seeds = seeds

        self._db_pool = db_pool
        self._frontier_seen = set()
        self._frontier_size = 0
        self._insert_item_lock = asyncio.Lock()
        self._insert_item_sequence = 0
        self._pending_count = 0
        self._rate_limiter = rate_limiter
        self._run_state = 'pending'
        self._started_at = datetime.now(tzlocal())
        self._stopped = asyncio.Future()
        self._task = None

    async def cancel(self):
        '''
        Cancel this job.

        A cancelled job is similar to a paused job but cannot be resumed.
        '''

        logger.info('Canceling crawl id={}…'.format(self.id[:8]))
        self._run_state = 'cancelled'
        await self._stop(graceful=False)

        cancel_query = (
            r.table('job')
             .get(self.id)
             .update({'run_state': 'cancelled',
                      'completed_at': datetime.now(tzlocal())})
        )

        frontier_query = (
            r.table('frontier')
             .between((self.id, r.minval),
                      (self.id, r.maxval),
                      index='cost_index')
             .delete()
        )

        async with self._db_pool.connection() as conn:
            await cancel_query.run(conn)
            await frontier_query.run(conn)

        logger.info('Crawl id={} has been cancelled.'.format(self.id[:8]))

    async def pause(self):
        '''
        Pause this job.

        A paused job may be resumed later.
        '''

        logger.info('Pausing crawl id={}…'.format(self.id[:8]))
        self._run_state = 'paused'

        query = (
            r.table('job')
             .get(self.id)
             .update({'run_state': 'paused'})
        )

        async with self._db_pool.connection() as conn:
            await query.run(conn)

        await self._stop(graceful=True)
        logger.info('Crawl id={} has been paused.'.format(self.id[:8]))

    async def run(self):
        ''' The main loop for a job. '''
        self._task = asyncio.Task.current_task()

        try:
            new_data = {}
            frontier_item = None

            if self._run_state == 'pending':
                seeds = [FrontierItem(url=seed, cost=1) for seed in self.seeds]
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
                query = r.table('job').get(self.id).update(new_data)
                await query.run(conn)

            logger.info('Job id={} is running...'.format(self.id[:8]))

            while True:
                frontier_item = await self._next_frontier_item()
                crawl_item = _CrawlItem(self.policy, self.id,
                    self._handle_download, frontier_item)
                await self._rate_limiter.push(crawl_item)
                frontier_item = None
                self._pending_count += 1
        except asyncio.CancelledError:
            # Put the frontier item back on the frontier
            if frontier_item is not None:
                async with self._db_pool.connection() as conn:
                    await r.table('frontier').insert(frontier_item).run(conn)
        finally:
            self._task = None

    async def _add_frontier_items(self, frontier_items):
        '''
        Add a list of `FrontierItem`s to the frontier.

        If a URL has been seen before, then that item is silently ignored.
        '''
        insert_items = list()

        for frontier_item in frontier_items:
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
                await r.table('frontier').insert(insert_items).run(conn)

    async def _complete(self, graceful=True):
        ''' Update state to indicate this job is complete. '''

        await self._stop(graceful)
        self._run_state = 'completed'
        completed_at = datetime.now(tzlocal())

        new_data = {
            'run_state': self._run_state,
            'completed_at': completed_at,
            'duration': completed_at - r.row['started_at'],
        }

        async with self._db_pool.connection() as conn:
            query = r.table('job').get(self.id).update(new_data)
            await query.run(conn)

        logger.info('Crawl id={} is complete.'.format(self.id[:8]))

    async def _handle_download(self, crawl_item):
        ''' A coroutine that processes a downloaded item. '''

        # Note that all item writes for a single job are serialized so that we
        # can insert an incrementing sequence number.
        try:
            if self._run_state != 'running':
                # Don't finish processing items if the crawl stopped.
                logger.info('Ignoring item because crawl is not running: %s',
                    crawl_item.url)
                return

            if crawl_item.is_complete():
                await self._save_item(crawl_item)
                await self._update_job_stats(crawl_item)
                self.item_count += 1

            # Remove item from frontier.
            async with self._db_pool.connection() as conn:
                await r.table('frontier').get(crawl_item.frontier_id) \
                       .delete().run(conn)
                self._frontier_size -= 1

            # Extract links.
            if crawl_item.body is not None:
                extracted_urls = await asyncio.get_event_loop().run_in_executor(
                    None,
                    extract_urls,
                    crawl_item
                )
                frontier_items = list()
                for url in extracted_urls:
                    robots_ok = await self.policy.robots_txt.is_allowed(url)
                    new_cost = self.policy.url_rules.get_cost(crawl_item.cost,
                        url)
                    cost_ok = new_cost > 0 and \
                        not self.policy.limits.exceeds_max_cost(new_cost)
                    if robots_ok and cost_ok:
                        frontier_items.append(FrontierItem(url, new_cost))
                await self._add_frontier_items(frontier_items)
        finally:
            self._pending_count -= 1

        # Enforce policy limits. The crawl won't exit until all
        # _handle_download() coroutines finish, so we have to complete the
        # crawl in a separate task.
        if self._pending_count == 0 and self._frontier_size == 0:
            logger.info('Job %s has no more items pending.', self.id[:8])
            daemon_task(self._complete(graceful=True))
        elif self.policy.limits.exceeds_max_items(self.item_count):
            logger.info('Job %s has exceed items limit.', self.id[:8])
            daemon_task(self._complete(graceful=False))
        elif self.policy.limits.exceeds_max_duration(
            (datetime.now(tzlocal()) - self._started_at).seconds):
            #TODO This is not the ideal place to process duration limit.
            logger.info('Job %s has exceed duration limit.', self.id[:8])
            daemon_task(self._complete(graceful=False))

    async def _next_frontier_item(self):
        '''
        Get the next highest priority item from the frontier.

        If no item is available, then suspend until an item is added to the
        frontier.
        '''
        next_url_query = (
            r.table('frontier')
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
            r.table('frontier')
             .between((self.id, r.minval),
                      (self.id, r.maxval),
                      index='cost_index')
             .order_by(index='cost_index')
             .pluck('url_hash')
        )

        sequence_query = (
            r.table('job')
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
                item_data = {
                    'completed_at': crawl_item.completed_at,
                    'cost': crawl_item.cost,
                    'duration': crawl_item.duration.total_seconds(),
                    'insert_sequence': self._insert_item_sequence,
                    'job_id': self.id,
                    'started_at': crawl_item.started_at,
                    'url': crawl_item.url,
                    'url_can': crawl_item.url_can,
                    'url_hash': crawl_item.url_hash,
                }

                if crawl_item.exception is None:
                    item_data['charset'] = crawl_item.charset
                    item_data['completed_at'] = crawl_item.completed_at
                    item_data['content_type'] = crawl_item.content_type
                    item_data['headers'] = crawl_item.headers
                    item_data['is_success'] = crawl_item.status_code // 100 == 2
                    item_data['status_code'] = crawl_item.status_code
                    compress_body = self._should_compress_body(crawl_item)

                    if compress_body:
                        body = gzip.compress(crawl_item.body, compresslevel=6)
                    else:
                        body = crawl_item.body

                    body_hash = hashlib.blake2b(body, digest_size=32) \
                                       .digest()

                    item_data['body_id'] = body_hash
                    body_data = {
                        'id': body_hash,
                        'body': body,
                        'is_compressed': compress_body,
                    }

                    body = await r.table('crawl_item_body').get(body_hash) \
                        .run(conn)

                    if body is None:
                        await r.table('crawl_item_body').insert(body_data) \
                            .run(conn)
                else:
                    item_data['exception'] = crawl_item.exception
                    item_data['is_success'] = False

                await r.table('crawl_item').insert(item_data).run(conn)
                self._insert_item_sequence += 1

    def _should_compress_body(self, crawl_item):
        '''
        Returns true if the crawl item body should be compressed.

        This is pretty naive right now (only compress text/* responses), but we
        can make it smarter in the future.
        '''
        type_, subtype, parameters = mimeparse.parse_mime_type(
            crawl_item.content_type)
        return type_ == 'text'

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
                await r.table('frontier').insert(insert_items).run(conn)

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

        query = r.table('job').get(self.id).update(new_data)

        async with self._db_pool.connection() as conn:
            await query.run(conn)


class _CrawlItem:
    ''' Represents a resource to be crawled and the result of crawling it. '''

    def __init__(self, policy, job_id, download_callback, frontier_item):
        '''
        Constructor.

        A ``frontier_item`` is a document from the ``frontier`` table.
        '''

        self.policy = policy
        self.job_id = job_id
        self.download_callback = download_callback
        self.completed = asyncio.Future()

        # These members are persistent.
        self.body = None
        self.completed_at = None
        self.content_type = None
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

    def is_complete(self):
        ''' Return True if this item was completed. '''
        return self.completed_at is not None

    def set_exception(self, exception):
        ''' Update state from HTTP response. '''
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.exception = exception

    def set_response(self, response, body):
        ''' Update state from HTTP response. '''
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.status_code = response.status
        self.headers = response.headers
        #TODO try sniffing mime types if not declared?
        self.content_type = response.content_type
        if response.charset is not None:
            self.charset = response.charset
        else:
            self.charset = chardet.detect(body)['encoding']
        self.body = body

    def set_start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = datetime.now(tzlocal())
