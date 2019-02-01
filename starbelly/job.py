from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import functools
import gzip
import hashlib
import itertools
import logging
import pickle
import random
import time
from yarl import URL

from aiohttp.cookiejar import CookieJar
import mimeparse
from operator import itemgetter
from rethinkdb import RethinkDB
from rethinkdb.errors import ReqlNonExistenceError
from yarl import URL

from .downloader import Downloader, DownloadRequest
from .policy import Policy
from .version import __version__


@dataclass
class JobStatusNotification:
    '''  Contains status for a job. '''
    job_id: bytes
    schedule_id: bytes
    status: str
    datetime: datetime


@dataclass
class JobStateEvent:
    ''' Indicates a change in a job's run_state. '''
    job_id: bytes
    run_state: str


class CrawlStateProxy:
    ''' A proxy object that exposes the state of crawl jobs. '''
    def __init__(self, job_states):
        '''
        Constructor

        :param dict job_states: A dictionary keyed by job_id where each
            value is dictionary containing state for one job.
        '''
        self._job_states = job_states

    def __getitem__(self, job_id):
        '''
        Return a copy of job state for a given job ID.

        :param bytes job_id:
        '''
        return self._job_states[job_id].copy()

    def __iter__(self):
        return _CrawlStateProxyIter(self._job_states)


class _CrawlStateProxyIter:
    ''' An iterator for job states. '''
    def __init__(self, job_states):
        '''
        Constructor

        :param dict job_states: A dictionary keyed by job_id where each
            value is dictionary containing state for one job.
        '''
        self._job_states = job_states
        self._iter = iter(self._job_states.items())

    def __next__(self):
        ''' Get next job state. '''
        job_id, job_dict = next(self._iter)
        return job_id, job_dict.copy()

# TODO
#
# Taken out of schedule.py. Needs to be moved into crawl manager. Connect to
# the schedule with a send channel and receive channel. When job status changes,
# send events to the channel. Start a task to listen for events on the receive
# channel: these tell us when to start new jobs.
#
# async def listen_finished(self):
#     '''
#     Listen for jobs that finish, and then check if they should be
#     re-scheduled.

#     :returns: This method runs until cancelled.
#     '''
#     job_query = (
#         r.table('job')
#          .pluck('run_state', 'schedule_id')
#          .changes()
#          .pluck('new_val')
#     )
#     async with self._db_pool.connection() as conn:
#         feed = await job_query.run(conn)
#         async for change in feed:
#             job = change['new_val']
#             if job is None:
#                 continue
#             if job['run_state'] in ('cancelled', 'completed') and \
#                 'schedule_id' in job:
#                 schedule_query = self._get_schedule_query(
#                     job['schedule_id'])
#                 schedule = await schedule_query.run(conn)
#                 if schedule['timing'] == 'AFTER_PREVIOUS_JOB_FINISHED':
#                     self.schedule_next_event(schedule)
#                     self._schedule_changed.set()


# def _get_schedule_query(self, schedule_id=None):
#     '''
#     Construct a query for getting active schedules.

#     If schedule_id is provided, then the query returns a single schedule.
#     Otherwise, running this query returns a cursor.
#     '''
#     def get_job(schedule):
#         return {
#             'latest_job': r.branch(
#                 schedule.has_fields('latest_job_id'),
#                 r.table('job')
#                  .get(schedule['latest_job_id'])
#                  .pluck('run_state', 'started_at', 'completed_at'),
#                 None
#             ),
#         }

#     query = r.table('job_schedule')

#     if schedule_id is None:
#         query = query.filter({'enabled': True})
#     else:
#         query = query.get(schedule_id)

#     return query.merge(get_job)


    # async def _start_scheduled_job(self, schedule_id):
    #     '''
    #     Start a job that is ready to run.

    #     :param bytes schedule_id:
    #     '''
    #     async with self._db_pool.connection() as conn:
    #         query = self._get_schedule_query(schedule_id)
    #         schedule = await query.run(conn)

    #     # If a job is already running, cancel it.
    #     latest_job = schedule['latest_job']
    #     if latest_job is not None and \
    #         latest_job['run_state'] not in ('cancelled', 'completed'):
    #         await self._crawl_manager.cancel_job(schedule['latest_job_id'])

    #     # Start a new job for this schedule.
    #     name = _format_job_name(schedule['job_name'],
    #         datetime.now(timezone.utc), schedule['job_count'])

    #     job_id = await self._crawl_manager.start_job(
    #         schedule['seeds'],
    #         schedule['policy_id'],
    #         name,
    #         schedule['tags'],
    #         schedule['id']
    #     )

    #     async with self._db_pool.connection() as conn:
    #         await r.table('job_schedule').get(schedule_id).update({
    #             'latest_job_id': job_id,
    #             'job_count': schedule['job_count'] + 1,
    #         }).run(conn)

    #     # If the schedule runs at regular intervals, then reschedule it now.
    #     if schedule['timing'] == 'REGULAR_INTERVAL':
    #         async with self._db_pool.connection() as conn:
    #             query = self._get_schedule_query(schedule_id)
    #             schedule = await query.run(conn)
    #             self.schedule_next_event(schedule)


