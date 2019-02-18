from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest
import trio
import trio.hazmat

from . import assert_elapsed, assert_max_elapsed, assert_min_elapsed
from starbelly.job import StatsTracker
from starbelly.starbelly_pb2 import JobRunState, ServerMessage
from starbelly.subscription import (
    ExponentialBackoff,
    JobStatusSubscription,
    ResourceMonitorSubscription,
    SyncTokenError,
    SyncTokenInt,
    TaskMonitorSubscription,
)


def test_sync_token_int():
    token = b'\x01\x11\x00\x00\x00\x00\x00\x00\x00'
    assert SyncTokenInt.decode(token) == 0x11
    assert SyncTokenInt.encode(0x11) == token


def test_decode_wrong_type():
    token = b'\x00\x11\x00\x00\x00\x00\x00\x00\x00'
    with pytest.raises(SyncTokenError):
        assert SyncTokenInt.decode(token)


def test_decode_malformed():
    token = b'\x01\x00\x00'
    with pytest.raises(SyncTokenError):
        assert SyncTokenInt.decode(token)


async def test_job_state_subscription(autojump_clock, nursery):
    job1_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    job2_id = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
    job1_doc = {
        'id': str(job1_id),
        'name': 'Job #1',
        'seeds': ['https://job1.example'],
        'tags': ['tag1a', 'tag1b'],
        'item_count': 10,
        'http_success_count': 7,
        'http_error_count': 2,
        'exception_count': 1,
        'http_status_counts': {200: 7, 404: 2},
        'started_at': datetime(2019, 1, 25, 14, 44, 0, tzinfo=timezone.utc),
        'completed_at': None,
        'run_state': 'RUNNING',
    }
    job2_doc = {
        'id': str(job2_id),
        'name': 'Job #2',
        'seeds': ['https://job2.example'],
        'tags': ['tag2a'],
        'item_count': 20,
        'http_success_count': 14,
        'http_error_count': 4,
        'exception_count': 2,
        'http_status_counts': {200: 14, 404: 4},
        'started_at': datetime(2019, 1, 25, 14, 55, 0, tzinfo=timezone.utc),
        'completed_at': None,
        'run_state': 'RUNNING',
    }
    stats_tracker = StatsTracker()
    stats_tracker.add_job(job1_doc)
    stats_tracker.add_job(job2_doc)
    send_stream, receive_stream = trio.testing.memory_stream_pair()
    subscription = JobStatusSubscription(id_=1, stats_tracker=stats_tracker,
        stream=send_stream, stream_lock=trio.Lock(), min_interval=2)
    assert repr(subscription) == '<JobStatusSubscription id=1>'
    with pytest.raises(Exception):
        # Can't cancel before it starts running:
        subscription.cancel()
    nursery.start_soon(subscription.run)

    # The first two items should be received immediately and in full.
    with assert_max_elapsed(0.1):
        data = await receive_stream.receive_some(4096)
        message1 = ServerMessage.FromString(data).event
        assert message1.subscription_id == 1
        assert len(message1.job_list.jobs) == 2
        job1 = message1.job_list.jobs[0]
        assert job1.job_id == job1_id.bytes
        assert job1.name == 'Job #1'
        assert job1.seeds[0] == 'https://job1.example'
        assert job1.tag_list.tags[0] == 'tag1a'
        assert job1.tag_list.tags[1] == 'tag1b'
        assert job1.item_count == 10
        assert job1.http_success_count == 7
        assert job1.http_error_count == 2
        assert job1.exception_count == 1
        assert job1.http_status_counts[200] == 7
        assert job1.http_status_counts[404] == 2
        assert job1.started_at == '2019-01-25T14:44:00+00:00'
        assert not job1.HasField('completed_at')
        assert job1.run_state == JobRunState.Value('RUNNING')

        job2 = message1.job_list.jobs[1]
        assert job2.job_id == job2_id.bytes
        assert job2.name == 'Job #2'
        assert job2.seeds[0] == 'https://job2.example'
        assert job2.tag_list.tags[0] == 'tag2a'
        assert job2.item_count == 20
        assert job2.http_success_count == 14
        assert job2.http_error_count == 4
        assert job2.exception_count == 2
        assert job2.http_status_counts[200] == 14
        assert job2.http_status_counts[404] == 4
        assert job2.started_at == '2019-01-25T14:55:00+00:00'
        assert not job2.HasField('completed_at')
        assert job2.run_state == JobRunState.Value('RUNNING')

    # Add 1 item to job 1. Two seconds later, we should get an update for job 1
    # but not job 2.
    with assert_min_elapsed(2):
        job1_doc.update({
            'item_count': 11,
            'http_success_count': 8,
            'http_status_counts': {200: 8, 404: 2},
        })
        data = await receive_stream.receive_some(4096)
        message2 = ServerMessage.FromString(data).event
        assert message2.subscription_id == 1
        assert len(message2.job_list.jobs) == 1
        job1 = message2.job_list.jobs[0]
        assert job1.name == 'Job #1'
        assert job1.seeds[0] == 'https://job1.example'
        assert job1.tag_list.tags[0] == 'tag1a'
        assert job1.tag_list.tags[1] == 'tag1b'
        assert job1.item_count == 11
        assert job1.http_success_count == 8
        assert job1.http_error_count == 2
        assert job1.exception_count == 1
        assert job1.http_status_counts[200] == 8
        assert job1.http_status_counts[404] == 2
        assert job1.started_at == '2019-01-25T14:44:00+00:00'
        assert not job1.HasField('completed_at')
        assert job1.run_state == JobRunState.Value('RUNNING')

    # Add 2 items to job 2. Two seconds later, we should get an update for job 2
    # but not job 1.
    with assert_min_elapsed(2):
        completed_at = datetime(2019, 1, 25, 14, 56, 0, tzinfo=timezone.utc)
        job2_doc.update({
            'item_count': 22,
            'http_success_count': 15,
            'http_error_count': 5,
            'http_status_counts': {200: 15, 404: 5},
        })
        data = await receive_stream.receive_some(4096)
        message3 = ServerMessage.FromString(data).event
        assert message3.subscription_id == 1
        assert len(message3.job_list.jobs) == 1
        job2 = message3.job_list.jobs[0]
        assert job2.name == 'Job #2'
        assert job2.seeds[0] == 'https://job2.example'
        assert job2.tag_list.tags[0] == 'tag2a'
        assert job2.item_count == 22
        assert job2.http_success_count == 15
        assert job2.http_error_count == 5
        assert job2.exception_count == 2
        assert job2.http_status_counts[200] == 15
        assert job2.http_status_counts[404] == 5
        assert job2.started_at == '2019-01-25T14:55:00+00:00'
        assert job2.run_state == JobRunState.Value('RUNNING')

    # Cancel the subscription and wait 2 seconds to make sure it doesn't send us
    # any more events.
    subscription.cancel()
    with pytest.raises(trio.TooSlowError):
        with trio.fail_after(2):
            data = await receive_stream.receive_some(4096)


