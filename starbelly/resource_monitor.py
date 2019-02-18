from collections import deque
from datetime import datetime, timezone
import logging
import math
import os
from time import time

import psutil
import trio

from .starbelly_pb2 import ServerMessage


logger = logging.getLogger(__name__)


class ResourceMonitor:
    '''
    Keep track of consumption and usage statistics for various resources.
    '''
    def __init__(self, interval, buffer_size, crawl_resources_fn, rate_limiter):
        '''
        Constructor.

        :param float interval: The number of seconds to wait between
            measurements.
        :param int buffer_size: The number of measurements to store in the
            internal buffer.
        :param callable crawl_resource_fn: A function that will return a dict
            of crawl resources.
        :param starbelly.rate_limiter.RateLimiter rate_limiter:
        '''
        self._interval = interval
        self._crawl_resources_fn = crawl_resources_fn
        self._rate_limiter = rate_limiter
        self._measurements = deque(maxlen=buffer_size)
        self._channels = list()

    def get_channel(self, channel_size):
        '''
        Get a statistics channel. The resource monitor will send measurements to
        this channel until the receive end is closed. Note that if the channel
        is full, the resource monitor does not block! It will drop messages
        instead.

        :param int channel_size: The size of the channel to create.
        :returns: A channel that will receive resource statistics at regular
            intervals.
        :rtype: trio.ReceiveChannel
        '''
        logger.debug('Creating new channel with size=%d', channel_size)
        send_channel, recv_channel = trio.open_memory_channel(channel_size)
        self._channels.append(send_channel)
        return recv_channel

    def history(self, n=None):
        '''
        Return the most recent ``n`` measurements.

        :param int n: The number of measurements to retrieve. If ``n`` is None
            or there are fewer than ``n`` measurements, return all measurements.
        :rtype: list
        '''
        # A deque can't be sliced, so we have to do some extra work to return
        # the <n> most recent measurements from the end.
        history_iter = iter(self._measurements)
        if n is not None:
            for _ in range(len(self._measurements) - n):
                next(history_iter)
        return list(history_iter)

    async def run(self):
        '''
        Run the resource monitor.

        :returns: Runs until cancelled.
        '''
        next_run = trio.current_time() + self._interval
        while True:
            measurement = self._measure()
            self._measurements.append(measurement)
            to_remove = set()
            for channel in self._channels:
                try:
                    channel.send_nowait(measurement)
                except trio.WouldBlock:
                    continue
                except trio.BrokenResourceError:
                    to_remove.add(channel)
            for channel in to_remove:
                logger.debug('Removing closed channel')
                self._channels.remove(channel)
            next_run += self._interval
            await trio.sleep(next_run - trio.current_time())

    def _measure(self):
        '''
        Record one set of measurements.

        :rtype: dict
        '''
        measurement = dict()
        measurement['timestamp'] = datetime.now(timezone.utc)

        # CPUs
        measurement['cpus'] = psutil.cpu_percent(percpu=True)

        # Memory
        vm = psutil.virtual_memory()
        measurement['memory_used'] = vm.used
        measurement['memory_total'] = vm.total

        # Disks
        measurement['disks'] = list()
        for partition in psutil.disk_partitions():
            disk = dict()
            disk['mount'] = partition.mountpoint
            usage = psutil.disk_usage(disk['mount'])
            disk['used'] = usage.used
            disk['total'] = usage.total
            measurement['disks'].append(disk)

        # Networks
        measurement['networks'] = list()
        for name, nic in psutil.net_io_counters(pernic=True).items():
            net = dict()
            net['name'] = name
            net['sent'] = nic.bytes_sent
            net['received'] = nic.bytes_recv
            measurement['networks'].append(net)

        # Crawl Job Resources
        measurement['jobs'] = list()
        crawl_resources = self._crawl_resources_fn()
        for job in crawl_resources['jobs']:
            measurement['jobs'].append(job.copy())

        # Crawl Global Resources
        measurement['current_downloads'] = crawl_resources['current_downloads']
        measurement['maximum_downloads'] = crawl_resources['maximum_downloads']
        measurement['rate_limiter'] = self._rate_limiter.item_count

        return measurement
