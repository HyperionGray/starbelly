import asyncio
import base64
from collections import defaultdict, namedtuple
from datetime import datetime
import functools
import gzip
import hashlib
import logging
import pickle
import random
import time

from aiohttp.cookiejar import CookieJar
from dateutil.tz import tzlocal
import mimeparse
from operator import itemgetter
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
from urllib.parse import urlparse
import w3lib.url

from . import cancel_futures, daemon_task, VERSION
from .db import CursorContext
from .downloader import DownloadRequest
from .login import get_login_form
from .policy import Policy
from .pubsub import PubSub
from .url_extractor import extract_urls


logger = logging.getLogger(__name__)
FrontierItem = namedtuple('FrontierItem', ['url', 'cost'])
ExtractItem = namedtuple('ExtractItem', ['url', 'cost', 'content_type', 'body'])
CrawlStats = namedtuple('CrawlStats', ['job_id', 'frontier', 'pending',
    'extraction'])


class CrawlManager:
    ''' Responsible for creating and managing crawl jobs. '''

    def __init__(self, db_pool, rate_limiter, downloader, robots_txt_manager):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._downloader = downloader
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

    async def delete_job(self, job_id):
        ''' Delete a job. '''
        job_query = r.table('job').get(job_id).pluck('run_state')
        delete_items_query = (
            r.table('response')
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
            query = r.table('job').get(job_id).without('frontier_seen')
            try:
                job = await query.run(conn)
            except rethinkdb.errors.ReqlNonExistenceError:
                job = None
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
                    r.table('response_body').get(item['body_id']),
                    None
                )
            }

        base_query = (
            r.table('response')
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
            async for item in cursor:
                items.append(item)
            await cursor.close()

        return total_count, items

    def get_stats(self):
        ''' Get resource statistics for all jobs. '''
        stats = list()

        for job in self._running_jobs.values():
            stats.append(job.get_stats())

        return stats

    async def list_jobs(self, limit, offset, started_after, tag):
        '''
        List up to `limit` jobs, starting at row number `offset`, ordered by
        start date.
        '''
        query = r.table('job')

        if started_after is not None:
            query = query.between(started_after, r.maxval, index='started_at')

        # Have to order_by() before filter().
        query = query.order_by(index=r.desc('started_at'))

        if tag is not None:
            query = query.filter(r.row['tags'].contains(tag))

        async with self._db_pool.connection() as conn:
            count = await query.count().run(conn)

        query = (
            query
            .without('frontier_seen')
            .skip(offset)
            .limit(limit)
        )

        jobs = list()

        async with self._db_pool.connection() as conn:
            cursor = await query.run(conn)
            async for job in cursor:
                jobs.append(job)
            await cursor.close()

        return count, jobs

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
        policy = Policy(job_data['policy'], VERSION, job_data['seeds'],
            self._robots_txt_manager)
        job = _CrawlJob(self._db_pool, self._rate_limiter, self._downloader,
            job_data['id'], job_data['seeds'], policy, job_data['name'])
        await job.resume(job_data)
        self._running_jobs[job.id] = job
        job.stopped.add_done_callback(functools.partial(self._cleanup_job, job))

    async def start_job(self, seeds, policy_id, name, tags):
        '''
        Create a new job with a given seeds, policy, name, and tags.

        Returns a job ID.
        '''

        job_data = {
            'name': name,
            'seeds': seeds,
            'tags': tags,
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
        job = _CrawlJob(self._db_pool, self._rate_limiter, self._downloader,
            job_id, seeds, policy, name)
        self._running_jobs[job.id] = job
        job.stopped.add_done_callback(functools.partial(self._cleanup_job, job))
        await job.start()
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
            async for job in cursor:
                logger.warning('Startup: cancelling unfinished job %s.',
                    job['id'][:8])
                # Cancel the job.
                await (
                    r.table('job')
                     .get(job['id'])
                     .update({'run_state': 'cancelled',
                              'completed_at': datetime.now(tzlocal())})
                     .run(conn)
                )
                # And clear its frontier.
                logger.warning('Startup: clearing job=%s frontier.',
                    job['id'][:8])
                await (
                    r.table('frontier')
                     .between((job['id'], r.minval),
                              (job['id'], r.maxval),
                              index='cost_index')
                     .delete()
                     .run(conn)
                )
                # And its extraction queue.
                logger.warning('Startup: clearing job=%s extraction queue.',
                    job['id'][:8])
                await (
                    r.table('extraction_queue')
                     .between((job['id'], r.minval),
                              (job['id'], r.maxval),
                              index='cost_index')
                     .delete()
                     .run(conn)
                )
            await cursor.close()

        if count > 0:
            logger.warning(
                '%d jobs have been cancelled by the startup check.', count
            )

    async def update_job(self, job_id, name, tags):
        ''' Update job metadata. '''
        update = dict()

        if name is not None:
            update['name'] = name
        if tags is not None:
            update['tags'] = tags

        if len(update) > 0:
            async with self._db_pool.connection() as conn:
                await r.table('job').get(job_id).update(update).run(conn)

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

    def __init__(self, db_pool, rate_limiter, downloader, id_, seeds, policy,
        name):
        ''' Constructor. '''
        self.id = id_
        self.item_count = 0
        self.name = name
        self.policy = policy
        self.seeds = seeds
        self.stopped = asyncio.Future()

        self._authenticated_domains = set()
        self._cookie_jar = None
        self._db_pool = db_pool
        self._downloader = downloader
        self._extraction_size = 0
        self._extraction_task = None
        self._frontier_seen = set()
        self._frontier_size = 0
        self._frontier_task = None
        self._limits_task = None
        self._insert_item_sequence = 0
        self._pending_count = 0
        self._rate_limiter = rate_limiter
        self._run_state = 'pending'
        self._save_queue = asyncio.Queue(maxsize=1)
        self._save_task = None
        self._started_at = None

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
             .update({
                'authenticated_domains': None,
                'cookie_jar': None,
                'run_state': 'cancelled',
                'completed_at': datetime.now(tzlocal())
             })
        )

        frontier_query = (
            r.table('frontier')
             .between((self.id, r.minval),
                      (self.id, r.maxval),
                      index='cost_index')
             .delete()
        )

        extraction_query = (
            r.table('extraction_queue')
             .between((self.id, r.minval),
                      (self.id, r.maxval),
                      index='cost_index')
             .delete()
        )

        async with self._db_pool.connection() as conn:
            await cancel_query.run(conn)
            await frontier_query.run(conn)
            await extraction_query.run(conn)

        logger.info('Crawl id={} has been cancelled.'.format(self.id[:8]))

    def get_stats(self):
        ''' Return resource stats for this job. '''
        return CrawlStats(self.id, self._frontier_size, self._pending_count,
            self._extraction_size)

    async def pause(self):
        '''
        Pause this job.

        A paused job may be resumed later.
        '''

        logger.info('Pausing crawl id={}…'.format(self.id[:8]))
        self._run_state = 'paused'
        await self._stop(graceful=True)

        query = (
            r.table('job')
             .get(self.id)
             .update({
                'authenticated_domains': list(self._authenticated_domains),
                'cookie_jar': pickle.dumps(self._cookie_jar._cookies),
                'extraction_size': self._extraction_size,
                'frontier_seen': pickle.dumps(self._frontier_seen),
                'frontier_size': self._frontier_size,
                'insert_item_sequence': self._insert_item_sequence,
                'run_state': 'paused',
             })
        )

        async with self._db_pool.connection() as conn:
            await query.run(conn)

        self._extraction_size = 0
        self._frontier_seen.clear()
        self._frontier_size = 0
        self._pending_count = 0
        logger.info('Crawl id={} has been paused.'.format(self.id[:8]))

    async def resume(self, job_data):
        ''' On resume, restore crawl state. '''
        self.item_count = job_data['item_count']
        self._authenticated_domains = set(job_data['cookie_jar'])
        self._cookie_jar = pickle.loads(job_data['cookie_jar'])
        self._insert_item_sequence = job_data['insert_item_sequence']
        self._extraction_size = job_data['extraction_size']
        self._frontier_seen = pickle.loads(job_data['frontier_seen'])
        self._frontier_size = job_data['frontier_size']
        self._run_state = job_data['run_state']
        self._started_at = job_data['started_at']
        await self.start()

    async def run_extractor(self):
        '''
        This task fetches items from the extraction queue and finds links to
        follow.
        '''
        def delete(item):
            ''' Query helper for deleting an extract item. '''
            return r.table('extraction_queue').get(item['id']).delete()

        def get_body(item):
            ''' Query helper for joining response body to extract item. '''
            return {'join': r.table('response_body').get(item['body_id'])}

        extract_query = (
            r.table('extraction_queue')
             .between((self.id, r.minval),
                      (self.id, r.maxval),
                      index='cost_index')
             .order_by(index='cost_index')
             .merge(get_body)
        )

        while True:
            try:
                async with self._db_pool.connection() as conn:
                    async with CursorContext(extract_query, conn) as cursor:
                        async for extract_doc in cursor:
                            await self._extract(extract_doc)
                            await delete(extract_doc).run(conn)
                            self._extraction_size -= 1

                # When cursor is exhausted, wait a bit and try again.
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                # Cancellation is okay.
                break
            except Exception as e:
                logger.exception('run_extractor() exception')

    async def run_frontier(self):
        '''
        This task takes items off the frontier and sends them to the rate
        limiter.
        '''
        try:
            while True:
                frontier_item = None
                frontier_item = await self._next_frontier_item()
                robots_ok = await self.policy.robots_txt.is_allowed(
                    frontier_item['url']
                )
                if not robots_ok:
                    self._pending_count -= 1
                    frontier_item = None
                    continue
                if self.policy.authentication.is_enabled():
                    domain = urlparse(frontier_item['url']).hostname
                    if domain not in self._authenticated_domains:
                        await self._try_login(domain)
                        self._authenticated_domains.add(domain)
                download_request = DownloadRequest(
                    job_id=self.id,
                    url=frontier_item['url'],
                    cost=frontier_item['cost'],
                    policy=self.policy,
                    output_queue=self._save_queue,
                    cookie_jar=self._cookie_jar
                )
                await self._rate_limiter.push(download_request)
        except asyncio.CancelledError:
            # Put the frontier item back on the frontier
            if frontier_item is not None:
                logger.info('Putting 1 incomplete item back in the frontier.')
                async with self._db_pool.connection() as conn:
                    await r.table('frontier').insert(frontier_item).run(conn)
                    self._frontier_size += 1

    async def run_limits(self):
        '''
        This task periodically checks the crawl progress to see if any crawl
        limits have been exceeded. If they have, then this task ends the crawl.

        This task can't cancel itself, so we use ``daemon_task`` to spawn a new
        task to cancel the crawler's tasks.
        '''

        while True:
            if self._pending_count == 0 and self._frontier_size == 0 \
                and self._extraction_size == 0:
                logger.info('Job %s has no more items pending.', self.id[:8])
                daemon_task(self._complete(graceful=True))
            elif self.policy.limits.exceeds_max_duration(
                (datetime.now(tzlocal()) - self._started_at).seconds):
                logger.info('Job %s has exceeded duration limit.', self.id[:8])
                daemon_task(self._complete(graceful=False))

            await asyncio.sleep(1)

    async def run_save(self):
        '''
        This task takes items off the save queue, loads them into the database,
        and pushes responses bodies to the extraction queue.
        '''
        while True:
            response = await self._save_queue.get()

            if response.should_save:
                body_id = await self._save_response(response)
                await self._update_job_stats(response)
            else:
                body_id = None

            if body_id is not None:
                self._extraction_size += 1
                insert = r.table('extraction_queue').insert({
                    'body_id': body_id,
                    'content_type': response.content_type,
                    'cost': response.cost,
                    'job_id': self.id,
                    'url': response.url,
                })
                async with self._db_pool.connection() as conn:
                    await insert.run(conn)


            self._pending_count -= 1
            self._save_queue.task_done()

            # Enforce the crawl item limit (if applicable). This task can't
            # cancel itself, so we have to cancel the crawl in a separate task.
            if self.policy.limits.exceeds_max_items(self.item_count):
                logger.info('Job %s has exceeded items limit.', self.id[:8])
                daemon_task(self._complete(graceful=False))

    async def start(self):
        ''' Start the job. '''
        try:
            job_update = {}
            frontier_item = None

            if self._run_state == 'pending':
                seeds = list()
                self._cookie_jar = CookieJar()
                for seed in self.seeds:
                    download_request = DownloadRequest(
                        job_id=self.id,
                        url=seed,
                        cost=1.0,
                        policy=self.policy,
                        output_queue=self._save_queue,
                        cookie_jar=self._cookie_jar
                    )
                    seeds.append(download_request)
                await self._add_frontier_items(seeds)
                self._run_state = 'running'
                self._started_at = datetime.now(tzlocal())
                job_update['started_at'] = self._started_at
            elif self._run_state == 'paused':
                self._run_state = 'running'
            else:
                raise Exception('Cannot start or resume a job with run_state={}'
                    .format(self._run_state))

            job_update['run_state'] = self._run_state

            async with self._db_pool.connection() as conn:
                query = r.table('job').get(self.id).update(job_update)
                await query.run(conn)
        except asyncio.CancelledError:
            # If cancelled during startup, then don't do anything
            pass

        self._extraction_task = daemon_task(self.run_extractor())
        self._frontier_task = daemon_task(self.run_frontier())
        self._limits_task = daemon_task(self.run_limits())
        self._save_task = daemon_task(self.run_save())
        logger.info('Job id={} is running...'.format(self.id[:8]))

    async def _add_frontier_items(self, frontier_items):
        '''
        Add a list of ``FrontierItem`` to the frontier.

        If a URL has been seen before, then that item is silently ignored.
        '''
        insert_items = list()

        for frontier_item in frontier_items:
            url = frontier_item.url
            url_can = w3lib.url.canonicalize_url(url).encode('ascii')
            url_hash = hashlib.blake2b(url_can, digest_size=16).digest()

            if url_hash not in self._frontier_seen:
                logger.debug('Adding URL %s (cost=%0.2f)',
                    frontier_item.url, frontier_item.cost)
                insert_items.append({
                    'cost': frontier_item.cost,
                    'job_id': self.id,
                    'url': frontier_item.url,
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

    async def _extract(self, extract_doc):
        ''' Find links in a response body and put them in the frontier. '''
        if extract_doc['join']['is_compressed']:
            body = gzip.decompress(extract_doc['join']['body'])
        else:
            body = extract_doc['join']['body']

        extract_item = ExtractItem(
            extract_doc['url'],
            extract_doc['cost'],
            extract_doc['content_type'],
            body,
        )

        logger.debug('Extracting links from %s', extract_item.url)

        extracted_urls = await asyncio.get_event_loop().run_in_executor(
            None,
            extract_urls,
            extract_item
        )
        frontier_items = list()
        counter = 0

        for url in extracted_urls:
            new_cost = self.policy.url_rules.get_cost(extract_item.cost, url)
            exceeds_max_cost = self.policy.limits.exceeds_max_cost(new_cost)
            if (new_cost > 0 and not exceeds_max_cost):
                frontier_items.append(FrontierItem(url, new_cost))

            # Don't monopolize the event loop:
            counter += 1
            if counter % 100 == 0:
                await asyncio.sleep(0)

        await self._add_frontier_items(frontier_items)

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
                    self._frontier_size -= 1
                    self._pending_count += 1
                    break
                except ReqlNonExistenceError:
                    await asyncio.sleep(1)

        logger.debug('Popped %s', result['url'])
        return result

    async def _save_response(self, response):
        '''
        Save a response to the database.

        Returns the (new or existing) body ID.
        '''
        response_doc = {
            'completed_at': response.completed_at,
            'cost': response.cost,
            'duration': response.duration.total_seconds(),
            'insert_sequence': self._insert_item_sequence,
            'job_id': self.id,
            'started_at': response.started_at,
            'url': response.url,
            'url_can': response.url_can,
        }

        if response.exception is None:
            response_doc['completed_at'] = response.completed_at
            response_doc['content_type'] = response.content_type
            response_doc['is_success'] = response.status_code // 100 == 2
            response_doc['status_code'] = response.status_code
            compress_body = self._should_compress_body(response)

            headers = list()
            for key, value in response.headers.items():
                headers.append(key.upper())
                headers.append(value)
            response_doc['headers'] = headers

            if compress_body:
                body = gzip.compress(response.body, compresslevel=6)
            else:
                body = response.body

            body_hash = hashlib.blake2b(body, digest_size=32) \
                               .digest()

            response_doc['body_id'] = body_hash
            response_body_doc = {
                'id': body_hash,
                'body': body,
                'is_compressed': compress_body,
            }
        else:
            response_doc['exception'] = response.exception
            response_doc['is_success'] = False
            body = None
            body_hash = None

        async with self._db_pool.connection() as conn:
            if body is not None:
                body_query = (
                    r.table('response_body')
                     .get(body_hash)
                     .pluck('id')
                     .default(None)
                )
                existing_body = await body_query.run(conn)
                if existing_body is None:
                    await (
                        r.table('response_body')
                         .insert(response_body_doc)
                         .run(conn)
                    )

            await r.table('response').insert(response_doc).run(conn)
            self._insert_item_sequence += 1

        return body_hash

    def _should_compress_body(self, response):
        '''
        Returns true if the response body should be compressed.

        This is pretty naive right now (only compress text/* responses), but we
        can make it smarter in the future.
        '''
        type_, subtype, parameters = mimeparse.parse_mime_type(
            response.content_type)
        return type_ == 'text'

    async def _stop(self, graceful=True):
        '''
        Stop the job.

        If ``graceful`` is ``True``, then this will wait for the job's open
        downloads to finish before returning, and items removed from the rate
        limiter will be placed back into the crawl frontier.
        '''
        if self._save_task is None:
            logger.warning("Tried to stop a job that wasn't running")
            return

        await cancel_futures(
            self._extraction_task,
            self._frontier_task,
            self._limits_task,
        )

        removed_items = await self._rate_limiter.remove_job(self.id)
        await self._downloader.remove_job(self.id, finish_downloads=graceful)

        if graceful and len(removed_items) > 0:
            insert_items = list()

            for removed_item in removed_items:
                insert_items.append({
                    'cost': removed_item.cost,
                    'job_id': self.id,
                    'url': removed_item.url,
                })

            logger.info('Moving %d items from rate limiter back to frontier.',
                len(insert_items))
            async with self._db_pool.connection() as conn:
                await r.table('frontier').insert(insert_items).run(conn)
                self._frontier_size += len(insert_items)

        await self._save_queue.join()
        await cancel_futures(self._save_task)
        self.stopped.set_result(True)

    async def _try_login(self, domain):
        ''' Attempt a login for the given domain. '''
        async with self._db_pool.connection() as conn:
            login = await (
                r.table('domain_login')
                 .get(domain)
                 .run(conn)
            )

        if login is None:
            return

        user = random.choice(login['users'])
        mask_pass = user['password'][:2] + '******'
        logger.info('Attempting login for domain=%s with user=%s password=%s',
            domain, user['username'], mask_pass)
        output_queue = asyncio.Queue()
        request = DownloadRequest(self.id, login['login_url'], 1.0, self.policy,
            output_queue, self._cookie_jar)
        await self._rate_limiter.push(request)
        response = await output_queue.get()
        try:
            loop = asyncio.get_event_loop()
            action, method, data = await loop.run_in_executor(None,
                get_login_form, response, user['username'], user['password'])
        except Exception as e:
            logger.error("Exception during login: {}".format(str(e)))
            return
        logger.info('Login action=%s method=%s data=%r', action, method, data)
        request = DownloadRequest(self.id, action, 1.0, self.policy,
            output_queue, self._cookie_jar, method=method, form_data=data)
        await self._rate_limiter.push(request)
        response = await output_queue.get()

    async def _update_job_stats(self, response):
        '''
        Update job stats with this response.

        This function *should* make an atomic change to the database, e.g.
        no competing task can partially update stats at the same time as this
        task.
        '''
        status = str(response.status_code)
        status_first_digit = status[0]
        new_data = {'item_count': r.row['item_count'] + 1}
        self.item_count += 1

        if response.exception is None:
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
