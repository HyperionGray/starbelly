import asyncio
from collections import deque
from datetime import datetime
import logging
import math
import os
from time import time
from uuid import UUID

from dateutil.tz import tzlocal
import psutil

from .pubsub import PubSub
from protobuf.server_pb2 import ServerMessage


logger = logging.getLogger(__name__)


class ResourceMonitor:
    ''' Keep track of usage for various resources. '''

    # The number of frames to buffer. At one frame per second, this buffers 5
    # minutes of resource data.
    FRAME_BUFFER = 300

    def __init__(self, crawl_manager, rate_limiter, downloader):
        self.new_frame = PubSub()
        self._crawl_manager = crawl_manager
        self._rate_limiter = rate_limiter
        self._downloader = downloader
        self._frames = deque(maxlen=self.FRAME_BUFFER)

    def history(self, n):
        '''
        Retrieve ``n`` historical frames.

        A ``deque`` can't be sliced, so we have to do some extra work to return
        the last ``n`` frames. The approach here is more efficient than indexing
        each item individually.
        '''
        history_iter = iter(self._frames)
        # Skip old frames.
        for _ in range(len(self._frames) - n):
            next(history_iter)
        # Yield the remaining frames.
        yield from history_iter

    async def run(self):
        ''' Run the monitor. '''
        while True:
            try:
                frame = await self._make_frame()
                self._frames.append(frame)
                self.new_frame.publish(frame)
                now = time()
                # Sleep until the beginning of the next second.
                await asyncio.sleep(math.floor(now) - now + 1)
            except asyncio.CancelledError:
                # Cancellation is okay.
                break

    async def _make_frame(self):
        ''' Create a resource frame. '''
        message = ServerMessage()
        frame = message.event.resource_frame
        frame.timestamp = datetime.now(tzlocal()).isoformat()

        # CPUs
        for cpu_percent in psutil.cpu_percent(percpu=True):
            cpu = frame.cpus.add()
            cpu.usage = cpu_percent

        # Memory
        vm = psutil.virtual_memory()
        frame.memory.used = vm.used
        frame.memory.total = vm.total

        # Disks
        for partition in psutil.disk_partitions():
            disk = frame.disks.add()
            disk.mount = partition.mountpoint
            usage = psutil.disk_usage(disk.mount)
            disk.used = usage.used
            disk.total = usage.total

        # Networks
        for name, nic in psutil.net_io_counters(pernic=True).items():
            net = frame.networks.add()
            net.name = name
            net.sent = nic.bytes_sent
            net.received = nic.bytes_recv

        # Crawls
        for crawl_stat in self._crawl_manager.get_stats():
            crawl = frame.crawls.add()
            crawl.job_id = UUID(crawl_stat.job_id).bytes
            crawl.frontier = crawl_stat.frontier
            crawl.pending = crawl_stat.pending
            crawl.extraction = crawl_stat.extraction

        # Other components
        frame.rate_limiter.count = self._rate_limiter.count()
        frame.downloader.count = self._downloader.count()

        return message
