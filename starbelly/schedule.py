import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import functools
import heapq
import logging
from uuid import UUID

from rethinkdb import RethinkDB
import trio

from .job import JobStateEvent, RunState
from protobuf import pb_date
from protobuf.shared_pb2 import (
    JobScheduleTiming as PbJobScheduleTiming,
    JobScheduleTimeUnit as PbJobScheduleTimeUnit,
)


logger = logging.getLogger(__name__)
r = RethinkDB()


class ScheduleValidationError(Exception):
    ''' Custom error for job schedule validation. '''


@dataclass
class Schedule:
    ''' A schedule for running a job periodically. '''
    id: str
    name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    time_unit: str
    num_units: int
    timing: str
    job_name: str
    job_count: int
    seeds: list
    tags: list
    policy_id: str

    def __post_init__(self):
        ''' Validate schedule attributes. '''
        if not self.seeds:
            raise ScheduleValidationError(
                'Crawl schedule must have at least one seed URL.')
        if self.num_units <= 0:
            raise ScheduleValidationError('Time units must be positive')
        try:
            self.format_job_name(datetime(1982, 11, 21, 3, 14, 0).timestamp())
        except KeyError:
            raise ScheduleValidationError('Invalid variable in job name:'
                ' COUNT, DATE, & TIME are allowed.')
        except:
            raise ScheduleValidationError('Invalid job name')

    @classmethod
    def from_doc(cls, doc):
        '''
        Create a schedule from a database document.

        :param dict doc:
        '''
        return cls(
            doc['id'],
            doc['schedule_name'],
            doc['enabled'],
            doc['created_at'],
            doc['updated_at'],
            doc['time_unit'],
            doc['num_units'],
            doc['timing'],
            doc['job_name'],
            doc['job_count'],
            doc['seeds'],
            doc['tags'],
            doc['policy_id'],
        )

    @classmethod
    def from_pb(cls, pb):
        '''
        Create a schedule from a protobuf object.

        :param pb:
        '''
        return cls(
            pb.schedule_id,
            pb.schedule_name,
            pb.enabled,
            pb_date(pb, 'created_at'),
            pb_date(pb, 'updated_at'),
            PbJobScheduleTimeUnit.Name(pb.time_unit),
            pb.num_units,
            PbJobScheduleTiming.Name(pb.timing),
            pb.job_name,
            pb.job_count,
            [seed for seed in pb.seeds],
            [tag for tag in pb.tag_list.tags],
            pb.policy_id,
        )

    def to_doc(self):
        '''
        Convert schedule to database document.

        :returns: A database document.
        :rtype: dict
        '''
        return {
            'id': self.id,
            'schedule_name': self.name,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'time_unit': self.time_unit,
            'num_units': self.num_units,
            'timing': self.timing,
            'job_name': self.job_name,
            'job_count': self.job_count,
            'seeds': self.seeds,
            'tags': self.tags,
            'policy_id': self.policy_id,
        }

    def to_pb(self, pb):
        '''
        Convert schedule to a protobuf object.

        :param pb: A schedule protobuf.
        '''
        pb.schedule_id = UUID(self.id).bytes
        pb.schedule_name = self.name
        pb.enabled = self.enabled
        pb.created_at = self.created_at.isoformat()
        pb.updated_at = self.updated_at.isoformat()
        pb.time_unit = PbJobScheduleTimeUnit.Value(self.time_unit)
        pb.num_units = self.num_units
        pb.timing = PbJobScheduleTiming.Value(self.timing)
        pb.job_name = self.job_name
        pb.job_count = self.job_count
        for seed in self.seeds:
            pb.seeds.append(seed)
        for tag in self.tags:
            pb.tag_list.tags.append(tag)
        pb.policy_id = UUID(self.policy_id).bytes

    def format_job_name(self, when):
        '''
        Format a name for a new job.

        :param float when: The timestamp when the job is starting.
        :returns: A formatted job name.
        :rtype: str
        '''
        return self.job_name.format(
            COUNT=self.job_count,
            TIME=int(when),
            DATE=datetime.fromtimestamp(when, timezone.utc)
                         .strftime('%Y-%m-%dT%H:%M:%S')
        )


