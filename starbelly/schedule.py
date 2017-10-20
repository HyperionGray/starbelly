import asyncio
import calendar
from datetime import datetime, timedelta
import functools
import heapq
import logging
from uuid import UUID

from dateutil.tz import tzlocal
import protobuf.shared_pb2
import rethinkdb as r

from . import cancel_futures, daemon_task, wait_first


logger = logging.getLogger(__name__)


class ScheduleValidationError(Exception):
    ''' Custom error for job schedule validation. '''


@functools.total_ordering
class ScheduleEvent:
    '''
    An instance of one event in a schedule.

    This class implements rich comparison based on when the event is due.
    '''

    def __init__(self, schedule, due):
        ''' Constructor. '''
        self.schedule_id = schedule['id']
        self.schedule_name = schedule['schedule_name']
        self._due = due
        self._enabled = True

    def __eq__(self, other):
        ''' Implement == '''
        return self._due == other._due

    def __gt__(self, other):
        ''' Implement > '''
        return self._due > other._due

    def __repr__(self):
        ''' Make string representation. '''
        return 'ScheduleEvent<id={} name={} due={} enabled={}>'.format(
            self.schedule_id[:8], self.schedule_name, self._due.isoformat(),
            self._enabled
        )

    def disable(self):
        '''
        Disable this event.

        This means that the event will be ignored when it becomes due, which is
        easier than trying to remove an arbitrary event from the heap.
        '''
        self._enabled = False

    def is_enabled(self):
        ''' Return true if this event is enabled. '''
        return self._enabled

    def seconds_due(self):
        ''' Return the number of seconds until this event is due. '''
        return (self._due - datetime.now(tzlocal())).total_seconds()


