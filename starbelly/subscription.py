from abc import ABCMeta, abstractmethod
import base64
from binascii import hexlify, unhexlify
from collections import Counter, defaultdict
from datetime import datetime
import enum
import functools
import gzip
import json
import logging
from operator import attrgetter
import math
import struct
from uuid import UUID

from protobuf.shared_pb2 import JobRunState
from protobuf.server_pb2 import ServerMessage, SubscriptionClosed
from rethinkdb import RethinkDB
import trio
import websockets.exceptions


r = RethinkDB()
logger = logging.getLogger(__name__)


class ExponentialBackoff:
    def __init__(self, start=1, max_=math.inf):
        self._backoff = start
        self._initial = True
        self._max = max_

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._initial:
            backoff = 0
            self._initial = False
        else:
            backoff = self._backoff
            await trio.sleep(backoff)
        return backoff

    def increase(self):
        if self._backoff <= self._max // 2:
            self._backoff *= 2

    def decrease(self):
        if self._backoff >= 2:
            self._backoff //= 2


class SyncTokenError(Exception):
    ''' A sync token is syntactically invalid or was used with an incompatible
    stream type. '''


class SyncTokenInt(metaclass=ABCMeta):
    '''
    A sync token that stores a 64 bit integer. The first byte contains a literal
    1 and the next 8 bytes contains the value.
    '''
    FORMAT = '=BQ'
    TOKEN_NUM = 1

    @classmethod
    def decode(cls, token):
        '''
        Unpack a token and return the value contained in it.

        :param datetime token:
        :rtype: int
        '''
        try:
            type_, val = struct.unpack(cls.FORMAT, token)
        except:
            raise SyncTokenError('Cannot decocde SyncTokenInt: %s', token)
        if type_ != cls.TOKEN_NUM:
            raise SyncTokenError('Invalid SyncTokenInt: type={}'
                .format(type_))
        return val

    @classmethod
    def encode(cls, val):
        '''
        Encode a 64 bit integer value as a token.

        :param int val:
        :rtype: bytes
        '''
        return struct.pack(cls.FORMAT, cls.TOKEN_NUM, val)


