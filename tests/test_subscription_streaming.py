"""
Tests for the streaming list subscription classes:
  - PolicyListSubscription   – streams policy add/update/delete events
  - ScheduleListSubscription – streams schedule add/update/delete events
  - DomainLoginListSubscription – streams domain-login add/update/delete events

Each subscription wraps an async database changefeed and serialises events
as protobuf ``ServerMessage`` frames sent over a WebSocket.
"""
from unittest.mock import Mock
from uuid import UUID

import pytest
import trio

from . import assert_max_elapsed
from starbelly.starbelly_pb2 import (
    DomainLoginEvent,
    PolicyEvent,
    ScheduleEvent,
    ServerMessage,
)
from starbelly.subscription import (
    DomainLoginListSubscription,
    PolicyListSubscription,
    ScheduleListSubscription,
)


POLICY1_ID = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
POLICY2_ID = UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
SCHEDULE1_ID = UUID('cccccccc-cccc-cccc-cccc-cccccccccccc')
SCHEDULE2_ID = UUID('dddddddd-dddd-dddd-dddd-dddddddddddd')


class MockWebsocket:
    '''A simple mock websocket useful for testing.'''
    def __init__(self):
        self._send, self._recv = trio.open_memory_channel(0)

    async def get_message(self):
        return await self._recv.receive()

    async def send_message(self, message):
        await self._send.send(message)


async def make_async_gen(items):
    '''Helper: yields each item in the list as an async generator.'''
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# PolicyListSubscription
# ---------------------------------------------------------------------------

async def test_policy_list_subscription_add(nursery):
    '''An ADDED change document sends a PolicyEvent with event_type=ADDED.'''
    policy_doc = {
        'id': str(POLICY1_ID),
        'name': 'Default Policy',
    }
    change = {'old_val': None, 'new_val': policy_doc}

    subscription_db = Mock()
    subscription_db.stream_policies.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = PolicyListSubscription(
        id_=1, websocket=websocket, subscription_db=subscription_db
    )
    assert repr(subscription) == '<PolicyListSubscription id=1>'

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        msg = ServerMessage.FromString(data)
        event = msg.event
        assert event.subscription_id == 1
        assert event.HasField('policy_event')
        pe = event.policy_event
        assert pe.event_type == PolicyEvent.ADDED
        assert pe.policy_id == POLICY1_ID.bytes
        assert pe.name == 'Default Policy'


