import asyncio
import base64
from binascii import hexlify, unhexlify
from collections import defaultdict
import enum
import functools
import gzip
import json
import logging
import struct
from uuid import UUID

from protobuf.shared_pb2 import JobRunState
from protobuf.server_pb2 import ServerMessage, SubscriptionClosed
import rethinkdb as r

from . import cancel_futures, daemon_task
from .db import AsyncCursorIterator


logger = logging.getLogger(__name__)


class Sequence:
    ''' An incrementing sequence of integers. '''

    def __init__(self):
        ''' Constructor. '''
        self._sequence = -1

    def next(self):
        ''' Get the next number from the sequence. '''
        self._sequence += 1
        return self._sequence


_subscription_id_sequence = Sequence()


class InvalidSyncToken(Exception):
    '''
    A sync token is syntactically invalid or was used with an incompatible
    stream type.
    '''


class SubscriptionManager():
    ''' Manages all open subscriptions. '''

    def __init__(self, db_pool):
        ''' Constructor. '''
        self._closed = False
        self._closing = set()
        self._db_pool = db_pool
        self._subscriptions = defaultdict(dict)

    def add(self, subscription):
        '''
        Add a subscription and run it.
        '''
        socket = subscription.get_socket()

        if self._closed:
            raise Exception('The subscription manager is closed.')
        elif socket in self._closing:
            raise Exception(
                'Cannot add subscription: the socket is being closed.')

        def task_ended(f):
            daemon_task(self.unsubscribe(socket, subscription.id))

        task = daemon_task(subscription.run())
        task.add_done_callback(task_ended)
        self._subscriptions[socket][subscription.id] = task

    async def close_all(self):
        '''
        Close all subscriptions.

        No new subcriptions may be added after this manager is closed.
        '''

        logger.info('Closing subscription manager...')
        self._closed = True
        sub_tasks = list()
        for socket, socket_subs in self._subscriptions.items():
            for subscription_id, subscription in socket_subs.items():
                sub_tasks.append(subscription)
        await cancel_futures(*sub_tasks)
        logger.info('Subscription manager is closed.')

    async def close_for_socket(self, socket):
        ''' Close all subscriptions opened by the specified socket. '''
        subscriptions = self._subscriptions.get(socket, {}).values()

        if len(subscriptions) > 0:
            logger.info('Closing subscriptions for: %s:%s',
                socket.remote_address[0],
                socket.remote_address[1],
            )
            self._closing.add(socket)
            await cancel_futures(*subscriptions)
            del self._subscriptions[socket]
            self._closing.remove(socket)

    async def unsubscribe(self, socket, subscription_id):
        ''' Close a subscription. '''
        try:
            task = self._subscriptions[socket][subscription_id]
            await cancel_futures(task)
            del self._subscriptions[socket][subscription_id]
        except KeyError:
            logger.error('Invalid subscription id=%d on socket %s:%s',
                subscription_id,
                socket.remote_address[0],
                socket.remote_address[1],
            )


