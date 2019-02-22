#TODO I wrote this before I started putting all of the database queries into
# a separate module. This could be modified into a unit test and probably
# grouped into the test_server.py module.

from datetime import datetime, timezone
import gzip
import logging
from unittest.mock import Mock
from uuid import UUID

import pytest
from rethinkdb import RethinkDB
import trio

from . import fail_after
from starbelly.db import SubscriptionDb
from starbelly.job import JobStateEvent, RunState
from starbelly.starbelly_pb2 import ServerMessage, SubscriptionClosed
from starbelly.subscription import (
    CrawlSyncSubscription,
)


r = RethinkDB()
r.set_loop_type('trio')
logger = logging.getLogger(__name__)


@pytest.fixture
async def db_pool(nursery):
    r = RethinkDB()
    db_pool = r.ConnectionPool(db='test', nursery=nursery)
    yield db_pool
    await db_pool.close()


@pytest.fixture
async def job_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('job').run(conn)
    yield r.table('job')
    await r.table_drop('job').run(conn)


@pytest.fixture
async def response_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('response').run(conn)
        await r.table('response').index_create('job_sync',
            [r.row['job_id'], r.row['sequence']]).run(conn)
        await r.table('response').index_wait('job_sync').run(conn)
    yield r.table('response')
    await r.table_drop('response').run(conn)


@pytest.fixture
async def response_body_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('response_body').run(conn)
    yield r.table('response_body')
    await r.table_drop('response_body').run(conn)


class MockWebsocket:
    ''' A simple mock websocket useful for testing. '''
    def __init__(self):
        self._send, self._recv = trio.open_memory_channel(0)

    async def get_message(self):
        message = await self._recv.receive()
        return message

    async def send_message(self, message):
        await self._send.send(message)


