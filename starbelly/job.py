from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
import trio
from yarl import URL

from .login import LoginManager
from .downloader import CrawlItemLimitExceeded, Downloader, DownloadRequest
from .extractor import CrawlExtractor
from .frontier import CrawlFrontier, FrontierExhaustionError
from .policy import Policy
from .storage import CrawlStorage
from .version import __version__


logger = logging.getLogger(__name__)
r = RethinkDB()


class CrawlDurationExceeded(Exception):
    ''' The crawl duration limit has been exceeded. '''


class RunState:
    '''
    Lists the allowable run states for a job.

    Unlike an enum, the values are also strings, because these get stored in the
    database and strings are easier to debug than integers.
    '''
    PENDING = 'pending'
    PAUSED = 'paused'
    RUNNING = 'running'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'


@dataclass
class JobStateEvent:
    '''  Contains status for a job. '''
    job_id: str
    schedule_id: str
    run_state: RunState
    event_time: datetime


@dataclass
class StatsTracker:
    ''' Statistics about job progress like number of items downloaded. '''
    def __init__(self):
        self._jobs = dict()

    def add_job(self, stats_doc):
        self._jobs[stats_doc['id']] = stats_doc

    def complete_job(self, job_id, completed_at):
        self._jobs[job_id]['completed_at'] = completed_at

    def set_run_state(self, job_id, run_state):
        self._jobs[job_id]['run_state'] = run_state

    def snapshot(self):
        '''
        Return a copy of stats for all running and recent crawls.

        Remove any crawls that are over an hour old.

        :rtype list:
        '''
        jobs = list()
        to_remove = list()
        for job_id, job in self._jobs.items():
            completed_at = job.get('completed_at')
            now = datetime.now(timezone.utc)
            if completed_at and now - timedelta(hours=1) > completed_at:
                to_remove.append(job_id)
                continue
            jobs.append({
                'id': job['id'],
                'name': job['name'],
                'run_state': job['run_state'],
                'seeds': job['seeds'].copy(),
                'tags': job['tags'].copy(),
                'started_at': job['started_at'],
                'completed_at': job['completed_at'],
                'item_count': job['item_count'],
                'http_success_count': job['http_success_count'],
                'http_error_count': job['http_error_count'],
                'exception_count': job['exception_count'],
                'http_status_counts': job['http_status_counts'].copy(),
            })
        for job_id in to_remove:
            del self._jobs[job_id]
        return jobs