logger = logging.getLogger(__name__)
r = RethinkDB()


# class CrawlRegistry(self):
#     ''' This class keeps tracks of running jobs. '''
#     def __init__(self, send_channel, recv_channel):
#         ''' Constructor. '''
#         self._jobs = dict()
#         self._send_channel = send_channel
#         self._recv_channel = recv_channel

#     @property
#     def stats(self):
#         '''
#         Return mapping of {job_id: job_stats} containing all running jobs.

#         :rtype: dict
#         '''
#         return {job_id, job.stats for job_id, job in self._jobs.items()}

#     def add_job(self, job):
#         '''
#         Add a job to the registry.

#         :param CrawlJob job:
#         '''
#         self._jobs[job.id] = job

#     def get_send_channel(self):
#         '''
#         Get a channel that a job can send status updates to.

#         :rtype trio.MemoryChannel:
#         '''
#         return self._send_channel.clone()

#     def remove_job(self, job):
#         '''
#         Remove a job from the registry.

#         :param CrawlJob job:
#         '''
#         del self._jobs[job.id]


async def clear_dangling_response_bodies(db_pool):
    '''
    Response bodies are deduplicated and stored in a separate table from
    response metadata. When a job is deleted, only the response metadata is
    removed. This method finds response bodies that are dangling (not
    referred to by any existing response) and removes them.

    Note: this is a very slow operation because it has to iterate over all
    existing response bodies. This should only be run periodically.

    :param db_pool: A RethinkDB connection pool.
    '''
    def dangling(body):
        responses = r.table('response').get_all(body['id'], index='body_id')
        return  responses.count().eq(0)
    query = r.table('response_body').order_by('id').filter(dangling).delete()
    async with db_pool.connection() as conn:
        await query.run(conn)


