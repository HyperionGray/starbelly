from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock
from uuid import UUID

import pytest
import trio

from . import AsyncMock, async_iter, fail_after
from starbelly.job import JobStateEvent, RunState
from starbelly.schedule import (
    Schedule,
    Scheduler,
    ScheduleEvent,
    ScheduleValidationError
)
from starbelly.starbelly_pb2 import (
    JobSchedule as PbJobSchedule,
    JobScheduleTiming as PbJobScheduleTiming,
    JobScheduleTimeUnit as PbJobScheduleTimeUnit,
)


@contextmanager
def assert_elapsed(min_=None, max_=None):
    ''' A context manager which asserts that its block runs within some bounded
    time. '''
    start = trio.current_time()
    yield
    elapsed = trio.current_time() - start
    if min_ is not None:
        assert elapsed >= min_
    if max_ is not None:
        assert elapsed <= max_


def make_schedule(num, timing='REGULAR_INTERVAL', num_units=3,
    time_unit='HOURS', enabled=True, seeds=None, tags=None):
    ''' Return a new schedule database document. '''
    return Schedule(
        '123e4567-e89b-12d3-a456-42665544000{}'.format(num),
        'My Schedule {}'.format(num),
        enabled,
        datetime(2017, 11, 29, 15, 19, 50, tzinfo=timezone.utc),
        datetime(2018, 11, 29, 15, 19, 50, tzinfo=timezone.utc),
        time_unit,
        num_units,
        timing,
        'Test Job @ {TIME}',
        0,
        seeds or ['http://one.example'],
        tags or ['tag1', 'tag2'],
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    )


async def test_event_due():
    # This test is async because it relies on the Trio clock.
    event1 = ScheduleEvent(make_schedule(1), trio.current_time() - 60)
    assert event1.seconds_until_due < 0
    assert event1.is_due
    event2 = ScheduleEvent(make_schedule(2), trio.current_time() + 60)
    assert event2.seconds_until_due > 0
    assert not event2.is_due


def test_event_repr():
    r = repr(ScheduleEvent(make_schedule(1), 0))
    assert r == 'ScheduleEvent<id=123e4567 name=My Schedule 1 due=0>'


async def test_event_order():
    # This test is async because it relies on the Trio clock.
    schedule = make_schedule(1)
    due_future = trio.current_time() + 60
    due_past = trio.current_time() - 60
    due_now = trio.current_time()
    dues = [due_future, due_past, due_now]
    dues.sort()
    assert dues[0] == due_past
    assert dues[1] == due_now
    assert dues[2] == due_future


def test_format_job_name():
    args = [
        '123e4567-e89b-12d3-a456-426655440001',
        'Test Schedule',
        True,
        datetime(2018, 11, 29, 15, 19, 50),
        datetime(2018, 11, 30, 15, 19, 50),
        'HOURS',
        3,
        'REGULAR_INTERVAL',
        'Test Job #{COUNT} @ {TIME}',
        1,
        ['http://one.example'],
        ['tag1', 'tag2'],
        '123e4567-e89b-12d3-a456-426655440002'
    ]
    time = 1541175331
    schedule = Schedule(*args)
    format_name = schedule.format_job_name(when=time)
    assert format_name == 'Test Job #1 @ 1541175331'

    args[8] = 'Another Job on {DATE}'
    schedule = Schedule(*args)
    format_name = schedule.format_job_name(when=time)
    assert format_name == 'Another Job on 2018-11-02T16:15:31'


