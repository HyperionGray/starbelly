import asyncio
import base64
from binascii import hexlify, unhexlify
from collections import defaultdict
import enum
import json
import logging
import struct
from uuid import UUID

from protobuf.shared_pb2 import JobRunState
from protobuf.server_pb2 import ServerMessage
import rethinkdb as r

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


class InvalidSyncToken(Exception):
    '''
    A sync token is syntactically invalid or was used with an incompatible
    stream type.
    '''


class CrawlSyncSubscription:
    '''
    A subscription stream that allows a client to sync items from a specific
    crawl.

    This subscription includes a "sync token" that allows the subscription to
    be canceled and then resumed later. For example, if the network connection
    drops, the client may reconnect and resubscribe without missing any items
    or restarting the sync from the beginning.
    '''

    _id_sequence = Sequence()
    TOKEN_HEADER = 'BBB'
    TOKEN_BODY = '!L'

    def __init__(self, tracker, db_pool, socket, job_id, sync_token=None):
        ''' Constructor. '''
        self.id = self._id_sequence.next()
        self._db_pool = db_pool
        self._socket = socket
        self._job_id = job_id
        self._tracker = tracker
        self._crawl_run_state = None
        self._crawl_item_count = None

        # Decode sync token if present.
        if sync_token is None:
            self._sequence = 1
        else:
            self._sequence = self._decode_sync_token(sync_token)

    async def run(self):
        ''' Run the subscription. '''

        backoff = 1 # Exponential backoff, e.g. 1, 2, 4, 8, 16, 32
        out_of_order_count = 0
        await self._set_initial_job_status()
        self._tracker.job_status_changed.listen(self._handle_job_status)
        logger.info('sync started')

        while True:
            async with self._db_pool.connection() as conn:
                cursor = await self._get_query().run(conn)
                async for item in AsyncCursorIterator(cursor):
                    # Make sure this item matches the expected sequence number.
                    if item['insert_sequence'] != self._sequence:
                        out_of_order_count += 1
                        break
                    else:
                        self._sequence += 1
                        out_of_order_count = 0
                        if backoff > 1:
                            backoff /= 2
                        if item['is_success']:
                            await self._send_item(item)

            # If we get too many out-of-order results, it indicates something is
            # wrong with our crawl data. Log an error and move onto the next
            # item.
            if out_of_order_count >= 5:
                msg = 'Crawl sync received too many out-of-order results!' \
                      ' (job={} waiting for sequence={})' \
                      .format(self._job_id, self._sequence)
                logger.error(msg)
                self._sequence += 1
                out_of_order_count = 0

            if self._sync_is_complete():
                #TODO need a way to communicate end of subscription to client
                break

            # Wait for more results to come in.
            await asyncio.sleep(backoff)

            if backoff < 32:
                backoff *= 2

        self._tracker.job_status_changed.cancel(self._handle_job_status)
        logger.info('sync finished')


    def _decode_sync_token(self, token):
        ''' Unpack a token and return a sequence number. '''

        type_, version, length = struct.unpack(self.TOKEN_HEADER, token[:3])

        if type_ != 1 or version != 1 or length != 4:
            raise InvalidSyncToken('Invalid token: type={} version={} length={}'
                .format(type_, version, length))

        sequence = struct.unpack(self.TOKEN_BODY, token[-length:])[0]
        return sequence

    def _get_query(self):
        ''' Return the query used for getting items to sync. '''
        query = (
            r.table('crawl_item')
             .between((self._job_id, self._sequence),
                      (self._job_id, r.maxval),
                      index='sync_index')
             .order_by(index='sync_index')
        )
        return query

    def _get_sync_token(self):
        '''
        A "sync token" is an opaque string that a client stores after it
        processes an event. If the subscription needs to be resumed later, the
        client may present the stored sync token and continue where it
        previously left off.

        A sync token has a header containing 3 bytes: subscription type number
        (1 for CrawlItemSubscription -- others may be added in the future),
        version number (the current version is 1), and payload length in bytes.

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

    async def _send_item(self, item):
        ''' Send a crawl item to the client. '''
        message = ServerMessage()
        message.event.subscription_id = self.id
        crawl_item = message.event.crawl_item
        crawl_item.body = item['body']
        crawl_item.completed_at = item['completed_at'].isoformat()
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
        return self._crawl_run_state == 'completed' and \
               self._sequence > self._crawl_item_count


class JobStatusSubscription:
    '''
    A subscription stream that emits updates about the status of all running
    crawls.

    The first emitted event will contain the complete status for each running
    crawl; subsequent events will only include fields that have changed since
    the previous event.
    '''

    _id_sequence = Sequence()

    def __init__(self, tracker, socket, min_interval):
        ''' Constructor. '''
        self.id = self._id_sequence.next()
        self._socket = socket
        self._min_interval = min_interval
        self._status_changed = asyncio.Event()
        self._updates = tracker.get_all_job_status()
        tracker.job_status_changed.listen(self._handle_status_changed)

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