class CrawlSyncSubscription:
    '''
    A subscription stream that allows a client to sync items from a specific
    crawl.

    This subscription includes a "sync token" that allows the subscription to
    be canceled and then resumed later. For example, if the network connection
    drops, the client may reconnect and resubscribe without missing any items
    or restarting the sync from the beginning.
    '''

    TOKEN_HEADER = 'BBB'
    TOKEN_BODY = '!L'

    def __init__(self, tracker, db_pool, socket, job_id, compression_ok,
                 sync_token=None):
        ''' Constructor. '''
        self.id = _subscription_id_sequence.next()
        self._compression_ok = compression_ok
        self._db_pool = db_pool
        self._socket = socket
        self._job_id = job_id
        self._tracker = tracker
        self._crawl_run_state = None
        self._crawl_item_count = None

        # Decode sync token if present.
        if sync_token is None:
            self._sequence = 0
        else:
            self._sequence = self._decode_sync_token(sync_token)

    def get_socket(self):
        ''' Return the associated socket. '''
        return self._socket

    async def run(self):
        ''' Run the subscription. '''

        await self._set_initial_job_status()
        self._tracker.job_status_changed.listen(self._handle_job_status)
        logger.info('Syncing items from job_id=%s', self._job_id[:8])

        while True:
            async with self._db_pool.connection() as conn:
                cursor = await self._get_query().run(conn)

                async for item in AsyncCursorIterator(cursor):
                    # Make sure this item matches the expected sequence number.
                    if item['insert_sequence'] != self._sequence:
                        logger.error(
                            'Crawl sync item is out-of-order: job=%s expected '
                            '%d but found %d.', self._job_id[:8],
                            self._sequence, item['insert_sequence']
                        )
                        self._sequence = item['insert_sequence']

                    self._sequence += 1
                    if item['is_success']:
                        await self._send_item(item)

            if self._sync_is_complete():
                logger.info('Item sync complete for job_id=%s',
                    self._job_id[:8])
                await self._send_complete()
                break

            # Wait for more results to come in.
            await asyncio.sleep(1)

        self._tracker.job_status_changed.cancel(self._handle_job_status)
        logger.info('Stop syncing items from job_id=%s', self._job_id[:8])

    def _decode_sync_token(self, token):
        ''' Unpack a token and return a sequence number. '''

        version, type_, length = struct.unpack(self.TOKEN_HEADER, token[:3])

        if version != 1 or type_ != 1 or length != 4:
            raise InvalidSyncToken('Invalid token: version={} type={} length={}'
                .format(version, type_, length))

        sequence = struct.unpack(self.TOKEN_BODY, token[-length:])[0]
        return sequence

    def _get_query(self):
        '''
        Return the query used for getting items to sync.

        This query is a little funky. I want to join `crawl_item` and
        `crawl_item_body` while preserving the `insert_sequence` order, but
        RethinkDB's `eq_join()` method doesn't preserve order (see GitHub issue:
        https://github.com/rethinkdb/rethinkdb/issues/6319). Somebody on
        RethinkDB Slack showed me that you can use merge and subquery to
        simulate a left outer join that preserves order and in a quick test on
        200k documents, it works well and runs fast.
        '''

        def get_body(item):
            return {'join': r.table('crawl_item_body').get(item['body_id'])}

        query = (
            r.table('crawl_item')
             .between((self._job_id, self._sequence),
                      (self._job_id, r.maxval),
                      index='sync_index')
             .order_by(index='sync_index')
             .merge(get_body)
        )

        return query

    def _get_sync_token(self):
        '''
        A "sync token" is an opaque string that a client stores after it
        processes an event. If the subscription needs to be resumed later, the
        client may present the stored sync token and continue where it
        previously left off.

        A sync token has a header containing 3 bytes: version number (the
        current version is 1), subscription type number (1 for
        CrawlItemSubscription -- others may be added in the future), and payload
        length in bytes.

        The body comes after the header and is a sequence of raw bytes. For this
        subscription, the body is a 32-bit unsigned integer sequence number.
        '''

        token_body = struct.pack(self.TOKEN_BODY, self._sequence)
        token_header = struct.pack(self.TOKEN_HEADER, 1, 1, len(token_body))
        return token_header + token_body

    def _handle_job_status(self, job_id, job):
        ''' Handle job status updates. '''
        if job_id == self._job_id:
            self._crawl_run_state = job['run_state']
            self._crawl_item_count = job['item_count']

    async def _send_complete(self):
        ''' Send a subscription end event. '''
        message = ServerMessage()
        message.event.subscription_id = self.id
        message.event.subscription_closed.reason = SubscriptionClosed.END
        await self._socket.send(message.SerializeToString())

    async def _send_item(self, item):
        ''' Send a crawl item to the client. '''
        message = ServerMessage()
        message.event.subscription_id = self.id

        if item['join']['is_compressed'] and not self._compression_ok:
            body = gzip.decompress(item['join']['body'])
            is_body_compressed = False
        else:
            body = item['join']['body']
            is_body_compressed = item['join']['is_compressed']

        crawl_item = message.event.crawl_item
        crawl_item.body = body
        crawl_item.is_body_compressed = is_body_compressed
        crawl_item.completed_at = item['completed_at'].isoformat()
        crawl_item.content_type = item['content_type']
        crawl_item.cost = item['cost']
        crawl_item.duration = item['duration']
        for key, value in item['headers'].items():
            if value is None:
                value = ''
            crawl_item.headers[key] = value
        crawl_item.job_id = UUID(item['job_id']).bytes
        crawl_item.started_at = item['started_at'].isoformat()
        crawl_item.status_code = item['status_code']
        crawl_item.sync_token = self._get_sync_token()
        crawl_item.url = item['url']
        crawl_item.url_can = item['url_can']
        crawl_item.url_hash = item['url_hash']
        await self._socket.send(message.SerializeToString())

    async def _set_initial_job_status(self):
        ''' Query database for initial job status. '''

        query = (
            r.table('crawl_job')
             .get(self._job_id)
             .pluck('run_state', 'item_count')
        )

        async with self._db_pool.connection() as conn:
            result = await query.run(conn)
            self._crawl_run_state = result['run_state']
            self._crawl_item_count = result['item_count']

    def _sync_is_complete(self):
        ''' Return true if the sync is finished. '''
        return self._sequence >= self._crawl_item_count - 1 and \
               self._crawl_run_state in ('completed', 'cancelled')