@functools.total_ordering
class ScheduleEvent:
    '''
    An instance of one event in a schedule.

    The scheduler will instantiate one event for each schedule. That event
    corresponds to the next time that scheduled job needs to run. When a job
    starts and finishes, the scheduler will check if it needs to instantiate a
    new event and add it to the schedule.

    This class implements comparison operators to make it easy to sort events
    into chronological order.
    '''
    def __init__(self, schedule, due):
        '''
        Construct a schedule event from a database document..

        :param dict schedule: A database document.
        :param float due: The timestamp when this event is due.
        '''
        self._schedule = schedule
        self._due = due

    def __eq__(self, other):
        ''' Implement == '''
        return self._due == other._due

    def __gt__(self, other):
        ''' Implement > '''
        return self._due > other._due

    def __repr__(self):
        ''' Make string representation. '''
        return 'ScheduleEvent<id={} name={} due={}>'.format(
            self._schedule.id[:8], self._schedule.name, self._due)

    @property
    def due(self):
        '''
        :returns: The timestamp when this event is due.
        :rtype float:
        '''
        return self._due

    @property
    def is_due(self):
        '''
        :returns: Indicates if this event is due.
        :rtype: bool
        '''
        return self.seconds_until_due <= 0

    @property
    def schedule(self):
        '''
        :returns: The schedule object.
        :rtype: Schedule
        '''
        return self._schedule

    @property
    def seconds_until_due(self):
        '''
        :returns: The number of seconds until this event is due.
        :rtype: float
        '''
        return self._due - trio.current_time()