async def test_resource_subscription(autojump_clock, nursery):
    # Set up fixtures
    job1_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    job2_id = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
    resource_monitor = Mock()
    measurement1 = {
        'timestamp': datetime(2019, 1, 25, 0, 0, 0, tzinfo=timezone.utc),
        'cpus': [0.99, 0.55],
        'memory_used': 1_000_000,
        'memory_total': 2_000_000,
        'disks': [{
            'mount': '/root',
            'used': 3_000_000,
            'total': 4_000_000,
        },{
            'mount': '/home',
            'used': 5_000_000,
            'total': 6_000_000,
        }],
        'networks': [{
            'name': 'eth0',
            'sent': 7_000_000,
            'received': 8_000_000,
        },{
            'name': 'eth1',
            'sent': 9_000_000,
            'received': 10_000_000,
        }],
        'jobs': [{
            'id': str(job1_id),
            'name': 'Test 1 Job',
            'current_downloads':3,
        },{
            'id': str(job2_id),
            'name': 'Test 2 Job',
            'current_downloads': 2,
        }],
        'current_downloads': 5,
        'maximum_downloads': 10,
        'rate_limiter': 150,
    }
    measurement2 = measurement1.copy() # Note: SHALLOW COPY!
    measurement2['timestamp'] = datetime(2019, 1, 25, 0, 0, 1,
        tzinfo=timezone.utc)
    measurement2['memory_used'] = 1_000_001
    measurement3 = measurement1.copy() # Note: SHALLOW COPY!
    measurement3['timestamp'] = datetime(2019, 1, 25, 0, 0, 2,
        tzinfo=timezone.utc)
    measurement3['memory_used'] = 1_000_002
    resource_monitor.history.return_value = [measurement1, measurement2]
    send_channel, recv_channel = trio.open_memory_channel(0)
    resource_monitor.get_channel.return_value = recv_channel

    # Instantiate subscription. Ask for 3 historical measurements, but only 2
    # are available so it should just send those 2.
    send_stream, receive_stream = trio.testing.memory_stream_pair()
    subscription = ResourceMonitorSubscription(id_=1, stream=send_stream,
        stream_lock=trio.Lock(), resource_monitor=resource_monitor, history=3)
    assert repr(subscription) == '<ResourceMonitorSubscription id=1>'
    nursery.start_soon(subscription.run)

    # We should be able to read two events immediately.
    with assert_max_elapsed(0.1):
        data = await receive_stream.receive_some(4096)
        event1 = ServerMessage.FromString(data).event
        assert event1.subscription_id == 1
        frame1 = event1.resource_frame
        assert frame1.timestamp == '2019-01-25T00:00:00+00:00'
        assert frame1.cpus[0].usage == 0.99
        assert frame1.cpus[1].usage == 0.55
        assert frame1.memory.used == 1_000_000
        assert frame1.memory.total == 2_000_000
        assert frame1.disks[0].mount == '/root'
        assert frame1.disks[0].used == 3_000_000
        assert frame1.disks[0].total == 4_000_000
        assert frame1.disks[1].mount == '/home'
        assert frame1.disks[1].used == 5_000_000
        assert frame1.disks[1].total == 6_000_000
        assert frame1.networks[0].name == 'eth0'
        assert frame1.networks[0].sent == 7_000_000
        assert frame1.networks[0].received == 8_000_000
        assert frame1.networks[1].name == 'eth1'
        assert frame1.networks[1].sent == 9_000_000
        assert frame1.networks[1].received == 10_000_000
        assert frame1.jobs[0].job_id == job1_id.bytes
        assert frame1.jobs[0].name == 'Test 1 Job'
        assert frame1.jobs[0].current_downloads == 3
        assert frame1.jobs[1].job_id == job2_id.bytes
        assert frame1.jobs[1].name == 'Test 2 Job'
        assert frame1.jobs[1].current_downloads == 2
        assert frame1.current_downloads == 5
        assert frame1.maximum_downloads == 10
        assert frame1.rate_limiter == 150

        data = await receive_stream.receive_some(4096)
        event2 = ServerMessage.FromString(data).event
        assert event2.subscription_id == 1
        frame2 = event2.resource_frame
        assert frame2.timestamp == '2019-01-25T00:00:01+00:00'
        assert frame2.memory.used == 1_000_001

    # The third frame does not arrive immediately.
    with pytest.raises(trio.TooSlowError):
        with trio.fail_after(2):
            data = await receive_stream.receive_some(4096)

    # Now emulate the resource monitor sending another measurement, and we
    # should be able to receive it immediately.
    with assert_max_elapsed(0.1):
        await send_channel.send(measurement3)
        data = await receive_stream.receive_some(4096)
        event3 = ServerMessage.FromString(data).event
        assert event3.subscription_id == 1
        frame3 = event3.resource_frame
        assert frame3.timestamp == '2019-01-25T00:00:02+00:00'
        assert frame3.memory.used == 1_000_002


