from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import hashlib
import itertools
import logging
import pickle

from rethinkdb import RethinkDB
import trio

from .login import LoginManager
from .downloader import CrawlItemLimitExceeded, Downloader
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


FINISHED_STATES = (RunState.COMPLETED, RunState.CANCELLED)


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


class PipelineTerminator:
    '''
    This class reads all items from a channel and discards them. This is
    handy because each crawling component is part of a pipeline that reads from
    one channel and writes to another. This class can be used to terminate the
    pipeline.
    '''
    def __init__(self, channel):
        '''
        Constructor

        :param trio.ReceiveChannel channel:
        '''
        self._channel = channel

    async def run(self):
        ''' Run the pipeline terminator. '''
        async for _ in self._channel:
            pass


class CrawlManager:
    ''' Manage crawl jobs and provide introspection into their states. '''
    def __init__(self, rate_limiter, stats_tracker, robots_txt_manager,
            crawl_db, frontier_db, extractor_db, storage_db, login_db):
        '''
        Constructor.

        :param starbelly.rate_limiter.RateLimiter rate_limiter: A rate limiter.
        :param StatsTracker stats_tracker: A stats tracking instance.
        :param starbelly.robots.RobotsTxtManager robots_txt_manager: A
            robots.txt manager.
        :param starbelly.db.CrawlManagerDb crawl_db: A database layer.
        :param starbelly.db.CrawlFrontierDb crawl_db: A database layer.
        :param starbelly.db.CrawlExtractorDb crawl_db: A database layer.
        :param starbelly.db.CrawlStorageDb crawl_db: A database layer.
        :param starbelly.db.LoginDb login_db: A database layer.
        '''
        self._rate_limiter = rate_limiter
        self._stats_tracker = stats_tracker
        self._robots_txt_manager = robots_txt_manager
        self._db = crawl_db
        self._frontier_db = frontier_db
        self._extractor_db = extractor_db
        self._storage_db = storage_db
        self._login_db = login_db

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
        run_state = RunState.CANCELLED
        completed_at = datetime.now(timezone.utc)
        await self._db.finish_job(job_id, run_state, completed_at)
        schedule_id = await self._db.clear_frontier(job_id)
        self._stats_tracker.set_run_state(job_id, run_state)
        event = JobStateEvent(job_id, schedule_id, run_state, completed_at)
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
        max_ = self._download_capacity
        return {
            'current_downloads': max_ - self._download_semaphore.value,
            'maximum_downloads': max_,
            'jobs': jobs,
        }

    async def pause_job(self, job_id):
        '''
        Stop the specified job and set it to paused in the database.

        :param str job_id:
        '''
        job = self._jobs[job_id]
        logger.info('%r Pausing job_id=%s…', self, job.id[:8])
        await job.stop()
        run_state = RunState.PAUSED
        old_urls = pickle.dumps(job.old_urls)
        await self._db.pause_job(job.id, old_urls)
        self._stats_tracker.set_run_state(job.id, run_state)
        event = JobStateEvent(job.id, job.schedule_id, run_state,
            datetime.now(timezone.utc))
        self._send_job_state_event(event)
        logger.info('%r Paused job_id=%s', self, job.id[:8])

    async def resume_job(self, job_id):
        '''
        Resume a paused job: load it from the database and run it.

        :param str job_id: The ID of the job to resume.
        '''
        logger.info('%r Resuming job_id=%s…', self, job_id[:8])
        job_doc = await self._db.resume_job(job_id)
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
        max_sequence = await self._db.get_max_sequence()
        self._sequence = itertools.count(start=max_sequence + 1)
        logger.info('%r Sequence initialized to %s', self, max_sequence + 1)

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

        policy_doc = await self._db.get_policy(policy_id)
        job_doc['policy'] = policy_doc
        job_id = await self._db.create_job(job_doc, policy_id)
        job_doc['id'] = job_id
        job = self._make_job(job_doc)
        self._nursery.start_soon(self._run_job, job)
        return job_id

    def _make_job(self, job_doc):
        '''
        Create a job instance.

        :param dict job_doc: A database document.
        :param set seen_urls: A
        :rtype: CrawlJob
        '''
        job_id = job_doc['id']
        policy = Policy(job_doc['policy'], __version__, job_doc['seeds'])
        try:
            old_urls = pickle.loads(job_doc['old_urls'])
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
        extractor_send, pipeline_end = trio.open_memory_channel(0)

        # Set up crawling components.
        stats_dict = {
            'id': job_id,
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
        downloader = Downloader(job_id, policy, downloader_send,
            downloader_recv, self._download_semaphore, rate_limiter_reset,
            stats_dict)
        login_manager = LoginManager(job_id, self._login_db, policy, downloader)
        frontier = CrawlFrontier(job_id, self._frontier_db, frontier_send,
            login_manager, policy, stats_dict)
        storage = CrawlStorage(job_id, self._storage_db, storage_send,
            storage_recv, policy, self._sequence)
        extractor = CrawlExtractor(job_id, self._extractor_db, extractor_send,
            extractor_recv, policy, self._robots_txt_manager, old_urls,
            stats_dict)
        terminator = PipelineTerminator(pipeline_end)

        # Now we can create a job instance.
        return CrawlJob(job_doc['name'], job_id, job_doc.get('schedule_id'),
            policy, frontier, downloader, storage, extractor, terminator)

    async def _run_job(self, job):
        '''
        Add a job to the internal list of running jobs and then run it. When
        it completes, remove it from the list of internal jobs and update its
        status.
        '''
        # Update local state to indicate that the job is running:
        run_state = RunState.RUNNING
        await self._db.run_job(job.id)
        self._jobs[job.id] = job
        self._stats_tracker.set_run_state(job.id, run_state)
        event = JobStateEvent(job.id, job.schedule_id, run_state,
            datetime.now(timezone.utc))
        self._send_job_state_event(event)
        job_completed = False

        try:
            await job.run()
        except (CrawlDurationExceeded, CrawlItemLimitExceeded,
                FrontierExhaustionError) as exc:
            logger.info('<CrawlManager> job_id=%s finished %r', job.id[:8],
                exc)
            job_completed = True

        # When job finishes, update database and cleanup local state:
        del self._jobs[job.id]
        self._rate_limiter.remove_job(job.id)
        if job_completed:
            completed_at = datetime.now(timezone.utc)
            run_state = RunState.COMPLETED
            await self._db.finish_job(job.id, run_state, completed_at)
            await self._db.clear_frontier(job.id)
            self._stats_tracker.set_run_state(job.id, run_state)
            self._stats_tracker.complete_job(job.id, completed_at)
            event = JobStateEvent(job.id, job.schedule_id, run_state,
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
    def __init__(self, name, job_id, schedule_id, policy, frontier, downloader,
            storage, extractor, terminator):
        '''
        Constructor.

        :param str name: The name of this job.
        :param str job_id: ID for this job, or None if its a new job.
        :param schedule_id: (Optional) The ID of the schedule associated with
            this job.
        :type schedule_id: str or None
        :param starbelly.policy.Policy: A crawl policy.
        :param starbelly.frontier.CrawlFrontier frontier: The component that
            manages the crawl priority queue.
        :param starbelly.downloader.Downloader downloader: The component that
            downloads resources.
        :param starbelly.storage.CrawlStorage storage: The component that stores
            crawl results in the database.
        :param starbelly.extractor.CrawlExtractor extractor: The component that
            extracts URLs from downloaded resources and adds them to the crawl
            frontier.
        :param PipelineTerminator terminator: The component that reads data off
            of the end of the crawling pipeline and discards it.
        '''
        self._name = name
        self._job_id = job_id
        self._schedule_id = schedule_id
        self._policy = policy
        self._frontier = frontier
        self._downloader = downloader
        self._storage = storage
        self._extractor = extractor
        self._terminator = terminator

        self._cancel_scope = None
        self._stopped = trio.Event()

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<CrawlJob job_id={} "{}">'.format(self._job_id[:8], self._name)

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
    def name(self):
        return self._name

    @property
    def old_urls(self):
        ''' Returns a set of hashed URLs that the crawl has seen before. '''
        return self._extractor.old_urls

    @property
    def schedule_id(self):
        return self._schedule_id

    async def run(self):
        '''
        Start all of the subcomponents of the job.

        :returns: Runs until this job finishes.
        '''
        def exc_filter(exc):
            ''' Filter out Cancelled exceptions raised by the nursery. '''
            if isinstance(exc, trio.Cancelled):
                return None
            return exc

        with trio.MultiError.catch(exc_filter):
            async with trio.open_nursery() as nursery:
                self._cancel_scope = nursery.cancel_scope
                logger.info('%r Running...', self)
                nursery.start_soon(self._frontier.run)
                nursery.start_soon(self._downloader.run)
                nursery.start_soon(self._extractor.run)
                nursery.start_soon(self._storage.run)
                nursery.start_soon(self._terminator.run)

                # After starting background tasks, this task enforces the
                # maximum crawl duration.
                if self._policy.limits.max_duration:
                    await trio.sleep(self._policy.limits.max_duration)
                    raise CrawlDurationExceeded()
                await trio.sleep_forever()

        self._stopped.set()

    async def stop(self):
        '''
        Stop the crawl job.
        '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception('Cannot cancel job because it has not started')
        await self._stopped.wait()
