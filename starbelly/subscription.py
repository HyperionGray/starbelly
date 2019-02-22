from abc import ABCMeta, abstractmethod
import base64
from binascii import hexlify, unhexlify
from collections import Counter, defaultdict
from datetime import datetime
import enum
import functools
import gzip
import itertools
import json
import logging
from operator import attrgetter
import math
import struct
from uuid import UUID

from rethinkdb import RethinkDB
import trio
import websockets.exceptions

from .backoff import ExponentialBackoff
from .job import FINISHED_STATES, RunState
from .starbelly_pb2 import JobRunState, ServerMessage, SubscriptionClosed


r = RethinkDB()
logger = logging.getLogger(__name__)


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


class SubscriptionManager:
    '''
    Manages a group of subscriptions, e.g. all of the subscriptions on one
    connection.
    '''
    def __init__(self, subscription_db, nursery, websocket):
        '''
        Constructor

        :param subscription_db: A database layer.
        '''
        self._subscription_db = subscription_db
        self._subscription_id = itertools.count()
        self._subscriptions = dict()
        self._nursery = nursery
        self._websocket = websocket

    def cancel_subscription(self, subscription_id):
        '''
        Cancel a subscription.
        '''
        self._subscriptions.pop(subscription_id).cancel()

    def subscribe_crawl_sync(self, job_id, compression_ok, sync_token):
        '''
        Subscribe to crawl job sync.

        :param str job_id:
        :param bool compression_ok:
        :param sync_token:
        :type sync_token: bytes or None
        :returns: A subscription ID.
        :rtype: int
        '''
        sub_id = next(self._subscription_id)
        sub = CrawlSyncSubscription(sub_id, job_id, self._subscription_db,
            self._websocket, compression_ok, job_state_recv, sync_token)
        self._subscriptions[sub_id] = sub
        self._nursery.start_soon(sub)
        return sub_id

    def subscribe_job_status(self, stats_stracker, min_interval):
        '''
        Subscribe to job status.

        :param starbelly.job.StatsTracker stats_tracker:
        :param float min_interval:
        :returns: A subscription ID.
        :rtype: int
        '''
        sub_id = next(self._subscription_id)
        sub = JobStatusSubscription(sub_id, self._websocket, stats_tracker,
            min_interval)
        self._subscriptions[sub_id] = sub
        self._nursery.start_soon(sub)
        return sub_id

    def subscribe_resource_monitor(self, resource_monitor, history):
        '''
        Subscribe to resource monitor.

        :param starbelly.resource_monitor.ResourceMonitor resource_monitor:
        :param int history:
        :returns: A subscription ID.
        :rtype: int
        '''
        sub_id = next(self._subscription_id)
        sub = ResourceMonitorSubscription(sub_id, self._websocket,
            resource_monitor, history)
        self._subscriptions[sub_id] = sub
        self._nursery.start_soon(sub)
        return sub_id

    def subscribe_task_monitor(self, period, root_task):
        '''
        Subscribe to crawl job sync.

        :param float period:
        :param trio.hazmat.Task root_task:
        :returns: A subscription ID.
        :rtype: int
        '''
        sub_id = next(self._subscription_id)
        sub = TaskMonitorSubscription(sub_id, self._websocket, period,
            root_task)
        self._subscriptions[sub_id] = sub
        self._nursery.start_soon(sub)
        return sub_id