async def test_schedule_doc_to_pb():
    schedule_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    policy_id = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
    job_id = UUID('cccccccc-cccc-cccc-cccc-cccccccccccc')
    doc = {
        'id': str(schedule_id),
        'schedule_name': 'Test Schedule',
        'enabled': True,
        'created_at': datetime(2017, 11, 29, 15, 19, 50),
        'updated_at': datetime(2018, 11, 29, 15, 19, 50),
        'time_unit': 'HOURS',
        'num_units': 3,
        'timing': 'REGULAR_INTERVAL',
        'job_name': 'Test Job #{COUNT}',
        'job_count': 1,
        'seeds': ['http://one.example'],
        'tags': ['tag1', 'tag2'],
        'policy_id': str(policy_id)
    }
    pb = PbJobSchedule()
    schedule = Schedule.from_doc(doc)
    schedule.to_pb(pb)
    assert pb.schedule_id == schedule_id.bytes
    assert pb.schedule_name == 'Test Schedule'
    assert pb.enabled
    assert pb.created_at == '2017-11-29T15:19:50'
    assert pb.updated_at == '2018-11-29T15:19:50'
    assert pb.time_unit == PbJobScheduleTimeUnit.Value('HOURS')
    assert pb.num_units == 3
    assert pb.timing == PbJobScheduleTiming.Value('REGULAR_INTERVAL')
    assert pb.job_name == 'Test Job #{COUNT}'
    assert pb.job_count == 1
    assert pb.seeds[0] == 'http://one.example'
    assert pb.tag_list.tags[0] == 'tag1'
    assert pb.tag_list.tags[1] == 'tag2'
    assert pb.policy_id == policy_id.bytes


async def test_schedule_pb_to_doc():
    pb = PbJobSchedule()
    pb.schedule_id = b'\x12>Eg\xe8\x9b\x12\xd3\xa4VBfUD\x00\x01'
    pb.schedule_name = 'Test Schedule'
    pb.enabled = True
    pb.created_at = '2017-11-29T15:19:50'
    pb.updated_at = '2018-11-29T15:19:50'
    pb.time_unit = PbJobScheduleTimeUnit.Value('HOURS')
    pb.num_units = 3
    pb.timing = PbJobScheduleTiming.Value('REGULAR_INTERVAL')
    pb.job_name = 'Test Job #{COUNT}'
    pb.job_count = 1
    pb.seeds.append('http://one.example')
    pb.tag_list.tags.append('tag1')
    pb.tag_list.tags.append('tag2')
    pb.policy_id = b'\x12>Eg\xe8\x9b\x12\xd3\xa4VBfUD\x00\x02'
    schedule = Schedule.from_pb(pb)
    doc = schedule.to_doc()
    assert doc['id'] == b'\x12>Eg\xe8\x9b\x12\xd3\xa4VBfUD\x00\x01'
    assert doc['schedule_name'] == 'Test Schedule'
    assert doc['enabled']
    assert doc['created_at'] == datetime(2017, 11, 29, 15, 19, 50) \
        .replace(tzinfo=timezone.utc)
    assert doc['updated_at'] == datetime(2018, 11, 29, 15, 19, 50) \
        .replace(tzinfo=timezone.utc)
    assert doc['time_unit'] == 'HOURS'
    assert doc['num_units'] == 3
    assert doc['timing'] == 'REGULAR_INTERVAL'
    assert doc['job_name'] == 'Test Job #{COUNT}'
    assert doc['job_count'] == 1
    assert doc['seeds'][0] == 'http://one.example'
    assert doc['tags'][0] == 'tag1'
    assert doc['tags'][1] == 'tag2'
    assert doc['policy_id'] == b'\x12>Eg\xe8\x9b\x12\xd3\xa4VBfUD\x00\x02'