class CrawlJob:
    ''' Manages job state. '''
    def __init__(self, job_doc, sequence, db_pool, send_to_rate_limiter,
            receive_from_rate_limiter, downloader_semaphore):
        '''
        Constructor.

        :param bytes job_id: ID for this job, or None if its a new job.
        :param str name: Name for this job.
        '''
        self._id = job_doc['id']
        self._name = job_doc['name']
        self._tags = job_doc['tags']
        self._seeds = job_doc['seeds']
        self._policy = policy
        self._sequence = sequence
        self._db_pool = db_pool
        self._rate_limiter = rate_limiter

        # Create job components and wire them together.
        frontier_send = send_to_rate_limiter
        downloader_recv = receive_from_rate_limiter
        downloader_send, storage_recv = trio.open_memory_channel(0)
        storage_send, extractor_recv = trio.open_memory_channel(0)
        self._frontier = CrawlFrontier(frontier_send)
        self._download = Downloader(downloader_send, downloader_recv,
            downloader_semaphore)
        self._extractor = CrawlExtractor(extractor_recv)
        self._storage = CrawlStorage(storage_send, storage_recv)

        self._db_pool = db_pool
        self._run_state = 'pending'
        self._state = {
            'name': name,
            'seeds': seeds,
            'tags': [],
            'item_count': 10,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {},
            'started_at': None,
            'completed_at': None,
            'run_state': 'PENDING',
        }
        self._stats = {
            'frontier': 0,
            'pending': 0,
            'extraction': 0,
            'downloader': 0,
        }
        self._started_at = None
        self._cancel_scope = None
        self._stopped = trio.Event()

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<CrawlJob job_id={}>'.format(self._job_id[:8])

    @property
    def state(self):
        return CrawlStateProxy(self._state)

    @property
    def stats(self):
        return CrawlStateProxy(self._stats)

    async def cancel(self):
        '''
        Cancel this job.

        A cancelled job is similar to a paused job but cannot be resumed.
        '''
        logger.info('%r Canceling…'.format(self))
        await self._stop()

        cancel_query = (
            r.table('job')
             .get(self.id)
             .update({
                'authenticated_domains': None,
                'cookie_jar': None,
                'run_state': 'cancelled',
                'completed_at': datetime.now(timezone.utc)
             })
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
            await extraction_query.run(conn)

        logger.info('%r Cancelled'.format(self))

    async def pause(self):
        '''
        Pause this job.

        A paused job may be resumed later.
        '''
        logger.info('%r Pausing…'.format(self))
        await self._stop()

        self._run_state = 'paused'
        query = (
            r.table('job')
             .get(self.id)
             .update({
                'authenticated_domains': list(self._authenticated_domains),
                'cookie_jar': pickle.dumps(self._cookie_jar._cookies),
                'extraction_size': self._extraction_size,
                'frontier_seen': pickle.dumps(self._frontier_seen),
                'frontier_size': self._frontier.size,
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
        logger.info('%r Paused'.format(self))

    async def resume(self, job_data):
        ''' On resume, restore crawl state.
        TODO Make this private? make an initialize function that handles new jobs,
        then this handles resume jobs '''

        # TODO copied from crawl manager
        async with self._db_pool.connection() as conn:
            job_data = await r.table('job').get(job_id).run(conn)
            if job_data['policy'].get('captcha_solver_id') is not None:
                job_data['policy']['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(job_data['policy']['captcha_solver_id'])
                     .run(conn)
                )
                del job_data['policy']['captcha_solver_id']
        policy = Policy(job_data['policy'], __version__, job_data['seeds'],
            self._robots_txt_manager)
        job = _CrawlJob(job_data['id'], job_data['name'], job_data['seeds'],
            policy, self._db_pool, self._rate_limiter)
        await job.resume(job_data)
        self._running_jobs[job.id] = job

        self.item_count = job_data['item_count']
        self._authenticated_domains = set(job_data['authenticated_domains'])
        self._cookie_jar = CookieJar()
        self._cookie_jar._cookies = pickle.loads(job_data['cookie_jar'])
        self._insert_item_sequence = job_data['insert_item_sequence']
        self._extraction_size = job_data['extraction_size']
        self._frontier_seen = pickle.loads(job_data['frontier_seen'])
        self._frontier_size = job_data['frontier_size']
        self._run_state = job_data['run_state']
        self._started_at = job_data['started_at']
        await self.start()

    async def run(self):
        '''
        Run the job. This will start a pending job or resume a paused job.

        :returns: This function runs until cancelled.
        '''
        # TODO add to crawl registry
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
                        output_queue=self._save_queue
                    )
                    seeds.append(download_request)
                await self._add_frontier_items(seeds)
                self._run_state = 'running'
                self._started_at = datetime.now(timezone.utc)
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

        async with trio.open_nursery() as nursery:
            self._cancel_scope = nursery.cancel_scope
            nursery.start_soon(self._frontier.run)
            nursery.start_soon(self._extractor.run)
            nursery.start_soon(self._storage.run)
            logger.info('%r Running...'.format(self))

            # After starting background tasks, this task checks to see if any
            # crawl limits have been exceeded.
            while True:
                if self._pending_count == 0 and self._frontier.size == 0 \
                        and self._extraction_size == 0:
                    logger.info('%r No more items pending.', self)
                    daemon_task(self._complete(graceful=True))
                elif self.policy.limits.exceeds_max_duration(
                        (datetime.now(timezone.utc) - self._started_at).seconds):
                    logger.info('%r Exceeded duration limit.', self)
                    daemon_task(self._complete(graceful=False))

                await trio.sleep(1)
        self._stopped.set()


    async def _complete(self, graceful=True):
        ''' Update state to indicate this job is complete. '''

        await self._stop(graceful)
        self._run_state = 'completed'
        completed_at = datetime.now(timezone.utc)

        new_data = {
            'run_state': self._run_state,
            'completed_at': completed_at,
            'duration': completed_at - r.row['started_at'],
        }

        async with self._db_pool.connection() as conn:
            query = r.table('job').get(self.id).update(new_data)
            await query.run(conn)

        logger.info('%r Completed.'.format(self.id[:8]))

    async def _new(self):
        # TODO copied from crawl manager
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
            'http_status_counts': {},
        }

        if schedule_id is not None:
            job_data['schedule_id'] = schedule_id

        async with self._db_pool.connection() as conn:
            policy = await r.table('policy').get(policy_id).run(conn)
            job_data['policy'] = policy
            result = await r.table('job').insert(job_data).run(conn)
            if policy.get('captcha_solver_id') is not None:
                policy['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(policy['captcha_solver_id'])
                     .run(conn)
                )
                del policy['captcha_solver_id']

        policy = Policy(policy, __version__, seeds, self._robots_txt_manager)
        job_id = result['generated_keys'][0]
        job = _CrawlJob(self._db_pool, self._rate_limiter, self._downloader,
            job_id, seeds, policy, name)
        self._running_jobs[job.id] = job
        await job.start()
        return job.id

    async def _stop(self):
        '''
        Implements the shared behavior between ``pause()`` and ``cancel()``.
        '''
        # TODO remove from crawl registry
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception('Cannot cancel job because it has not started')
        await self._stopped.wait()

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