@fail_after(3)
async def test_subscribe_to_crawl(db_pool, job_table, response_table,
        response_body_table, nursery):
    ''' Subscribe to a job that has 3 items. Simulate interrupting and resuming
    sync using a sync token. '''
    job_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-000000000000')

    # Create sample data: a job with 3 downloaded items.
    async with db_pool.connection() as conn:
        await r.table('job').insert({
            'id': str(job_id),
            'run_state': RunState.COMPLETED,
        }).run(conn)

        await r.table('response_body').insert({
            # Response bodies are keyed by the blake2 hash of the body.
            'id': b'\x00' * 32,
            'is_compressed': True,
            'body': b'\x1f\x8b\x08\x00\x0b\xf0I\\\x02\xff\x0bI-.QH\xc9O'
                    b'.\xcdM\xcd+QP6\x04\x00\xe8\x8b\x9a\x93\x10\x00\x00\x00',
        }).run(conn)
        await r.table('response').insert({
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-000000000000',
            'body_id': b'\x00' * 32,
            'sequence': 1,
            'started_at':   datetime(2019, 1, 1, 1, 1, 0, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 1, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 1.0,
            'is_success': True,
            'job_id': str(job_id),
            'url':     'https://www.example/',
            'url_can': 'https://www.example/',
            'status_code': 200,
            'content_type': 'text/plain',
            'headers': [
                'Server', 'FakeServer 1.0',
                'X-Foo', 'Bar',
            ]
        }).run(conn)

        await r.table('response_body').insert({
            'id': b'\x01' * 32,
            'is_compressed': False,
            'body': b'File not found',
        }).run(conn)
        await r.table('response').insert({
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-000000000001',
            'body_id': b'\x01' * 32,
            'sequence': 3,
            'started_at':   datetime(2019, 1, 1, 1, 1, 2, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 3, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 2.0,
            'is_success': False,
            'job_id': str(job_id),
            'url':     'https://www.example/foo',
            'url_can': 'https://www.example/foo',
            'status_code': 404,
            'content_type': 'text/plain',
            'headers': []
        }).run(conn)

        await r.table('response_body').insert({
            'id': b'\x02' * 32,
            'is_compressed': True,
            'body': b'\x1f\x8b\x08\x00\xe7\x01J\\\x02\xff\x0bI-.QH\xc9O.\xcdM'
                    b'\xcd+QP6\x02\x00R\xda\x93\n\x10\x00\x00\x00'
        }).run(conn)
        await r.table('response').insert({
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-000000000002',
            'body_id': b'\x02' * 32,
            'sequence': 5,
            'started_at':   datetime(2019, 1, 1, 1, 1, 4, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 5, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 2.0,
            'is_success': True,
            'job_id': str(job_id),
            'url':     'https://www.example/bar',
            'url_can': 'https://www.example/bar',
            'status_code': 200,
            'content_type': 'text/plain',
            'headers': []
        }).run(conn)

    # Instantiate subscription
    websocket = MockWebsocket()
    job_send, job_recv = trio.open_memory_channel(0)
    subscription_db = SubscriptionDb(db_pool)
    subscription = CrawlSyncSubscription(id_=1, websocket=websocket,
        job_id=str(job_id), subscription_db=subscription_db,
        compression_ok=True, job_state_recv=job_recv, sync_token=None)
    assert repr(subscription) == '<CrawlSyncSubscription id=1 job_id=aaaaaaaa>'
    nursery.start_soon(subscription.run)

    # Read from subscription
    data = await websocket.get_message()
    message1 = ServerMessage.FromString(data).event
    assert message1.subscription_id == 1
    item1 = message1.sync_item.item
    assert item1.job_id == job_id.bytes
    assert item1.url     == 'https://www.example/'
    assert item1.url_can == 'https://www.example/'
    assert item1.started_at   == '2019-01-01T01:01:00+00:00'
    assert item1.completed_at == '2019-01-01T01:01:01+00:00'
    assert item1.cost == 1.0
    assert item1.duration == 1.0
    assert item1.status_code == 200
    assert item1.headers[0].key == 'Server'
    assert item1.headers[0].value == 'FakeServer 1.0'
    assert item1.headers[1].key == 'X-Foo'
    assert item1.headers[1].value == 'Bar'
    assert item1.is_success
    assert item1.is_compressed
    assert gzip.decompress(item1.body) == b'Test document #1'
    sync_token = message1.sync_item.token

    data = await websocket.get_message()
    message2 = ServerMessage.FromString(data).event
    assert message2.subscription_id == 1
    item2 = message2.sync_item.item
    assert item2.job_id == job_id.bytes
    assert item2.url     == 'https://www.example/foo'
    assert item2.url_can == 'https://www.example/foo'
    assert item2.started_at   == '2019-01-01T01:01:02+00:00'
    assert item2.completed_at == '2019-01-01T01:01:03+00:00'
    assert item2.cost == 2.0
    assert item2.duration == 1.0
    assert item2.status_code == 404
    assert not item2.is_success
    assert not item2.is_compressed
    assert item2.body == b'File not found'

    # Act as if the subscription was interrupted in between the first and second
    # items, and then resume from there.
    subscription.cancel()
    websocket = MockWebsocket()
    job_send, job_recv = trio.open_memory_channel(0)
    subscription_db = SubscriptionDb(db_pool)
    subscription = CrawlSyncSubscription(id_=2, websocket=websocket,
        job_id=str(job_id), subscription_db=subscription_db,
        compression_ok=True, job_state_recv=job_recv, sync_token=sync_token)
    assert repr(subscription) == '<CrawlSyncSubscription id=2 job_id=aaaaaaaa>'
    nursery.start_soon(subscription.run)

    # The next message will be a repeat of the previous, since we "interrupted"
    # the sync before the previous item finished.
    data = await websocket.get_message()
    message3 = ServerMessage.FromString(data).event
    assert message3.subscription_id == 2
    item3 = message3.sync_item.item
    assert item3.url == 'https://www.example/foo'

    data = await websocket.get_message()
    message4 = ServerMessage.FromString(data).event
    assert message4.subscription_id == 2
    item4 = message4.sync_item.item
    assert item4.job_id == job_id.bytes
    assert item4.url     == 'https://www.example/bar'
    assert item4.url_can == 'https://www.example/bar'
    assert item4.started_at   == '2019-01-01T01:01:04+00:00'
    assert item4.completed_at == '2019-01-01T01:01:05+00:00'
    assert item4.cost == 2.0
    assert item4.duration == 1.0
    assert item4.status_code == 200
    assert item4.is_success
    assert item4.is_compressed
    assert gzip.decompress(item4.body) == b'Test document #2'

    data = await websocket.get_message()
    message5 = ServerMessage.FromString(data).event
    assert message5.subscription_id == 2
    assert message5.subscription_closed.reason == SubscriptionClosed.COMPLETE


@fail_after(3)
async def test_subscribe_to_crawl_decompress(db_pool, job_table, response_table,
        response_body_table, nursery):
    ''' If requested, the server will decompress response bodies. '''
    job_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-000000000000')

    # Create sample data: a job with 1 downloaded item.
    async with db_pool.connection() as conn:
        await r.table('job').insert({
            'id': str(job_id),
            'run_state': RunState.COMPLETED,
        }).run(conn)

        await r.table('response_body').insert({
            'id': b'\x00' * 32,
            'is_compressed': True,
            'body': b'\x1f\x8b\x08\x00\x0b\xf0I\\\x02\xff\x0bI-.QH\xc9O'
                    b'.\xcdM\xcd+QP6\x04\x00\xe8\x8b\x9a\x93\x10\x00\x00\x00',
        }).run(conn)
        await r.table('response').insert({
            'id': UUID('bbbbbbbb-bbbb-bbbb-bbbb-000000000000').bytes,
            'body_id': b'\x00' * 32,
            'sequence': 1,
            'started_at':   datetime(2019, 1, 1, 1, 1, 0, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 1, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 1.0,
            'is_success': True,
            'job_id': str(job_id),
            'url':     'https://www.example/',
            'url_can': 'https://www.example/',
            'status_code': 200,
            'content_type': 'text/plain',
            'headers': []
        }).run(conn)

    # Instantiate subscription
    logger.info('Creating subscription…')
    websocket = MockWebsocket()
    job_send, job_recv = trio.open_memory_channel(0)
    subscription_db = SubscriptionDb(db_pool)
    subscription = CrawlSyncSubscription(id_=1, websocket=websocket,
        job_id=str(job_id), subscription_db=subscription_db,
        compression_ok=False, job_state_recv=job_recv, sync_token=None)
    assert repr(subscription) == '<CrawlSyncSubscription id=1 job_id=aaaaaaaa>'
    nursery.start_soon(subscription.run)

    # Read from subscription
    logger.info('Reading one event…')
    data = await websocket.get_message()
    message1 = ServerMessage.FromString(data).event
    assert message1.subscription_id == 1
    item1 = message1.sync_item.item
    assert item1.job_id == job_id.bytes
    assert item1.url     == 'https://www.example/'
    assert item1.url_can == 'https://www.example/'
    assert item1.started_at   == '2019-01-01T01:01:00+00:00'
    assert item1.completed_at == '2019-01-01T01:01:01+00:00'
    assert item1.cost == 1.0
    assert item1.duration == 1.0
    assert item1.status_code == 200
    assert item1.is_success
    assert not item1.is_compressed
    assert item1.body == b'Test document #1'

    logger.info('Reading subscription close…')
    data = await websocket.get_message()
    message2 = ServerMessage.FromString(data).event
    assert message2.subscription_id == 1
    assert message2.subscription_closed.reason == SubscriptionClosed.COMPLETE


@fail_after(6)
async def test_subscribe_to_unfinished_crawl(db_pool, job_table, response_table,
        response_body_table, nursery):
    ''' Subscribe to a job that currently has 1 items. After receiving the first
    item, the crawl adds a second item and finishes. The subscription should
    send the second item and also finish. '''
    job_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-000000000000')

    # Create sample data: a job with 1 downloaded items.
    async with db_pool.connection() as conn:
        await r.table('job').insert({
            'id': str(job_id),
            'run_state': RunState.RUNNING,
        }).run(conn)

        await r.table('response_body').insert({
            'id': b'\x00' * 32,
            'is_compressed': True,
            'body': b'\x1f\x8b\x08\x00\x0b\xf0I\\\x02\xff\x0bI-.QH\xc9O'
                    b'.\xcdM\xcd+QP6\x04\x00\xe8\x8b\x9a\x93\x10\x00\x00\x00',
        }).run(conn)
        await r.table('response').insert({
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-000000000000',
            'body_id': b'\x00' * 32,
            'sequence': 1,
            'started_at':   datetime(2019, 1, 1, 1, 1, 0, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 1, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 1.0,
            'is_success': True,
            'job_id': str(job_id),
            'url':     'https://www.example/',
            'url_can': 'https://www.example/',
            'status_code': 200,
            'content_type': 'text/plain',
            'headers': [
                'Server', 'FakeServer 1.0',
                'X-Foo', 'Bar',
            ]
        }).run(conn)

    # Instantiate subscription
    logger.info('Set up subscription…')
    websocket = MockWebsocket()
    job_send, job_recv = trio.open_memory_channel(0)
    subscription_db = SubscriptionDb(db_pool)
    subscription = CrawlSyncSubscription(id_=1, websocket=websocket,
        job_id=str(job_id), subscription_db=subscription_db,
        compression_ok=True, job_state_recv=job_recv, sync_token=None)
    assert repr(subscription) == '<CrawlSyncSubscription id=1 job_id=aaaaaaaa>'
    nursery.start_soon(subscription.run)

    # Read from subscription
    logger.info('Read first event…')
    data = await websocket.get_message()
    message1 = ServerMessage.FromString(data).event
    assert message1.subscription_id == 1
    item1 = message1.sync_item.item
    assert item1.job_id == job_id.bytes
    assert item1.url     == 'https://www.example/'
    assert item1.url_can == 'https://www.example/'
    assert item1.started_at   == '2019-01-01T01:01:00+00:00'
    assert item1.completed_at == '2019-01-01T01:01:01+00:00'
    assert item1.cost == 1.0
    assert item1.duration == 1.0
    assert item1.status_code == 200
    assert item1.headers[0].key == 'Server'
    assert item1.headers[0].value == 'FakeServer 1.0'
    assert item1.headers[1].key == 'X-Foo'
    assert item1.headers[1].value == 'Bar'
    assert item1.is_success
    assert item1.is_compressed
    assert gzip.decompress(item1.body) == b'Test document #1'

    # The subscription should time out because there are no items to send:
    logger.info('Time out on next event…')
    with pytest.raises(trio.TooSlowError):
        with trio.fail_after(1) as cancel_scope:
            data = await websocket.get_message()

    # Now add second result and mark the crawl as completed:
    logger.info('Add second result…')
    async with db_pool.connection() as conn:
        await r.table('response_body').insert({
            'id': b'\x02' * 32,
            'is_compressed': True,
            'body': b'\x1f\x8b\x08\x00\xe7\x01J\\\x02\xff\x0bI-.QH\xc9O.\xcdM'
                    b'\xcd+QP6\x02\x00R\xda\x93\n\x10\x00\x00\x00'
        }).run(conn)
        await r.table('response').insert({
            'id': 'bbbbbbbb-bbbb-bbbb-bbbb-000000000002',
            'body_id': b'\x02' * 32,
            'sequence': 5,
            'started_at':   datetime(2019, 1, 1, 1, 1, 4, tzinfo=timezone.utc),
            'completed_at': datetime(2019, 1, 1, 1, 1, 5, tzinfo=timezone.utc),
            'duration': 1.0,
            'cost': 2.0,
            'is_success': True,
            'job_id': str(job_id),
            'url':     'https://www.example/bar',
            'url_can': 'https://www.example/bar',
            'status_code': 200,
            'content_type': 'text/plain',
            'headers': []
        }).run(conn)
    await job_send.send(JobStateEvent(job_id=str(job_id), schedule_id=None,
        run_state=RunState.COMPLETED, event_time=datetime.now(timezone.utc)))

    # Now wait to receive the second result
    logger.info('Read second event…')
    data = await websocket.get_message()
    message2 = ServerMessage.FromString(data).event
    assert message2.subscription_id == 1
    item2 = message2.sync_item.item
    assert item2.job_id == job_id.bytes
    assert item2.url     == 'https://www.example/bar'
    assert item2.url_can == 'https://www.example/bar'
    assert item2.started_at   == '2019-01-01T01:01:04+00:00'
    assert item2.completed_at == '2019-01-01T01:01:05+00:00'
    assert item2.cost == 2.0
    assert item2.duration == 1.0
    assert item2.status_code == 200
    assert item2.is_success
    assert item2.is_compressed
    assert gzip.decompress(item2.body) == b'Test document #2'

    logger.info('Read subscription close…')
    data = await websocket.get_message()
    message3 = ServerMessage.FromString(data).event
    assert message3.subscription_id == 1
    assert message3.subscription_closed.reason == SubscriptionClosed.COMPLETE