def test_invalid_schedule():
    with pytest.raises(ScheduleValidationError):
        Schedule(
            '123e4567-e89b-12d3-a456-426655440001',
            'My Schedule',
            True,
            datetime(2017, 11, 29, 15, 19, 50),
            datetime(2018, 11, 29, 15, 19, 50),
            'HOURS',
            3,
            'AFTER_PREVIOUS_JOB_FINISHED',
            'Test Job @ {TIME}',
            0,
            [], # Must contain one seed
            ['tag1', 'tag2'],
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )

    with pytest.raises(ScheduleValidationError):
        Schedule(
            '123e4567-e89b-12d3-a456-426655440001',
            'My Schedule',
            True,
            datetime(2017, 11, 29, 15, 19, 50),
            datetime(2018, 11, 29, 15, 19, 50),
            'HOURS',
            -3, # Num units must be positive
            'AFTER_PREVIOUS_JOB_FINISHED',
            'Test Job @ {TIME}',
            0,
            ['http://seed.example'],
            ['tag1', 'tag2'],
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )

    with pytest.raises(ScheduleValidationError):
        Schedule(
            '123e4567-e89b-12d3-a456-426655440001',
            'My Schedule',
            True,
            datetime(2017, 11, 29, 15, 19, 50),
            datetime(2018, 11, 29, 15, 19, 50),
            'HOURS',
            3,
            'AFTER_PREVIOUS_JOB_FINISHED',
            'Test Job @ {BOGUS}', # Invalid job name key
            0,
            ['http://seed.example'],
            ['tag1', 'tag2'],
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )

    with pytest.raises(ScheduleValidationError):
        Schedule(
            '123e4567-e89b-12d3-a456-426655440001',
            'My Schedule',
            True,
            datetime(2017, 11, 29, 15, 19, 50),
            datetime(2018, 11, 29, 15, 19, 50),
            'HOURS',
            3,
            'AFTER_PREVIOUS_JOB_FINISHED',
            'Test Job @ {', # Invalid job name format
            0,
            ['http://seed.example'],
            ['tag1', 'tag2'],
            'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )


# This test is async because it depends on trio.current_time()
async def test_add_schedule_twice():
    schedule = make_schedule(1)
    db_pool = Mock()
    crawl_manager = Mock()
    scheduler = Scheduler(db_pool, crawl_manager)
    scheduler.add_schedule(schedule, latest_job=None)
    with pytest.raises(Exception):
        scheduler.add_schedule(schedule, latest_job=None)


def test_schedule_time_units(autojump_clock):
    ''' It is less tedious to test this private method directly than to set up
    schedules for each possible time unit. '''
    db_pool = Mock()
    crawl_manager = Mock()
    scheduler = Scheduler(db_pool, crawl_manager)
    base = datetime(1982, 11, 21, 3, 14, 0)

    due1 = scheduler._compute_next_event(base, 2, 'MINUTES')
    assert due1 == datetime(1982, 11, 21, 3, 16, 0)

    due2 = scheduler._compute_next_event(base, 2, 'HOURS')
    assert due2 == datetime(1982, 11, 21, 5, 14, 0)

    due3 = scheduler._compute_next_event(base, 2, 'DAYS')
    assert due3 == datetime(1982, 11, 23, 3, 14, 0)

    due4 = scheduler._compute_next_event(base, 2, 'WEEKS')
    assert due4 == datetime(1982, 12, 5, 3, 14, 0)

    due5 = scheduler._compute_next_event(base, 2, 'MONTHS')
    assert due5 == datetime(1983, 1, 21, 3, 14, 0)

    due6 = scheduler._compute_next_event(base, 2, 'YEARS')
    assert due6 == datetime(1984, 11, 21, 3, 14, 0)


@fail_after(4 * 60 * 60)
async def test_schedule_one_event_run_twice(autojump_clock, mocker, nursery):
    ''' Create one schedule and let it run twice. '''
    sched_id = '123e4567-e89b-12d3-a456-426655440001'
    sched_job1_id = '123e4567-e89b-12d3-a456-426655440002'
    sched_job2_id = '123e4567-e89b-12d3-a456-426655440003'

    # This schedule runs 3 hours after the last job finishes, and it has
    # never run before.
    sched = make_schedule(1, num_units=3, timing='AFTER_PREVIOUS_JOB_FINISHED',
        seeds=['http://schedule.example'], tags=['schedule'])
    sched_doc = sched.to_doc()
    sched_doc['latest_job'] = None
    assert sched.job_count == 0

    start_job_count = 0
    start_job_args = None
    async def start_job(*args):
        nonlocal start_job_count
        nonlocal start_job_args
        start_job_count += 1
        start_job_args = args

    # Set up scheduler
    job_send, job_recv = trio.open_memory_channel(0)
    db = Mock()
    db.get_schedule_docs.return_value = async_iter([sched_doc])
    db.update_job_count.side_effect = AsyncMock()
    crawl_manager = Mock()
    crawl_manager.get_job_state_channel.return_value = job_recv
    crawl_manager.start_job.side_effect = start_job
    scheduler = Scheduler(db, crawl_manager)
    nursery.start_soon(scheduler.run)
    assert crawl_manager.start_job.call_count == 0

    # If we send job status for a job that isn't part of a schedule, it
    # should be ignored.
    await job_send.send(JobStateEvent(
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', None, RunState.RUNNING,
        datetime.fromtimestamp(trio.current_time())))

    # The job should run after 15 seconds.
    await trio.sleep(15.5)
    assert start_job_count == 1
    assert start_job_args[0].startswith('Test Job @')
    assert start_job_args[1] == ['http://schedule.example']
    assert start_job_args[2] == ['schedule']
    assert start_job_args[4] == '123e4567-e89b-12d3-a456-426655440001'

    # If we send completion status for a job that doesn't run at regular
    # intervals, it should be ignored.
    await job_send.send(JobStateEvent(sched_job1_id, sched_id,
        RunState.COMPLETED, datetime.fromtimestamp(trio.current_time())))

    # Then it should run again three hours later.
    await trio.sleep(3 * 60 * 60 + 1)
    assert start_job_count == 2

    # Remove the schedule and ensure that it does not run again.
    scheduler.remove_schedule(sched.id)


async def test_schedule_two_events(autojump_clock, nursery):
    ''' Create two schedules and ensure they execute at the correct times. '''
    sched1_id = '123e4567-e89b-12d3-a456-426655440001'
    sched1_job_id = '123e4567-e89b-12d3-a456-426655440011'
    sched2_id = '123e4567-e89b-12d3-a456-426655440002'
    sched2_job_id = '123e4567-e89b-12d3-a456-426655440012'
    base_date = datetime.fromtimestamp(trio.current_time(), timezone.utc)

    start_job_count = 0
    start_job_args = None
    async def start_job(*args):
        nonlocal start_job_count
        nonlocal start_job_args
        start_job_count += 1
        start_job_args = args

    # This schedule runs every 3 hours after the last job started, and the
    # last job just started.
    s1 = make_schedule(1, num_units=3, timing='REGULAR_INTERVAL',
        seeds=['http://one.example'], tags=['tag1'])
    s1_doc = s1.to_doc()
    s1_doc['latest_job'] = {'name': 'Test Job @ 0',
        'run_state': RunState.RUNNING, 'started_at': base_date,
        'completed_at': None}

    # This schedule runs 2 hours after the last job finished, and the last
    # job just finished.
    s2 = make_schedule(2, num_units=2, timing='AFTER_PREVIOUS_JOB_FINISHED',
        seeds=['http://two.example'], tags=['tag2'])
    s2_doc = s2.to_doc()
    s2_doc['latest_job'] = {'name': 'Test Job @ 1',
        'run_state': RunState.COMPLETED, 'started_at': base_date,
        'completed_at': base_date}

    # Set up scheduler.
    job_send, job_recv = trio.open_memory_channel(0)
    db = Mock()
    db.get_schedule_docs.return_value = async_iter([s1_doc, s2_doc])
    db.update_job_count.side_effect = AsyncMock()
    crawl_manager = Mock()
    crawl_manager.get_job_state_channel.return_value = job_recv
    crawl_manager.start_job.side_effect = start_job
    scheduler = Scheduler(db, crawl_manager)
    nursery.start_soon(scheduler.run)

    # Schedule 2 should start a job 2 hours later.
    await trio.sleep(60 * 60)
    assert crawl_manager.start_job.call_count == 0
    await trio.sleep(60 * 60 + 1)
    assert crawl_manager.start_job.call_count == 1
    assert start_job_args[0].startswith('Test Job @')
    assert start_job_args[1] == ['http://two.example']
    assert start_job_args[2] == ['tag2']
    assert start_job_args[4] == sched2_id

    # Schedule 1 should start a job 1 hour later.
    await trio.sleep(60 * 60)
    assert crawl_manager.start_job.call_count == 2
    assert start_job_args[0].startswith('Test Job @')
    assert start_job_args[1] == ['http://one.example']
    assert start_job_args[2] == ['tag1']
    assert start_job_args[4] == sched1_id