class JobStatusSubscription:
    '''
    A subscription stream that emits updates about the status of all running
    crawls.

    The first emitted event will contain the complete status for each running
    crawl; subsequent events will only include fields that have changed since
    the previous event.
    '''

    def __init__(self, tracker, socket, min_interval):
        ''' Constructor. '''
        self.id = _subscription_id_sequence.next()
        self._socket = socket
        self._min_interval = min_interval
        self._status_changed = asyncio.Event()
        self._updates = tracker.get_all_job_status()
        tracker.job_status_changed.listen(self._handle_status_changed)

    def get_socket(self):
        ''' Return the associated socket. '''
        return self._socket

    async def run(self):
        ''' Start the subscription stream. '''

        # If we have initial job statuses, go ahead and send them.
        if len(self._updates) > 0:
            await self._send_event()

        while True:
            await asyncio.gather(
                asyncio.sleep(self._min_interval),
                self._status_changed.wait()
            )
            await self._send_event()

    async def _send_event(self):
        ''' Send an event to send to the client and update internal state. '''
        message = ServerMessage()
        message.event.subscription_id = self.id

        def cond_set(src, tgt, attr):
            if attr in src:
                setattr(tgt, attr, src[attr])

        for job_id, job_data in self._updates.items():
            job_status = message.event.job_statuses.statuses.add()
            job_status.job_id = UUID(job_id).bytes
            cond_set(job_data, job_status, 'name')
            cond_set(job_data, job_status, 'item_count')
            cond_set(job_data, job_status, 'http_success_count')
            cond_set(job_data, job_status, 'http_error_count')
            cond_set(job_data, job_status, 'exception_count')
            if 'run_state' in job_data:
                run_state = job_data['run_state'].upper()
                job_status.run_state = JobRunState.Value(run_state)
            http_status_counts = job_data.get('http_status_counts', {})
            for status_code, count in http_status_counts.items():
                job_status.http_status_counts[int(status_code)] = count
        self._updates = {}
        self._status_changed.clear()
        await self._socket.send(message.SerializeToString())

    def _handle_status_changed(self, job_id, job):
        ''' Handle an update from the job tracker. '''
        self._updates[job_id] = job
        self._status_changed.set()
