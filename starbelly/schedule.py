import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import functools
import heapq
import logging
from uuid import UUID

from protobuf import pb_date
from protobuf.shared_pb2 import (
    JobScheduleTiming as PbJobScheduleTiming,
    JobScheduleTimeUnit as PbJobScheduleTimeUnit,
)
import trio

from .job import JobStatusNotification


logger = logging.getLogger(__name__)


class ScheduleValidationError(Exception):
    ''' Custom error for job schedule validation. '''


@dataclass
class ScheduleNotification:
    ''' Indicates that a scheduled job is ready start. '''
    schedule_id: bytes
    job_name: str
    seeds: list
    tags: list


@dataclass
class Schedule:
    ''' A schedule for running a job periodically. '''
    id_: bytes
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
    policy_id: bytes
    latest_job_id: bytes

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
            doc['latest_job_id']
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
            pb.latest_job_id
        )

    def to_doc(self):
        '''
        Convert schedule to database document.

        :returns: A database document.
        :rtype: dict
        '''
        return {
            'id': self.id_,
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
            'latest_job_id': self.latest_job_id,
        }

    def to_pb(self, pb):
        '''
        Convert schedule to a protobuf object.

        :param pb: A schedule protobuf.
        '''
        pb.schedule_id = UUID(self.id_).bytes
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
        pb.latest_job_id = UUID(self.latest_job_id).bytes

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
            self._schedule.id_[:8], self._schedule.name, self._due)

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
    '''
    Starts jobs according to a schedule.


    '''
    def __init__(self, recv_channel, send_channel):
        '''
        Constructor.

        :param trio.abc.ReceiveChannel recv_channel: A channel for receiving
            updates on job status, i.e. when jobs start and complete.
        :parm trio.abc.SendChannel send_channel: A channel for sending schedule
            status, i.e. when a job needs to start.
        '''
        self._events = list()
        self._schedules = dict()
        self._recv_channel = recv_channel
        self._send_channel = send_channel
        self._event_added = trio.Event()

    async def run(self):
        '''
        Listen for changes in job status and check if a job needs to be
        rescheduled.

        :returns: This method runs until cancelled.
        '''
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._listen_task,
                name='Scheduler Listen Task')
            nursery.start_soon(self._schedule_task,
                name='Scheduler Task')

    def add_schedule(self, schedule):
        '''
        Add a schedule.

        :param Schedule schedule:
        '''
        if schedule.id_ in self._schedules:
            raise Exception('Schedule ID {:x} has already been added.'.format(
                schedule.id_))
        self._schedules[schedule.id_] = schedule

    def remove_schedule(self, schedule_id):
        '''
        Remove pending events for the specified schedule and do not schedule
        additional events.

        It is easier to copy all non-cancelled events into a new list than to
        remove an element from the middle of the list.

        :param bytes schedule_id: The ID of the schedule to disable.
        '''
        self._events = [e for e in self._events if e.schedule.id_ !=
            schedule_id]
        self._schedules.pop(schedule_id)

    def _compute_next_event(self, base, num_units, time_unit):
        '''
        Add an offset to a base time.

        :param float base: The base timestamp.
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
        Listen for JobStatusNotification and check if a job needs to be
        rescheduled.

        :returns: This method runs until cancelled.
        '''
        async for job_notification in self._recv_channel:
            try:
                schedule = self._schedules[job_notification.schedule_id]
            except KeyError:
                # This job is not associated with a schedule.
                continue

            # Keep track of job counts.
            if job_notification.status == 'STARTED':
                schedule.job_count += 1

            # Compute the due date for the next event.
            due = None
            if job_notification.status is None:
                # This schedule has not run before, so it should start soon.
                due = datetime.fromtimestamp(trio.current_time()) \
                    + timedelta(minutes=1)
            elif ((job_notification.status == 'STARTED' and
                      schedule.timing == 'REGULAR_INTERVAL') or
                  (job_notification.status == 'COMPLETED' and
                      schedule.timing == 'AFTER_PREVIOUS_JOB_FINISHED')):
                due = self._compute_next_event(
                    job_notification.datetime,
                    schedule.num_units,
                    schedule.time_unit
                )

            if due:
                # Add job to schedule.
                logger.info('Scheduling crawl for "{}" at {}'.format(
                    schedule.name, due.isoformat()
                ))
                event = ScheduleEvent(schedule, due.timestamp())
                heapq.heappush(self._events, event)
                self._event_added.set()
                self._event_added = trio.Event()

    async def _schedule_task(self):
        '''
        Send notifications when scheduled events are ready to run.

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
            schedule = next_event.schedule
            job_count = schedule.job_count + 1
            job_name = schedule.format_job_name(next_event.due)
            notification = ScheduleNotification(schedule.id_, job_name,
                list(schedule.seeds), list(schedule.tags))
            logger.info('Scheduled job "%s" is ready to start.', job_name)
            await self._send_channel.send(notification)