class CrawlManager:
    ''' Manage crawl jobs and provide introspection into their states. '''
    def __init__(self, db_pool, rate_limiter, stats_tracker):
        self._db_pool = db_pool
        self._rate_limiter = rate_limiter
        self._stats_tracker = stats_tracker

        self._download_capacity = 20
        self._download_semaphore = trio.Semaphore(self._download_capacity)
        self._jobs = dict()
        self._job_state_channels = dict()
        self._nursery = None
        self._sequence = None

    def __repr__(self):
        ''' Customize repr. '''
        return '<CrawlManager>'

    async def cancel_job(self, job_id):
        '''
        Stop the specified job if it is currently running and set it to
        cancelled in the database.

        :param str job_id:
        '''
        logger.info('%r Cancelling job_id=%s…', self, job_id[:8])
        try:
            # If the job is currently running, stop it.
            await self._jobs.pop(job_id).stop()
        except KeyError:
            pass

        completed_at = datetime.now(timezone.utc)

        run_state = RunState.CANCELLED
        job_query = (
            r.table('job')
             .get(job_id)
             .update({
                'run_state': run_state,
                'completed_at': completed_at
             })
        )

        schedule_query = r.table('job').get(job_id).pluck('schedule_id')

        frontier_query = (
            r.table('frontier')
             .between((job_id, r.minval, r.minval),
                      (job_id, r.maxval, r.maxval),
                      index='cost_index')
             .delete()
        )

        async with self._db_pool.connection() as conn:
            await job_query.run(conn)
            await frontier_query.run(conn)
            schedule_id = await schedule_query.run(conn)

        self._stats_tracker.set_run_state(job_id, run_state)
        event = JobStateEvent(job_id=self.job_id, schedule_id=schedule_id,
            run_state=run_state, datetime=completed_at)
        self._send_job_state_event(event)
        logger.info('%r Cancelled job_id=%s', self, job_id[:8])

    def get_job_state_channel(self, size=10):
        '''
        Open a new job state channel.

        JobStateEvent objects will be sent to this channel when a job changes
        state. When the channel is full, state events will not be sent, so
        consumers need to read events continually.

        :param int size: The size of the channel.
        :rtype: trio.ReceiveChannel
        '''
        send_channel, recv_channel = trio.open_memory_channel(size)
        self._job_state_channels[recv_channel] = send_channel
        return recv_channel

    def get_resource_usage(self):
        '''
        Return statistics about crawler resource usage, i.e. concurrent
        downloads.

        :rtype dict:
        '''
        jobs = list()
        for job in self._jobs.values():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'current_downloads': job.current_downloads,
            })
        max_ = self._download_semaphore.max_value
        return {
            'current_downloads': max_ - self._download_semaphore.value,
            'maximum_downloads': max_,
            'jobs': jobs,
        }
        return stats

    async def pause_job(self, job_id):
        '''
        Stop the specified job and set it to paused in the database.

        :param str job_id:
        '''
        logger.info('%r Pausing job_id=%s…', self, job_id[:8])
        job = self._jobs.pop(job_id)
        await job.stop()

        run_state = RunState.PAUSED
        job_query = (
            r.table('job')
             .get(self.id)
             .update({
                'run_state': run_state,
                'old_urls': job.old_urls,
             })
        )

        async with self._db_pool.connection() as conn:
            await job_query.run(conn)
            await frontier_query.run(conn)

        self._stats_tracker.set_run_state(job_id, run_state)
        event = JobStateEvent(job_id=self.job.id, schedule_id=job.schedule_id,
            run_state=run_state, datetime=datetime.now(timezone.utc))
        self._send_job_state_event(event)
        logger.info('%r Paused job_id=%s', self, job_id[:8])

    async def resume_job(self, job_id):
        '''
        Resume a paused job: load it from the database and run it.

        :param str job_id: The ID of the job to resume.
        '''
        logger.info('%r Resuming job_id=%s…', self, job_id[:8])
        job_query = r.table('job').get(job_id)
        async with self._db_pool.connection() as conn:
            job_doc = await job_query.run(conn)
            policy_doc = job_doc['policy']
            captcha_solver_id = policy_doc.get('captcha_solver_id')
            if captcha_solver_id:
                policy_doc['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(captcha_solver_id)
                     .run(conn)
                )
                del policy_doc['captcha_solver_id']

        policy = Policy(policy_doc, __version__, seeds)
        job = self._make_job(job_doc)
        self._nursery.start_soon(self._run_job, job)
        logger.info('%r Resumed job_id=%s', self, job_id[:8])

    async def run(self, *, task_status=trio.TASK_STATUS_IGNORED):
        '''
        Run the crawl manager.

        You should call ``await nursery.start(crawl_manager.run)`` to ensure
        that the crawl manager is ready before calling any of its job methods.

        :returns: This function runs until cancelled.
        '''
        sequence_query = r.table('response').max(index='sequence')
        async with self._db_pool.connection() as conn:
            try:
                max_sequence = await sequence_query.run(conn)
            except r.RuntimeError:
                max_sequence = 0
            self._sequence = itertools.count(start=max_sequence + 0)
            logger.info('%r Sequence initialized to %s', self, self._sequence)

        async with trio.open_nursery() as nursery:
            self._nursery = nursery
            task_status.started()
            await trio.sleep_forever()

    async def start_job(self, name, seeds, tags, policy_id, schedule_id=None):
        '''
        Start a new job.

        This adds the job to the database and runs it.

        :param str name: The name of the new job.
        :param list[str] seeds: A list of seeds.
        :param list[str] tags: A list of tags.
        :param str policy_id: The ID of the policy to apply to this job.
        :param str schedule_id: (Optional) The schedule that started this job.
        :returns: The new job ID.
        :rtype: str
        '''
        job_doc = {
            'name': name,
            'seeds': seeds,
            'tags': tags,
            'run_state': RunState.PENDING,
            'started_at': datetime.now(timezone.utc),
            'completed_at': None,
            'duration': None,
            'item_count': 0,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {},
        }

        if schedule_id is not None:
            job_doc['schedule_id'] = schedule_id

        async with self._db_pool.connection() as conn:
            # Set up the job in the database.
            policy_doc = await r.table('policy').get(policy_id).run(conn)
            job_doc['policy'] = policy_doc
            result = await r.table('job').insert(job_doc).run(conn)
            job_id = result['generated_keys'][0]
            job_doc['id'] = job_id
            if policy_doc.get('captcha_solver_id') is not None:
                policy_doc['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(policy['captcha_solver_id'])
                     .run(conn)
                )
                del policy_doc['captcha_solver_id']

            # Add seeds to the frontier.
            frontier_items = list()
            for seed in seeds:
                frontier_items.append({
                    'cost': 0,
                    'job_id': job_id,
                    'url': seed,
                })
            await r.table('frontier').insert(insert_items).run(conn)

        policy = Policy(policy_doc, __version__, seeds)
        job = self._make_job(job_doc)
        self._nursery.start_soon(self._run_job, job)
        return job_id

    async def _make_job(self, job_doc):
        '''
        Create a job instance.

        :param dict job_doc: A database document.
        :param set seen_urls: A
        :rtype: CrawlJob
        '''
        job_id = job_doc['id']
        policy = Policy(job_doc['policy'], __version__, job_doc['seeds'])
        try:
            old_urls = pickle.load(job_doc['old_urls'])
        except KeyError:
            # If old URLs are not in the job_doc, then this is a new job and
            # we should intialize old_urls to the seed URLs.
            old_urls = set()
            for seed in job_doc['seeds']:
                url_can = policy.url_normalization.normalize(seed)
                hash_ = hashlib.blake2b(url_can.encode('ascii'), digest_size=16)
                old_urls.add(hash_.digest())

        # Set up channels
        frontier_send = self._rate_limiter.get_request_channel()
        rate_limiter_reset = self._rate_limiter.get_reset_channel()
        downloader_recv = self._rate_limiter.add_job(job_id)
        downloader_send, storage_recv = trio.open_memory_channel(0)
        storage_send, extractor_recv = trio.open_memory_channel(0)

        # Set up crawling components.
        stats_dict = {
            'job_id': job_id,
            'run_state': job_doc['run_state'],
            'name': job_doc['name'],
            'seeds': job_doc['seeds'],
            'tags': job_doc['tags'],
            'started_at': job_doc['started_at'],
            'completed_at': job_doc['completed_at'],
            'item_count': job_doc['item_count'],
            'http_success_count': job_doc['http_success_count'],
            'http_error_count': job_doc['http_error_count'],
            'exception_count': job_doc['exception_count'],
            'http_status_counts': job_doc['http_status_counts'],
        }
        self._stats_tracker.add_job(stats_dict)
        login_manager = LoginManager(job_id, db_pool, downloader)
        downloader = Downloader(job_id, policy, downloader_send,
            downloader_recv, self._download_semaphore, rate_limiter_reset,
            stats_dict)
        frontier = CrawlFrontier(job_id, self._db_pool, frontier_send,
            login_manager, policy)
        storage = CrawlStorage(job_id, db_pool, storage_send, storage_recv,
            policy, self._sequence)
        extractor = CrawlExtractor(job_id, extractor_recv, policy, old_urls)

        # Now we can create a job instance.
        return CrawlJob(job_doc['name'], job_id, job_doc.get('schedule_id'),
            frontier, downloader, storage, extractor, stats)

    async def _run_job(self, job):
        '''
        Add a job to the internal list of running jobs and then run it. When
        it completes, remove it from the list of internal jobs and update its
        status.
        '''
        # Update local state to indicate that the job is running:
        run_state = RunState.RUNNING
        query = r.table('job').get(job.id).update({'run_state': run_state})
        async with self._db_pool.connection() as conn:
            await query.run(conn)
        self._running_jobs[job.id] = job
        self._stats_tracker.set_run_state(job_id, run_state)
        event = JobStateEvent(job_id=self.job.id, schedule_id=job.schedule_id,
            run_state=run_state, datetime=datetime.now(timezone.utc))
        self._send_job_state_event(event)
        job_completed = False

        try:
            await job.run()
        except (CrawlDurationExceeded, CrawlItemLimitExceeded,
                FrontierExhaustionError) as exc:
            logger.info('<CrawlManager> job_id=%s finished %s', job.id[:8],
                exc)
            job_completed = True

        # When job finishes, update database and cleanup local state:
        del self._jobs[job.id]
        self._rate_limiter.remove_job(job.id)
        if job_completed:
            completed_at = datetime.now(timezone.utc)
            run_state = RunState.COMPLETED
            new_data = {
                'run_state': run_state,
                'completed_at': completed_at,
                'duration': completed_at - r.row['started_at'],
            }
            job_query = r.table('job').get(job.id).update(new_data)
            frontier_query = (
                r.table('frontier')
                 .order_by(index='cost_index')
                 .between((self.id, r.minval, r.minval),
                          (self.id, r.maxval, r.maxval))
                 .delete()
            )
            async with self._db_pool.connection() as conn:
                await job_query.run(conn)
                await frontier_query.run(conn)
            self._stats_tracker.set_run_state(job.id, run_state)
            self._stats_tracker.complete_job(job.id, completed_at)
            event = JobStateEvent(self.job.id, job.schedule_id, run_state,
                completed_at)
            self._send_job_state_event(event)
            logger.info('%r Completed job id=%s', self, job.id[:8])

    def _send_job_state_event(self, event):
        '''
        Send a job state event to all listeners.

        If a listener's channel is full, then the event is not sent to that
        listener. If the listener's channel is closed, then that channel is
        removed and will not be sent to in the future.

        :param JobStateEvent event:
        '''
        to_remove = list()
        for recv_channel, send_channel in self._job_state_channels.items():
            try:
                send_channel.send_nowait(event)
            except trio.WouldBlock:
                # The channel is full. Drop this message and move on.
                pass
            except trio.BrokenResourceError:
                # The consumer closed the channel. We can remove it from our
                # dict after the loop finishes.
                to_remove.append(recv_channel)
        for recv_channel in to_remove:
            del self._job_state_channels[recv_channel]