class Scheduler:
    ''' Implements job scheduling. '''
    def __init__(self, crawl_manager, db_pool):
        ''' Constructor. '''
        self._crawl_manager = crawl_manager
        self._db_pool = db_pool
        self._events = list()
        self._schedule_changed = asyncio.Event()

    async def delete_job_schedule(self, schedule_id):
        ''' Delete a job schedule from the database. '''
        async with self._db_pool.connection() as conn:
            await r.table('job_schedule').get(schedule_id).delete().run(conn)
        self._disable_schedule(schedule_id)

    @staticmethod
    def doc_to_pb(doc, pb):
        ''' Convert database document schedule to protobuf. '''
        pb.schedule_id = UUID(doc['id']).bytes
        pb.created_at = doc['created_at'].isoformat()
        pb.updated_at = doc['updated_at'].isoformat()
        pb.enabled = doc['enabled']
        pb.time_unit = protobuf.shared_pb2.JobScheduleTimeUnit.Value(
            doc['time_unit'])
        pb.num_units = doc['num_units']
        pb.timing = protobuf.shared_pb2.JobScheduleTiming.Value(
            doc['timing'])
        pb.schedule_name = doc['schedule_name']
        pb.job_name = doc['job_name']
        pb.job_count = doc['job_count']
        for seed in doc['seeds']:
            pb.seeds.append(seed)
        pb.policy_id = UUID(doc['policy_id']).bytes
        for tag in doc['tags']:
            pb.tag_list.tags.append(tag)
        if 'latest_job_id' in doc:
            pb.latest_job_id = UUID(doc['latest_job_id']).bytes

    @staticmethod
    def format_job_name(name, now, job_count):
        ''' Format a name for a new job. '''
        return name.format(
            COUNT=job_count,
            TIME=int(now.timestamp()),
            DATE=now.strftime('%Y-%m-%d %H:%M:%S')
        )

    async def get_job_schedule(self, schedule_id):
        ''' Get a job schedule from the database. '''
        async with self._db_pool.connection() as conn:
            return await r.table('job_schedule').get(schedule_id).run(conn)

    async def list_job_schedules(self, limit, offset):
        ''' List job schedules in the database. '''
        schedules = list()
        query = (
            r.table('job_schedule')
             .order_by(index='schedule_name')
             .skip(offset)
             .limit(limit)
        )
        async with self._db_pool.connection() as conn:
            count = await r.table('job_schedule').count().run(conn)
            cursor = await query.run(conn)
            async for schedule in cursor:
                schedules.append(schedule)
            await cursor.close()
        return count, schedules

    @staticmethod
    def pb_to_doc(pb):
        ''' Convert a protobuf schedule to a database document. '''
        if pb.num_units <= 0:
            raise ScheduleValidationError('Time units must be positive')

        try:
            Scheduler.format_job_name(pb.job_name, datetime.now(tzlocal()),
                job_count=0)
        except KeyError:
            raise ScheduleValidationError('Invalid variable in job name:'
                ' COUNT, DATE, & TIME are allowed.')
        except:
            raise ScheduleValidationError('Invalid job name')

        if len(pb.seeds) == 0:
            raise Exception('Crawl schedule must have at least one seed URL.')

        doc = {
            'enabled': pb.enabled,
            'time_unit': protobuf.shared_pb2.JobScheduleTimeUnit.Name(
                pb.time_unit),
            'num_units': pb.num_units,
            'timing': protobuf.shared_pb2.JobScheduleTiming.Name(pb.timing),
            'schedule_name': pb.schedule_name,
            'job_name': pb.job_name,
            'seeds': [seed for seed in pb.seeds],
            'policy_id': str(UUID(bytes=pb.policy_id)),
            'tags': [tag for tag in pb.tag_list.tags],
        }

        if pb.HasField('schedule_id'):
            doc['id'] = str(UUID(bytes=pb.schedule_id))
        if pb.HasField('latest_job_id'):
            doc['latest_job_id'] = str(UUID(bytes=pb.latest_job_id))

        return doc

    async def run(self):
        ''' Run the schedule. '''
        # Determine when the next job should start for each schedule.
        schedule_query = self._get_schedule_query()
        async with self._db_pool.connection() as conn:
            cursor = await schedule_query.run(conn)
            async for schedule in cursor:
                self._add_next_event(schedule)

        # Dispatch schedule events.
        job_complete_task = daemon_task(self._job_complete_task())
        while True:
            try:
                if len(self._events) == 0:
                    await self._schedule_changed.wait()
                    self._schedule_changed.clear()
                else:
                    next_event = self._get_next_event()
                    if next_event is None:
                        if len(self._events) == 0:
                            continue
                        next_due = self._events[0].seconds_due()
                        sleeper = asyncio.sleep(next_due)
                        waiter = self._schedule_changed.wait()
                        await wait_first(sleeper, waiter)
                        self._schedule_changed.clear()
                    else:
                        logger.info('Start scheduled job: name=%r id=%r',
                            next_event.schedule_name, next_event.schedule_id)
                        await self._start_scheduled_job(next_event.schedule_id)
            except asyncio.CancelledError:
                await cancel_futures(job_complete_task)
                break

    async def set_job_schedule(self, doc):
        ''' Create or update a job schedule from a database document. '''
        # Update database.
        async with self._db_pool.connection() as conn:
            if 'id' not in doc:
                # Create policy
                doc['created_at'] = r.now()
                doc['updated_at'] = r.now()
                doc['job_count'] = 0
                result = await r.table('job_schedule').insert(doc).run(conn)
                schedule_id = result['generated_keys'][0]
            else:
                doc['updated_at'] = r.now()
                await (
                    r.table('job_schedule')
                     .get(doc['id'])
                     .update(doc)
                     .run(conn)
                )
                schedule_id = None

        # Reschedule.
        async with self._db_pool.connection() as conn:
            query = self._get_schedule_query(schedule_id or doc['id'])
            schedule = await query.run(conn)
            self._disable_schedule(schedule['id'])
            self._add_next_event(schedule)
            self._schedule_changed.set()

        return schedule_id

    def _add_next_event(self, schedule):
        ''' Add the next event for the given schedule. '''
        if not schedule['enabled']:
            return

        latest_job = schedule['latest_job']
        num_units = schedule['num_units']
        time_unit = schedule['time_unit']

        if latest_job is None:
            # The first job should start 1 minute after the schedule is saved.
            due = datetime.now(tzlocal()) + timedelta(minutes=1)
        elif schedule['timing'] == 'REGULAR_INTERVAL':
            # The next job should be scheduled relative to the start time of
            # the latest job.
            due = self._compute_next_event(
                latest_job['started_at'],
                num_units,
                time_unit
            )
        else:
            # The next job should be scheduled relative to the completion time
            # of the latest job.
            if schedule['latest_job']['completed_at'] is None:
                # Cannot schedule until the latest job is complete.
                return
            else:
                due = self._compute_next_event(
                    latest_job['completed_at'],
                    num_units,
                    time_unit
                )

        logger.info('Scheduling crawl for "{}" at {}'.format(
            schedule['schedule_name'], due.isoformat()
        ))
        event = ScheduleEvent(schedule, due)
        heapq.heappush(self._events, event)

    def _compute_next_event(self, base, num_units, time_unit):
        ''' Add an offset to a base time. '''
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
        else:
            raise Exception('Invalid time unit: {}'.format(time_unit))
        return next_

    def _disable_schedule(self, schedule_id):
        ''' Disable events for a schedule. '''
        for event in self._events:
            if event.schedule_id == schedule_id:
                event.disable()

    def _get_next_event(self):
        '''
        Get the next event that is due.

        Returns None if nothing is due.
        '''
        # Pop off any disabled events.
        while len(self._events) > 0 and not self._events[0].is_enabled():
            heapq.heappop(self._events)

        # Return next event, if there is one.
        if len(self._events) > 0 and self._events[0].seconds_due() <= 0:
            return heapq.heappop(self._events)
        else:
            return None

    def _get_schedule_query(self, schedule_id=None):
        '''
        Construct a query for getting active schedules.

        If schedule_id is provided, then the query returns a single schedule.
        Otherwise, running this query returns a cursor.
        '''
        def get_job(schedule):
            return {
                'latest_job': r.branch(
                    schedule.has_fields('latest_job_id'),
                    r.table('job')
                     .get(schedule['latest_job_id'])
                     .pluck('run_state', 'started_at', 'completed_at'),
                    None
                ),
            }

        query = r.table('job_schedule')

        if schedule_id is None:
            query = query.filter({'enabled': True})
        else:
            query = query.get(schedule_id)

        return query.merge(get_job)

    async def _job_complete_task(self):
        '''
        Listen for jobs that finish, and then check if they should be
        re-scheduled.
        '''
        job_query = (
            r.table('job')
             .pluck('run_state', 'schedule_id')
             .changes()
             .pluck('new_val')
        )
        async with self._db_pool.connection() as conn:
            feed = await job_query.run(conn)
            async for change in feed:
                job = change['new_val']
                if job is None:
                    continue
                if job['run_state'] in ('cancelled', 'completed') and \
                    'schedule_id' in job:
                    schedule_query = self._get_schedule_query(
                        job['schedule_id'])
                    schedule = await schedule_query.run(conn)
                    if schedule['timing'] == 'AFTER_PREVIOUS_JOB_FINISHED':
                        self._add_next_event(schedule)
                        self._schedule_changed.set()

    async def _start_scheduled_job(self, schedule_id):
        ''' Start a job that is ready to run. '''
        async with self._db_pool.connection() as conn:
            query = self._get_schedule_query(schedule_id)
            schedule = await query.run(conn)

        # If a job is already running, cancel it.
        latest_job = schedule['latest_job']
        if latest_job is not None and \
            latest_job['run_state'] not in ('cancelled', 'completed'):
            await self._crawl_manager.cancel_job(schedule['latest_job_id'])

        # Start a new job for this schedule.
        name = Scheduler.format_job_name(schedule['job_name'],
            datetime.now(tzlocal()), schedule['job_count'])

        job_id = await self._crawl_manager.start_job(
            schedule['seeds'],
            schedule['policy_id'],
            name,
            schedule['tags'],
            schedule['id']
        )

        async with self._db_pool.connection() as conn:
            await r.table('job_schedule').get(schedule_id).update({
                'latest_job_id': job_id,
                'job_count': schedule['job_count'] + 1,
            }).run(conn)

        # If the schedule runs at regular intervals, then reschedule it now.
        if schedule['timing'] == 'REGULAR_INTERVAL':
            async with self._db_pool.connection() as conn:
                query = self._get_schedule_query(schedule_id)
                schedule = await query.run(conn)
                self._add_next_event(schedule)