async def test_task_monitor(autojump_clock, nursery):
    # To simplify testing, we pick the current task as the root task:
    root_task = trio.hazmat.current_task()
    send_stream, receive_stream = trio.testing.memory_stream_pair()
    subscription = TaskMonitorSubscription(id_=1, stream=send_stream,
        stream_lock=trio.Lock(), period=2.0, root_task=root_task)

    # We create a few dummy tasks that will show up in the task monitor.
    async def dummy_parent(task_status):
        async with trio.open_nursery() as inner:
            await inner.start(dummy_child, name='Dummy Child 1')
            await inner.start(dummy_child, name='Dummy Child 2')
            task_status.started()

    async def dummy_child(task_status):
        task_status.started()
        await trio.sleep_forever()

    await nursery.start(dummy_parent, name='Dummy Parent 1')
    await nursery.start(dummy_parent, name='Dummy Parent 2')
    nursery.start_soon(subscription.run, name='Task Monitor Subscription')

    # We should receive the first event right away.
    with assert_max_elapsed(0.1):
        data = await receive_stream.receive_some(4096)
        event1 = ServerMessage.FromString(data).event
        assert event1.subscription_id == 1
        task_tree = event1.task_tree
        assert task_tree.name == '<Root>'
        subtask_1 = task_tree.subtasks[0]
        assert subtask_1.name == 'Dummy Parent 1'
        subtask_1_1 = subtask_1.subtasks[0]
        assert subtask_1_1.name == 'Dummy Child 1'
        subtask_1_2 = subtask_1.subtasks[1]
        assert subtask_1_2.name == 'Dummy Child 2'
        subtask_2 = task_tree.subtasks[1]
        assert subtask_2.name == 'Dummy Parent 2'
        subtask_2_1 = subtask_2.subtasks[0]
        assert subtask_2_1.name == 'Dummy Child 1'
        subtask_2_2 = subtask_2.subtasks[1]
        assert subtask_2_2.name == 'Dummy Child 2'
        subtask_3 = task_tree.subtasks[2]
        assert subtask_3.name == 'Task Monitor Subscription'

    # The second event won't arrive for two more seconds.
    with assert_min_elapsed(2.0):
        data = await receive_stream.receive_some(4096)
        event2 = ServerMessage.FromString(data).event
        assert event1.subscription_id == 1
        task_tree = event1.task_tree
        assert task_tree.name == '<Root>'
        assert len(task_tree.subtasks) == 3

    subscription.cancel()
