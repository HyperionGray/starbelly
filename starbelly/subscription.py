import asyncio
import base64
from binascii import hexlify, unhexlify
from collections import defaultdict
import enum
import json
import logging
import struct
from uuid import UUID, uuid1

import rethinkdb as r


logger = logging.getLogger(__name__)


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

    TOKEN_HEADER = 'BBB'
    TOKEN_BODY = '!L'

    def __init__(self, tracker, db_pool, socket, crawl_id, sync_token=None):
        ''' Constructor. '''
        self.id = uuid1().hex
        self._db_pool = db_pool
        self._socket = socket
        self._crawl_id = crawl_id
        self._tracker = tracker
        self._crawl_status = None
        self._crawl_item_count = None

        # Decode sync token if present.
        if sync_token is None:
            self._sequence = 1
        else:
            self._sequence = self._decode_sync_token(sync_token)

    async def run(self):
        ''' Run the subscription. '''

        backoff = 1 # Exponential backoff, e.g. 1, 2, 4, 8, ..., 32
        out_of_order_count = 0
        await self._set_initial_job_status()
        self._tracker.job_status_changed.listen(self._handle_job_status)
        logger.info('sync started')

        while True:
            async with self._db_pool.connection() as conn:
                cursor = await self._get_query().run(conn)
                while await cursor.fetch_next():
                    item = await cursor.next()

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
                cursor.close()

            # If we get too many out-of-order results, it indicates something is
            # wrong with our crawl data. Log an error and move onto the next
            # item.
            if out_of_order_count >= 5:
                msg = 'Crawl sync received too many out-of-order results!' \
                      ' (crawl={} waiting for sequence={})' \
                      .format(self._crawl_id, self._sequence)
                logger.error(msg)
                self._sequence += 1
                out_of_order_count = 0

            if self._sync_is_complete():
                #TODO need a way to communicate end of subscription to client
                break

            # Wait for more results to come in.
            logger.info('backoff={}'.format(backoff))
            await asyncio.sleep(backoff)

            if backoff < 32:
                backoff *= 2

        self._tracker.job_status_changed.cancel(self._handle_job_status)
        logger.info('sync finished')


    def _decode_sync_token(self, token):
        ''' Unpack a token and return a sequence number. '''

        token = unhexlify(token.encode('ascii'))
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
             .between((self._crawl_id, self._sequence),
                      (self._crawl_id, r.maxval),
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
        return hexlify(token_header + token_body).decode('ascii')

    def _handle_job_status(self, job_id, job):
        ''' Handle job status updates. '''
        if job_id == self._crawl_id:
            self._crawl_status = job['status']
            self._crawl_item_count = job['item_count']

    async def _send_item(self, item):
        ''' Send a crawl item to the client. '''
        message = {
            'type': 'event',
            'subscription_id': self.id,
            'data': {
                'body': base64.b64encode(item['body']).decode('ascii'),
                'completed_at': item['completed_at'].isoformat(),
                'crawl_id': item['crawl_id'],
                'depth': item['depth'],
                'duration': item['duration'],
                'headers': item['headers'],
                'started_at': item['started_at'].isoformat(),
                'status_code': item['status_code'],
                'sync_token': self._get_sync_token(),
                'url': item['url'],
            },
        }
        await self._socket.send(json.dumps(message))

    async def _set_initial_job_status(self):
        ''' Query database for initial job status. '''

        query = (
            r.table('crawl_job')
             .get(self._crawl_id)
             .pluck('status', 'item_count')
        )

        async with self._db_pool.connection() as conn:
            result = await query.run(conn)
            self._crawl_status = result['status']
            self._crawl_item_count = result['item_count']

    def _sync_is_complete(self):
        ''' Return true if the sync is finished. '''
        return self._crawl_status == 'completed' and \
               self._sequence > self._crawl_item_count


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
        self.id = uuid1().hex
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
        event = {
            'type': 'event',
            'subscription_id': self.id,
            'data': self._updates,
        }
        self._updates = {}
        self._status_changed.clear()
        await self._socket.send(json.dumps(event))

    def _handle_status_changed(self, job_id, job):
        ''' Handle an update from the job tracker. '''
        self._updates[job_id] = job
        self._status_changed.set()