class CrawlJob:
    ''' Manages job state. '''
    def __init__(self, name, job_id, schedule_id, frontier, downloader, storage,
            extractor):
        '''
        Constructor.

        :param str name: The name of this job.
        :param str job_id: ID for this job, or None if its a new job.
        :param schedule_id: (Optional) The ID of the schedule associated with
            this job.
        :type schedule_id: str or None
        :param starbelly.frontier.CrawlFrontier frontier: The component that
            manages the crawl priority queue.
        :param starbelly.downloader.Downloader downloader: The component that
            downloads resources.
        :param starbelly.storage.CrawlStorage storage: The component that stores
            crawl results in the database.
        :param starbelly.extractor.CrawlExtractor extractor: The component that
            extracts URLs from downloaded resources and adds them to the crawl
            frontier.
        '''
        self._name = name
        self._job_id = job_id
        self._frontier = frontier
        self._downloader = downloader
        self._storage = storage
        self._extractor = extractor
        self._stats = stats

        self._cancel_scope = None
        self._stopped = trio.Event()

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<CrawlJob job_id={} "{}">'.format(self._job_id[:8], self._name)

    @property
    def completed(self):
        '''
        Indicates if the crawl has completed, i.e. exhausted all possible URLs
        or run into one of the policy-defined limits.

        :rtype: bool
        '''
        return self._completed

    @property
    def current_downloads(self):
        return self._downloader.count

    @property
    def id(self):
        '''
        The job's unique ID.

        :rtype str:
        '''
        return self._job_id

    @property
    def old_urls(self):
        ''' Returns a set of hashed URLs that the crawl has seen before. '''
        return self._extractor.old_urls

    async def run(self):
        '''
        Start all of the subcomponents of the job.

        :returns: When the crawl stops running, return True if the crawl is
            completed or False otherwise.
        :rtype: bool
        '''
        def exc_filter(exc):
            ''' Filter out Cancelled exceptions raised by the nursery. '''
            if isinstance(exc, trio.Cancelled):
                return None
            else:
                return exc

        with trio.MultiError.catch(exc_filter):
            async with trio.open_nursery() as nursery:
                self._cancel_scope = nursery.cancel_scope
                logger.info('%r Running...'.format(self))
                nursery.start_soon(self._frontier.run)
                nursery.start_soon(self._downloader.run)
                nursery.start_soon(self._extractor.run)
                nursery.start_soon(self._storage.run)

                # After starting background tasks, this task enforces the
                # maximum crawl duration.
                if self._policy.limits.max_duration:
                    await trio.sleep(self._policy.limits.max_duration)
                    raise CrawlDurationExceeded()
                else:
                    await trio.sleep_forever()

        self._stopped.set()
        return False

    async def stop(self):
        '''
        Stop the crawl job.
        '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception('Cannot cancel job because it has not started')
        await self._stopped.wait()