async def test_policy_list_subscription_update(nursery):
    '''An UPDATED change document sends a PolicyEvent with event_type=UPDATED.'''
    old_doc = {'id': str(POLICY1_ID), 'name': 'Old Name'}
    new_doc = {'id': str(POLICY1_ID), 'name': 'New Name'}
    change = {'old_val': old_doc, 'new_val': new_doc}

    subscription_db = Mock()
    subscription_db.stream_policies.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = PolicyListSubscription(
        id_=2, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        pe = ServerMessage.FromString(data).event.policy_event
        assert pe.event_type == PolicyEvent.UPDATED
        assert pe.policy_id == POLICY1_ID.bytes
        assert pe.name == 'New Name'


async def test_policy_list_subscription_delete(nursery):
    '''A DELETED change document sends a PolicyEvent with event_type=DELETED.'''
    policy_doc = {'id': str(POLICY1_ID), 'name': 'Deleted Policy'}
    change = {'old_val': policy_doc, 'new_val': None}

    subscription_db = Mock()
    subscription_db.stream_policies.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = PolicyListSubscription(
        id_=3, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        pe = ServerMessage.FromString(data).event.policy_event
        assert pe.event_type == PolicyEvent.DELETED
        assert pe.policy_id == POLICY1_ID.bytes
        assert pe.name == 'Deleted Policy'


async def test_policy_list_subscription_multiple_events(nursery):
    '''Multiple change events are sent in order.'''
    doc1 = {'id': str(POLICY1_ID), 'name': 'Policy 1'}
    doc2 = {'id': str(POLICY2_ID), 'name': 'Policy 2'}
    changes = [
        {'old_val': None, 'new_val': doc1},
        {'old_val': None, 'new_val': doc2},
    ]

    subscription_db = Mock()
    subscription_db.stream_policies.return_value = make_async_gen(changes)

    websocket = MockWebsocket()
    subscription = PolicyListSubscription(
        id_=4, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data1 = await websocket.get_message()
        pe1 = ServerMessage.FromString(data1).event.policy_event
        assert pe1.event_type == PolicyEvent.ADDED
        assert pe1.name == 'Policy 1'

        data2 = await websocket.get_message()
        pe2 = ServerMessage.FromString(data2).event.policy_event
        assert pe2.event_type == PolicyEvent.ADDED
        assert pe2.name == 'Policy 2'


async def test_policy_list_subscription_cancel(nursery):
    '''cancel() terminates a running subscription.'''
    send, recv = trio.open_memory_channel(0)

    async def blocking_gen():
        async with recv:
            async for item in recv:
                yield item

    subscription_db = Mock()
    subscription_db.stream_policies.return_value = blocking_gen()

    websocket = MockWebsocket()
    subscription = PolicyListSubscription(
        id_=5, websocket=websocket, subscription_db=subscription_db
    )

    await nursery.start(lambda task_status: start_subscription(
        subscription, task_status, nursery
    ))
    subscription.cancel()


async def start_subscription(subscription, task_status, nursery):
    '''Helper: starts the subscription and signals when it has begun running.'''
    async with trio.open_nursery() as inner:
        inner.start_soon(subscription.run)
        await trio.sleep(0)  # Let run() start
        task_status.started()


# ---------------------------------------------------------------------------
# ScheduleListSubscription
# ---------------------------------------------------------------------------

async def test_schedule_list_subscription_add(nursery):
    '''An ADDED change document sends a ScheduleEvent with event_type=ADDED.'''
    schedule_doc = {
        'id': str(SCHEDULE1_ID),
        'schedule_name': 'Nightly Crawl',
    }
    change = {'old_val': None, 'new_val': schedule_doc}

    subscription_db = Mock()
    subscription_db.stream_schedules.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = ScheduleListSubscription(
        id_=10, websocket=websocket, subscription_db=subscription_db
    )
    assert repr(subscription) == '<ScheduleListSubscription id=10>'

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        event = ServerMessage.FromString(data).event
        assert event.subscription_id == 10
        assert event.HasField('schedule_event')
        se = event.schedule_event
        assert se.event_type == ScheduleEvent.ADDED
        assert se.schedule_id == SCHEDULE1_ID.bytes
        assert se.schedule_name == 'Nightly Crawl'


async def test_schedule_list_subscription_update(nursery):
    '''An UPDATED change document sends a ScheduleEvent with event_type=UPDATED.'''
    old_doc = {'id': str(SCHEDULE1_ID), 'schedule_name': 'Old Name'}
    new_doc = {'id': str(SCHEDULE1_ID), 'schedule_name': 'New Name'}
    change = {'old_val': old_doc, 'new_val': new_doc}

    subscription_db = Mock()
    subscription_db.stream_schedules.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = ScheduleListSubscription(
        id_=11, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        se = ServerMessage.FromString(data).event.schedule_event
        assert se.event_type == ScheduleEvent.UPDATED
        assert se.schedule_id == SCHEDULE1_ID.bytes
        assert se.schedule_name == 'New Name'


async def test_schedule_list_subscription_delete(nursery):
    '''A DELETED change document sends a ScheduleEvent with event_type=DELETED.'''
    schedule_doc = {'id': str(SCHEDULE1_ID), 'schedule_name': 'Gone Schedule'}
    change = {'old_val': schedule_doc, 'new_val': None}

    subscription_db = Mock()
    subscription_db.stream_schedules.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = ScheduleListSubscription(
        id_=12, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        se = ServerMessage.FromString(data).event.schedule_event
        assert se.event_type == ScheduleEvent.DELETED
        assert se.schedule_id == SCHEDULE1_ID.bytes
        assert se.schedule_name == 'Gone Schedule'


# ---------------------------------------------------------------------------
# DomainLoginListSubscription
# ---------------------------------------------------------------------------

async def test_domain_login_subscription_add(nursery):
    '''An ADDED change document sends a DomainLoginEvent with event_type=ADDED.'''
    login_doc = {'domain': 'example.com'}
    change = {'old_val': None, 'new_val': login_doc}

    subscription_db = Mock()
    subscription_db.stream_domain_logins.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = DomainLoginListSubscription(
        id_=20, websocket=websocket, subscription_db=subscription_db
    )
    assert repr(subscription) == '<DomainLoginListSubscription id=20>'

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        event = ServerMessage.FromString(data).event
        assert event.subscription_id == 20
        assert event.HasField('domain_login_event')
        le = event.domain_login_event
        assert le.event_type == DomainLoginEvent.ADDED
        assert le.domain == 'example.com'


async def test_domain_login_subscription_update(nursery):
    '''An UPDATED change document sends a DomainLoginEvent with event_type=UPDATED.'''
    old_doc = {'domain': 'example.com'}
    new_doc = {'domain': 'example.com'}
    change = {'old_val': old_doc, 'new_val': new_doc}

    subscription_db = Mock()
    subscription_db.stream_domain_logins.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = DomainLoginListSubscription(
        id_=21, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        le = ServerMessage.FromString(data).event.domain_login_event
        assert le.event_type == DomainLoginEvent.UPDATED
        assert le.domain == 'example.com'


async def test_domain_login_subscription_delete(nursery):
    '''A DELETED change document sends a DomainLoginEvent with event_type=DELETED.'''
    login_doc = {'domain': 'gone.example.com'}
    change = {'old_val': login_doc, 'new_val': None}

    subscription_db = Mock()
    subscription_db.stream_domain_logins.return_value = make_async_gen([change])

    websocket = MockWebsocket()
    subscription = DomainLoginListSubscription(
        id_=22, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data = await websocket.get_message()
        le = ServerMessage.FromString(data).event.domain_login_event
        assert le.event_type == DomainLoginEvent.DELETED
        assert le.domain == 'gone.example.com'


async def test_domain_login_subscription_multiple_domains(nursery):
    '''Multiple domain login changes are sent in order.'''
    changes = [
        {'old_val': None, 'new_val': {'domain': 'site1.example.com'}},
        {'old_val': None, 'new_val': {'domain': 'site2.example.com'}},
    ]

    subscription_db = Mock()
    subscription_db.stream_domain_logins.return_value = make_async_gen(changes)

    websocket = MockWebsocket()
    subscription = DomainLoginListSubscription(
        id_=23, websocket=websocket, subscription_db=subscription_db
    )

    nursery.start_soon(subscription.run)

    with assert_max_elapsed(0.5):
        data1 = await websocket.get_message()
        le1 = ServerMessage.FromString(data1).event.domain_login_event
        assert le1.domain == 'site1.example.com'

        data2 = await websocket.get_message()
        le2 = ServerMessage.FromString(data2).event.domain_login_event
        assert le2.domain == 'site2.example.com'