class Scheduler:
    ''' Starts jobs according to a schedule. '''
    def __init__(self, db, crawl_manager):
        '''
        Constructor.

        :param starbelly.db.ScheduleDB db:
        :param starbelly.job.CrawlManager crawl_manager: A crawl manager, used
            for starting jobs when they are scheduled to begin.
        '''
        self._db = db
        self._crawl_manager = crawl_manager

        self._events = list()
        self._schedules = dict()
        self._recv_channel = crawl_manager.get_job_state_channel()
        self._event_added = trio.Event()
        self._nursery = None
        self._running_jobs = dict()

    def add_schedule(self, schedule, latest_job):
        '''
        Add a new schedule.

        :param Schedule schedule:
        :param latest_job: (Optional) The most recent job for this schedule, or
            None if this schedule has never run.
        :type latest_job: dict or None
        '''
        if schedule.id in self._schedules:
            raise Exception('Schedule ID {} has already been added.'.format(
                schedule.id))
        self._schedules[schedule.id] = schedule

        # Schedule the next job for this schedule.
        due = None
        if latest_job:
            timing_regular = schedule.timing == 'REGULAR_INTERVAL'
            finished = latest_job['run_state'] in (RunState.CANCELLED,
                RunState.COMPLETED)
            running = not finished
            timing_after = schedule.timing == 'AFTER_PREVIOUS_JOB_FINISHED'
            if running and timing_regular:
                due = self._compute_next_event(
                    latest_job['started_at'],
                    schedule.num_units,
                    schedule.time_unit
                )
            elif finished and timing_after:
                due = self._compute_next_event(
                    latest_job['completed_at'],
                    schedule.num_units,
                    schedule.time_unit
                )
        else:
            # When a schedule is first created, it runs 15 seconds later.
            due = datetime.fromtimestamp(trio.current_time() + 15, timezone.utc)

        if due:
            logger.info('Scheduling "{}" at {}'.format(schedule.name, due))
            self._add_event(ScheduleEvent(schedule, due.timestamp()))

    def remove_schedule(self, schedule_id):
        '''
        Remove pending events for the specified schedule and do not schedule
        additional events.

        It is easier to copy all non-cancelled events into a new list than to
        remove an element from the middle of the list.

        :param bytes schedule_id: The ID of the schedule to disable.
        '''
        self._events = [e for e in self._events if e.schedule.id !=
            schedule_id]
        self._schedules.pop(schedule_id)

    async def run(self):
        '''
        Listen for changes in job status and check if a job needs to be
        rescheduled.

        :returns: This method runs until cancelled.
        '''
        async for schedule_doc in self._db.get_schedule_docs():
            schedule = Schedule.from_doc(schedule_doc)
            latest_job = schedule_doc['latest_job']
            self.add_schedule(schedule, latest_job)

        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._listen_task, name='Schedule Job Listener')
            nursery.start_soon(self._schedule_task, name='Schedule Main')

    def _add_event(self, event):
        '''
        Add an event to the internal queue.

        :param ScheduleEvent event:
        '''
        heapq.heappush(self._events, event)
        self._event_added.set()
        self._event_added = trio.Event()

    def _compute_next_event(self, base, num_units, time_unit):
        '''
        Add an offset to a base time.

        :param datetime base: The base timestamp.
        :param int num_units: The number of units to add to the base timestamp.
        :param str time_unit: The type of units to add to the base timestamp.
        :returns: The future timestamp.
        :rtype: float
        '''
        if time_unit == 'MINUTES':
            next_ = base + timedelta(minutes=num_units)
        elif time_unit == 'HOURS':
            next_ = base + timedelta(hours=num_units)
        elif time_unit == 'DAYS':
            next_ = base + timedelta(days=num_units)
        elif time_unit == 'WEEKS':
            next_ = base + timedelta(weeks=num_units)
        elif time_unit == 'MONTHS':
            month = base.month + num_units - 1
            year = int(base.year + month / 12 )
            month = month % 12 + 1
            day = min(base.day, calendar.monthrange(year,month)[1])
            next_ = base.replace(year=year, month=month, day=day)
        elif time_unit == 'YEARS':
            next_ = base.replace(base.year + num_units)
        return next_

    async def _listen_task(self):
        '''
        Listen for ``JobStateEvent`` and check if a job needs to be
        rescheduled.

        :returns: This method runs until cancelled.
        '''
        async with self._recv_channel:
            async for job_state in self._recv_channel:
                try:
                    schedule = self._schedules[job_state.schedule_id]
                except KeyError:
                    # This job is not associated with a schedule.
                    continue

                # Compute the due date for the next event.
                timing_regular = schedule.timing == 'REGULAR_INTERVAL'
                finished = job_state.run_state in (RunState.CANCELLED,
                    RunState.COMPLETED)
                running = not finished
                timing_after = schedule.timing == 'AFTER_PREVIOUS_JOB_FINISHED'
                if (running and timing_regular) or (finished and timing_after):
                    due = self._compute_next_event(
                        job_state.event_time,
                        schedule.num_units,
                        schedule.time_unit
                    )
                    logger.info('Rescheduling "{}" at {}'.format(
                        schedule.name, due.isoformat()
                    ))
                    self._add_event(ScheduleEvent(schedule, due.timestamp()))

                if running:
                    self._running_jobs[job_state.schedule_id] = job_state.job_id
                else:
                    self._running_jobs.pop(job_state.schedule_id, None)

    async def _schedule_task(self):
        '''
        Wait until a scheduled event is due, then start a new crawl job.

        :returns: This method runs until cancelled.
        '''
        while True:
            if len(self._events) == 0:
                await self._event_added.wait()
                continue

            next_event = self._events[0]

            if not next_event.is_due:
                with trio.move_on_after(next_event.seconds_until_due):
                    await self._event_added.wait()
                continue

            self._events.pop(0)
            logger.info('Scheduled job "%s" is ready to start.',
                next_event.schedule.name)
            await self._start_scheduled_job(next_event)

    async def _start_scheduled_job(self, event):
        '''
        Start a scheduled job that is ready to run. If an instance of this
        scheduled job is already running, cancel it first.

        :param ScheduleEvent event: The event that triggered this new job.
        '''
        schedule = event.schedule
        try:
            # If this schedule already has a job running, then cancel it.
            old_job_id = self._running_jobs[schedule.id]
            await self._crawl_manager.cancel_job(old_job_id)
        except KeyError:
            # This schedule does not have a job running.
            pass

        # Start the new job:
        schedule.job_count += 1
        job_name = schedule.format_job_name(event.due)
        job_id = await self._crawl_manager.start_job(job_name, schedule.seeds,
            schedule.tags, schedule.policy_id, schedule.id)

        # Update schedule metadata
        await self._db.update_job_count(schedule.id, schedule.job_count)