class CrawlSyncSubscription:
    '''
    A subscription stream that allows a client to sync items from a specific
    crawl job.

    This subscription includes a "sync token" that allows the subscription to
    be canceled and then resumed later. For example, if the network connection
    drops, the client may reconnect and resubscribe without missing any items
    or restarting the sync from the beginning.
    '''

    def __init__(self, id_, websocket, job_id, subscription_db, compression_ok,
            job_state_recv, sync_token=None):
        '''
        Constructor.

        :param int id_: An identifier for this subscription.
        :param trio_websocket.WebSocketConnection websocket: A WebSocket to send
            events to.
        :param db_pool: A RethinkDB connection pool.
        :param str job_id: The ID of the job to send events for.
        :param bool compression_ok: If true, response bodies are gzipped.
        :param trio.ReceiveChannel job_state_recv: A channel that will receive
            updates to job status.
        :param bytes sync_token: If provided, indicates that the sync should be
            restarted from the point represented by this token.
        '''
        self._id = id_
        self._db = subscription_db
        self._websocket = websocket
        self._job_id = job_id
        self._compression_ok = compression_ok
        self._job_state_recv = job_state_recv
        self._current_sequence = 0
        self._cancel_scope = None
        self._job_completed = None

        if sync_token:
            self._current_sequence = SyncTokenInt.decode(sync_token)
            logging.debug('%r Setting current sequence to %d', self,
                self._current_sequence)

    def __repr__(self):
        ''' For debugging purposes, put the subscription ID and part of the job
        ID in a string. '''
        return '<CrawlSyncSubscription id={} job_id={}>'.format(self._id,
            self._job_id[:8])

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

    async def _job_status_task(self):
        '''
        Handle job status updates.

        :returns: This function runs until cancelled. It will also exit if the
            job status channel is closed, but that should never happen.
        '''
        async for job_state in self._job_state_recv:
            if job_state.job_id == self._job_id:
                if job_state.run_state in FINISHED_STATES:
                    logger.debug('%r Job status: %s', self, job_state.run_state)
                    self._job_completed = True

    async def _run_sync(self):
        '''
        Run the main sync loop.

        :returns: This function runs until the sync is complete.
        '''
        backoff = ExponentialBackoff(max_=64)
        async for _ in backoff:
            item_count = 0
            async for item in self._db.get_job_sync_items(self._job_id,
                    self._current_sequence):
                item_count += 1
                await self._send_item(item)
                self._current_sequence = item['sequence'] + 1

            if item_count == 0:
                if self._job_completed:
                    break
                backoff.increase()
            else:
                backoff.decrease()
            logging.debug('backoff is now %s', backoff)

    async def _send_complete(self):
        ''' Send a subscription end event. '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        message.event.subscription_closed.reason = SubscriptionClosed.COMPLETE
        await self._websocket.send_message(message.SerializeToString())

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
        item.job_id = UUID(item_doc['job_id']).bytes
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
        await self._websocket.send_message(message.SerializeToString())

    async def _set_initial_job_status(self):
        ''' Query database for initial job status and update internal state. '''
        run_state = await self._db.get_job_run_state(self._job_id)
        logging.debug('%r Initial job state: %s', self, run_state)
        self._job_completed = run_state in FINISHED_STATES


class JobStatusSubscription:
    '''
    A subscription stream that emits updates about the status of all running
    jobs.

    It only sends events when something about a job has changed.
    '''

    def __init__(self, id_, websocket, stats_tracker, min_interval):
        '''
        Constructor.

        :param int id_: Subscription ID.
        :param trio_websocket.WebSocketConnection websocket: A WebSocket to send
            events to.
        :param starbelly.job.StatsTracker stats_tracker: An object that tracks
            crawl stats.
        :param float min_interval: The amount of time to wait in between
            sending events.
        '''
        self._id = id_
        self._websocket = websocket
        self._stats_tracker = stats_tracker
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
                await self._websocket.send_message(event.SerializeToString())
                await trio.sleep(self._min_interval)
        logger.info('%r Cancelled', self)

    def _make_event(self):
        '''
        Make an event to send to the client and update internal state.

        :rtype: starbelly_pb2.ServerMessage
        '''
        message = ServerMessage()
        message.event.subscription_id = self._id
        current_send = dict()
        import logging
        for job in self._stats_tracker.snapshot():
            logging.debug('job %r',job)
            job_id = job['id']
            current_send[job_id] = job
            if job == self._last_send.get(job_id):
                # No change since last send. Ignore this job.
                continue
            pb_job = message.event.job_list.jobs.add()
            pb_job.job_id = UUID(job_id).bytes
            pb_job.name = job['name']
            pb_job.item_count = job['item_count']
            pb_job.http_success_count = job['http_success_count']
            pb_job.http_error_count = job['http_error_count']
            pb_job.exception_count = job['exception_count']
            for seed in job['seeds']:
                pb_job.seeds.append(seed)
            for tag in job['tags']:
                pb_job.tags.append(tag)
            pb_job.started_at = job['started_at'].isoformat()
            if job['completed_at']:
                pb_job.completed_at = job['completed_at'].isoformat()
            pb_job.run_state = JobRunState.Value(job['run_state'].upper())
            for status_code, count in job['http_status_counts'].items():
                pb_job.http_status_counts[int(status_code)] = count

        self._last_send = current_send
        return message


class ResourceMonitorSubscription:
    ''' Keep track of usage for various resources. '''
    def __init__(self, id_, websocket, resource_monitor, history=0):
        ''' Constructor.

        :param int id_: Subscription ID.
        :param trio_websocket.WebSocketConnection websocket: A WebSocket to send
            events to.
        :type resource_monitor: starbelly.resource_monitor.ResourceMonitor
        :param int history: The number of historical measurements to send before
            streaming real-time measurements.
        '''
        self._id = id_
        self._websocket = websocket
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
                await self._websocket.send_message(event.SerializeToString())

            async for measurement in self._recv_channel:
                event = self._make_event(measurement)
                await self._websocket.send_message(event.SerializeToString())
        logger.info('%r Cancelled', self)

    def _make_event(self, measurement):
        '''
        Make an event to send to the client.

        :rtype: starbelly_pb2.ServerMessage
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

        for job_measure in measurement['jobs']:
            job = frame.jobs.add()
            job.job_id = UUID(job_measure['id']).bytes
            job.name = job_measure['name']
            job.current_downloads = job_measure['current_downloads']

        frame.current_downloads = measurement['current_downloads']
        frame.maximum_downloads = measurement['maximum_downloads']
        frame.rate_limiter = measurement['rate_limiter']
        return message


class TaskMonitorSubscription:
    '''
    Sends data showing whats kinds of tasks and how many of each are running.
    '''
    def __init__(self, id_, websocket, period, root_task):
        '''
        Constructor.

        :param int id_: The subscription ID.
        :param trio_websocket.WebSocketConnection websocket: A WebSocket to send
            events to.
        :param float period: The amount of time to wait in between events.
        :param trio.hazmat.Task root_task: The root task to build a task tree
            from.
        '''
        self._id = id_
        self._websocket = websocket
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
                await self._websocket.send_message(event.SerializeToString())
                await trio.sleep(self._period)

    def _make_event(self):
        '''
        Make an event containing task monitor data.

        :rtype: starbelly_pb2.ServerMessage
        '''
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