class CrawlSyncSubscription:
    '''
    A subscription stream that allows a client to sync items from a specific
    crawl job.

    This subscription includes a "sync token" that allows the subscription to
    be canceled and then resumed later. For example, if the network connection
    drops, the client may reconnect and resubscribe without missing any items
    or restarting the sync from the beginning.
    '''

    def __init__(self, id_, stream, stream_lock, db_pool, job_id,
                 compression_ok, job_state_recv, sync_token=None):
        '''
        Constructor.

        :param int id_: An identifier for this subscription.
        :param trio.abc.Stream: The stream to send subscription events to.
        :param trio.Lock stream_lock: A lock that must be acquired before
            writing to the stream.
        :param db_pool: A RethinkDB connection pool.
        :param bytes job_id: The ID of the job to send events for.
        :param bool compression_ok: If true, response bodies are gzipped.
        :param trio.ReceiveChannel job_state_recv: A channel that will receive
            updates to job status.
        :param bytes sync_token: If provided, indicates that the sync should be
            restarted from the point represented by this token.
        '''
        self._id = id_
        self._stream = stream
        self._stream_lock = stream_lock
        self._db_pool = db_pool
        self._job_id = job_id
        self._compression_ok = compression_ok
        self._job_state_recv = job_state_recv
        self._min_sequence = None
        self._max_sequence = None
        self._last_sequence = None
        self._cancel_scope = None

        if sync_token:
            min_seq = SyncTokenInt.decode(sync_token) + 1
            logging.debug('%r Setting min_sequence to %d', self, min_seq)
            self._min_sequence = min_seq

    def __repr__(self):
        ''' For debugging purposes, put the subscription ID and part of the job
        ID in a string. '''
        return '<CrawlSyncSubscription id={} job_id={}>'.format(self._id,
            hexlify(self._job_id)[:8].decode('ascii'))

    @property
    def id_(self):
        '''
        Get this subscription's ID.

        :rtype: int
        '''
        return self._id

    def cancel(self):
        ''' Cancel the subscription. '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception("Tried to cancel subscription that isn't running.")

    async def run(self):
        '''
        Run the subscription.

        :returns: This function returns when the sync is complete.
        '''
        logger.info('%r Starting', self)
        async with trio.open_nursery() as nursery:
            self._cancel_scope = nursery.cancel_scope
            await self._set_initial_job_status()
            nursery.start_soon(self._job_status_task)
            try:
                await self._run_sync()
            except (trio.BrokenResourceError, trio.ClosedResourceError):
                logger.info('%r Aborted', self)
            nursery.cancel_scope.cancel()
        try:
            await self._send_complete()
            logger.info('%r Finished', self)
        except (trio.BrokenResourceError, trio.ClosedResourceError):
            # If we can't send the completion message, then bail out.
            pass

    def _get_query(self):
        '''
        Return the query used for getting items to sync.

        This query is a little funky. I want to join `response` and
        `response_body` while preserving the `sequence` order, but
        RethinkDB's `eq_join()` method doesn't preserve order (see GitHub issue:
        https://github.com/rethinkdb/rethinkdb/issues/6319). Somebody on
        RethinkDB Slack showed me that you can use merge and subquery to
        simulate a left outer join that preserves order and in a quick test on
        200k documents, it works well and runs fast.

        :returns: a RethinkDB query object.
        '''
        def get_body(item):
            return {
                'join': r.branch(
                    item.has_fields('body_id'),
                    r.table('response_body').get(item['body_id']),
                    None
                )
            }

        max_sequence = self._max_sequence or r.maxval
        query = (
            r.table('response')
             .order_by(index='sequence')
             .between(self._min_sequence, max_sequence, right_bound='closed')
             .merge(get_body)
        )

        return query

    async def _job_status_task(self):
        '''
        Handle job status updates.

        :returns: This function runs until cancelled. It will also exit if the
            job status channel is closed, but that should never happen.
        '''
        async for job_state in self._job_state_recv:
            if job_state.job_id == self._job_id:
                self._max_sequence = job_state.max_sequence

    async def _run_sync(self):
        '''
        Run the main sync loop.

        :returns: This function runs until the sync is complete.
        '''
        backoff = ExponentialBackoff(max_=64)
        async for _ in backoff:
            async with self._db_pool.connection() as conn:
                item_count = 0
                cursor = await self._get_query().run(conn)
                async with cursor:
                    async for item in cursor:
                        item_count += 1
                        await self._send_item(item)
                        self._min_sequence = item['sequence'] + 1

            if self._max_sequence and self._min_sequence > self._max_sequence:
                break

            if item_count == 0:
                backoff.increase()
            else:
                backoff.decrease()

    async def _send_complete(self):
        ''' Send a subscription end event. '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        message.event.subscription_closed.reason = SubscriptionClosed.COMPLETE
        async with self._stream_lock:
            with trio.open_cancel_scope(shield=True) as cancel_scope:
                await self._stream.send_all(message.SerializeToString())

    async def _send_item(self, item_doc):
        ''' Send an item (download response) to the client. '''
        logger.debug('%r Sending item seq=%d url=%s', self,
            item_doc['sequence'], item_doc['url'])
        message = ServerMessage()
        message.event.subscription_id = self._id

        item = message.event.sync_item.item
        item.completed_at = item_doc['completed_at'].isoformat()
        item.cost = item_doc['cost']
        item.duration = item_doc['duration']
        item.is_success = item_doc['is_success']
        item.job_id = item_doc['job_id']
        item.started_at = item_doc['started_at'].isoformat()
        item.url = item_doc['url']
        item.url_can = item_doc['url_can']

        if 'exception' in item_doc:
            item.exception = item_doc['exception']
        else:
            if item_doc['join']['is_compressed'] and not self._compression_ok:
                body = gzip.decompress(item_doc['join']['body'])
                is_compressed = False
            else:
                body = item_doc['join']['body']
                is_compressed = item_doc['join']['is_compressed']
            item.body = body
            item.is_compressed = is_compressed
            item.content_type = item_doc['content_type']
            header_iter = iter(item_doc.get('headers', []))
            for key in header_iter:
                value = next(header_iter)
                header = item.headers.add()
                header.key = key
                header.value = value
            item.status_code = item_doc['status_code']

        message.event.sync_item.token = SyncTokenInt.encode(
            item_doc['sequence'])
        async with self._stream_lock:
            with trio.open_cancel_scope(shield=True) as cancel_scope:
                await self._stream.send_all(message.SerializeToString())

    async def _set_initial_job_status(self):
        ''' Query database for initial job status. '''
        query = (
            r.table('job')
             .get(self._job_id)
             .pluck('run_state', 'min_sequence', 'max_sequence')
        )
        async with self._db_pool.connection() as conn:
            result = await query.run(conn)
            logging.debug('%r Initial job state: %r', self, result)
            if not self._min_sequence:
                self._min_sequence = result['min_sequence']
            self._max_sequence = result['max_sequence']


class JobStatusSubscription:
    '''
    A subscription stream that emits updates about the status of all running
    jobs.

    It only sends events when something about a job has changed.
    '''

    def __init__(self, id_, job_states, stream, stream_lock, min_interval):
        '''
        Constructor.

        :param int id_: Subscription ID.
        :param JobStates job_states: A read-only view of job states.
        :param trio.abc.Stream stream: A stream to send events to.
        :param trio.Lock stream_lock: A lock that must be acquired before
            sending to the stream.
        :param float min_interval: The amount of time to wait in between
            sending events.
        '''
        self._id = id_
        self._job_states = job_states
        self._stream = stream
        self._stream_lock = stream_lock
        self._min_interval = min_interval
        self._cancel_scope = None
        self._last_send = dict()

    def __repr__(self):
        ''' For debugging purposes, put the subscription ID in a string. '''
        return '<JobStatusSubscription id={}>'.format(self._id)

    def cancel(self):
        ''' Cancel the subscription. '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception("Tried to cancel subscription that isn't running.")

    async def run(self):
        '''
        Start the subscription stream.

        :returns: This function runs until ``cancel()`` is called.
        '''
        logger.info('%r Starting', self)
        async with trio.open_nursery() as nursery:
            self._cancel_scope = nursery.cancel_scope

            while True:
                event = self._make_event()
                await self._send(event)
                await trio.sleep(self._min_interval)
        logger.info('%r Cancelled', self)

    def _make_event(self):
        '''
        Make an event to send to the client and update internal state.

        :rtype: protobuf.server_pb2.ServerMessage
        '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        current_send = dict()

        for job_id, job_state in self._job_states:
            current_send[job_id] = job_state
            if job_state == self._last_send.get(job_id):
                # No change since last send. Ignore this job.
                continue
            pb_job = message.event.job_list.jobs.add()
            pb_job.job_id = job_id
            pb_job.name = job_state['name']
            pb_job.item_count = job_state['item_count']
            pb_job.http_success_count = job_state['http_success_count']
            pb_job.http_error_count = job_state['http_error_count']
            pb_job.exception_count = job_state['exception_count']
            for seed in job_state['seeds']:
                pb_job.seeds.append(seed)
            for tag in job_state['tags']:
                pb_job.tag_list.tags.append(tag)
            pb_job.started_at = job_state['started_at'].isoformat()
            if job_state['completed_at']:
                pb_job.completed_at = job_state['completed_at'].isoformat()
            pb_job.run_state = JobRunState.Value(job_state['run_state'].upper())
            for status_code, count in job_state['http_status_counts'].items():
                pb_job.http_status_counts[int(status_code)] = count

        self._last_send = current_send
        return message

    async def _send(self, event):
        '''
        Send event. This method handles a few difficulties with sending on a
        shared stream, including acquiring a lock for the stream and shielding
        the send from cancellation.

        :param protobuf.server_pb2.ServerMessage event:
        '''
        async with self._stream_lock:
            with trio.open_cancel_scope(shield=True):
                await self._stream.send_all(event.SerializeToString())


class ResourceMonitorSubscription:
    ''' Keep track of usage for various resources. '''
    def __init__(self, id_, stream, stream_lock, resource_monitor, history=0):
        ''' Constructor.

        :param int id_: Subscription ID.
        :param trio.abc.Stream stream: A stream to send events to.
        :param trio.Lock stream_lock: A lock that must be acquired before
            sending to the stream.
        :type resource_monitor: starbelly.resource_monitor.ResourceMonitor
        :param int history: The number of historical measurements to send before
            streaming real-time measurements.
        '''
        self._id = id_
        self._stream = stream
        self._stream_lock = stream_lock
        self._resource_monitor = resource_monitor
        self._history = history
        self._recv_channel = None
        self._cancel_scope = None

    def __repr__(self):
        ''' For debugging purposes, put the subscription ID in a string. '''
        return '<ResourceMonitorSubscription id={}>'.format(self._id)

    def cancel(self):
        ''' Cancel the subscription. '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception('Tried to cancel subscription that is not running.')

    async def run(self):
        '''
        Start the subscription stream.

        :returns: This method runs until cancel is called.
        '''
        logger.info('%r Starting', self)
        async with trio.open_nursery() as nursery:
            self._cancel_scope = nursery.cancel_scope
            # Open a channel to the resource monitor now. We choose a channel
            # size that is big enough to hold up to 10 seconds worth of data,
            # since it may take a few seconds to send all of the requested
            # historical data.
            self._recv_channel = self._resource_monitor.get_channel(10)
            for measurement in self._resource_monitor.history(self._history):
                event = self._make_event(measurement)
                await self._send(event)

            async for measurement in self._recv_channel:
                event = self._make_event(measurement)
                await self._send(event)
        logger.info('%r Cancelled', self)

    def _make_event(self, measurement):
        '''
        Make an event to send to the client.

        :rtype: protobuf.server_pb2.ServerMessage
        '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        frame = message.event.resource_frame
        frame.timestamp = measurement['timestamp'].isoformat()

        for cpu_percent in measurement['cpus']:
            cpu = frame.cpus.add()
            cpu.usage = cpu_percent

        frame.memory.used = measurement['memory_used']
        frame.memory.total = measurement['memory_total']

        for disk_measure in measurement['disks']:
            disk = frame.disks.add()
            disk.mount = disk_measure['mount']
            disk.used = disk_measure['used']
            disk.total = disk_measure['total']

        for network_measure in measurement['networks']:
            net = frame.networks.add()
            net.name = network_measure['name']
            net.sent = network_measure['sent']
            net.received = network_measure['received']

        for crawl_measure in measurement['crawls']:
            crawl = frame.crawls.add()
            crawl.job_id = crawl_measure['job_id']
            crawl.frontier = crawl_measure['frontier']
            crawl.pending = crawl_measure['pending']
            crawl.extraction = crawl_measure['extraction']
            crawl.downloader = crawl_measure['downloader']

        frame.rate_limiter.count = measurement['rate_limiter']
        return message

    async def _send(self, event):
        '''
        Send event. This method handles a few difficulties with sending on a
        shared stream, including acquiring a lock for the stream and shielding
        the send from cancellation.

        :param protobuf.server_pb2.ServerMessage event:
        '''
        async with self._stream_lock:
            with trio.open_cancel_scope(shield=True):
                await self._stream.send_all(event.SerializeToString())


class TaskMonitorSubscription:
    '''
    Sends data showing whats kinds of tasks and how many of each are running.
    '''
    def __init__(self, id_, stream, stream_lock, period, root_task):
        '''
        Constructor.

        :param int id_: The subscription ID.
        :param trio.abc.Stream stream: A stream to send events to.
        :param trio.Lock stream_lock: A lock that must be acquired before
            sending to the stream.
        :param float period: The amount of time to wait in between events.
        :param trio.hazmat.Task root_task: The root task to build a task tree
            from.
        '''
        self._id = id_
        self._stream = stream
        self._stream_lock = stream_lock
        self._period = period
        self._root_task = root_task

    def __repr__(self):
        ''' For debugging purposes, put the subscription ID in a string. '''
        return '<TaskMonitorSubscription id={}>'.format(self._id)

    def cancel(self):
        ''' Cancel the subscription. '''
        if self._cancel_scope:
            self._cancel_scope.cancel()
        else:
            raise Exception('Tried to cancel subscription that is not running.')

    async def run(self):
        '''
        Start the subscription stream.

        :returns: This function runs until ``cancel()`` is called.
        '''
        with trio.open_cancel_scope() as cancel_scope:
            self._cancel_scope = cancel_scope
            while True:
                event = self._make_event()
                await self._send(event)
                await trio.sleep(self._period)

    def _make_event(self):
        ''' Make an event containing task monitor data. '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        root = message.event.task_tree
        root.name = '<Root>'
        nodes = [(self._root_task, root)]

        while nodes:
            trio_task, pb_task = nodes.pop(0)
            for nursery in trio_task.child_nurseries:
                children = sorted(nursery.child_tasks, key=attrgetter('name'))
                for trio_child_task in children:
                    pb_child_task = pb_task.subtasks.add()
                    pb_child_task.name = trio_child_task.name
                    nodes.append((trio_child_task, pb_child_task))

        return message

    async def _send(self, event):
        '''
        Send event. This method handles a few difficulties with sending on a
        shared stream, including acquiring a lock for the stream and shielding
        the send from cancellation.

        :param protobuf.server_pb2.ServerMessage event:
        '''
        async with self._stream_lock:
            with trio.open_cancel_scope(shield=True):
                await self._stream.send_all(event.SerializeToString())

