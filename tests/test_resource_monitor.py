from collections import namedtuple
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import trio

from . import assert_min_elapsed, assert_max_elapsed
from starbelly.rate_limiter import RateLimiter
from starbelly.resource_monitor import ResourceMonitor


@pytest.fixture
def rate_limiter():
    return RateLimiter(1)


async def test_history(autojump_clock, nursery, rate_limiter):
    '''
    Set interval to 2 seconds and run for 11 seconds. This should produce
    6 measurements.

    Note: this test doesn't mock out psutil, so it also ensures that we are
    consuming the psutil API correctly.
    '''
    job1_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    crawl_resources_fn = lambda: {
        'current_downloads': 3,
        'maximum_downloads': 10,
        'jobs': [{
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'name': 'Test Job',
            'current_downloads': 3,
        }],
    }
    rm = ResourceMonitor(interval=2, buffer_size=300,
        crawl_resources_fn=crawl_resources_fn, rate_limiter=rate_limiter)
    nursery.start_soon(rm.run)
    await trio.sleep(11)
    history1 = list(rm.history())
    assert len(history1) == 6
    # We should also be able to get a subset of history
    history2 = list(rm.history(3))
    assert len(history2) == 3
    assert history1[0]['timestamp'] < history2[0]['timestamp']


async def test_measurement(autojump_clock, nursery, mocker,
    rate_limiter):
    ''' Mock out inputs and check that the resource monitor formats the data
    correctly. '''
    # Set up patches
    Consumed = namedtuple('Memory', 'used total')
    Mount = namedtuple('Disk', 'mountpoint')
    Nic = namedtuple('Nic', 'bytes_sent bytes_recv')
    psutil_cpu_percent = mocker.patch('psutil.cpu_percent')
    psutil_cpu_percent.return_value = [12.3, 45.6]
    ps_util_virtual_memory = mocker.patch('psutil.virtual_memory')
    ps_util_virtual_memory.return_value = Consumed(100_000, 200_000)
    psutil_disk_partitions = mocker.patch('psutil.disk_partitions')
    psutil_disk_partitions.return_value = [Mount('/'), Mount('/mnt/external')]
    psutil_disk_usage = mocker.patch('psutil.disk_usage')
    psutil_disk_usage.return_value = Consumed(300_000, 400_000)
    psutil_net_io_counters = mocker.patch('psutil.net_io_counters')
    psutil_net_io_counters.return_value = {
        'eth0': Nic(100, 200),
        'eth1': Nic(300, 400),
    }

    # The crawl resources can be instantiated right here; no mocking required.
    job1_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    job2_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    crawl_resources_fn = lambda: {
        'current_downloads': 5,
        'maximum_downloads': 10,
        'jobs': [{
            'id': job1_id,
            'name': 'Test Job 1',
            'current_downloads': 3,
        },{
            'id': job2_id,
            'name': 'Test Job 2',
            'current_downloads': 2,
        }],
    }

    # Run the resource monitor
    rm = ResourceMonitor(interval=1, buffer_size=300,
        crawl_resources_fn=crawl_resources_fn, rate_limiter=rate_limiter)
    rm_recv = rm.get_channel(channel_size=5)
    nursery.start_soon(rm.run)

    # Read one measurement:
    measurement = await rm_recv.receive()
    assert measurement['cpus'] == [12.3, 45.6]
    assert measurement['memory_used'] == 100_000
    assert measurement['memory_total'] == 200_000
    assert len(measurement['disks']) == 2
    assert measurement['disks'][0]['mount'] == '/'
    assert measurement['disks'][0]['used'] == 300_000
    assert measurement['disks'][0]['total'] == 400_000
    assert measurement['disks'][1]['mount'] == '/mnt/external'
    assert measurement['disks'][1]['used'] == 300_000
    assert measurement['disks'][1]['total'] == 400_000
    assert len(measurement['networks']) == 2
    assert measurement['networks'][0]['name'] == 'eth0'
    assert measurement['networks'][0]['sent'] == 100
    assert measurement['networks'][0]['received'] == 200
    assert measurement['networks'][1]['name'] == 'eth1'
    assert measurement['networks'][1]['sent'] == 300
    assert measurement['networks'][1]['received'] == 400
    assert measurement['jobs'][0]['id'] == job1_id
    assert measurement['jobs'][0]['name'] == 'Test Job 1'
    assert measurement['jobs'][0]['current_downloads'] == 3
    assert measurement['jobs'][1]['id'] == job2_id
    assert measurement['jobs'][1]['name'] == 'Test Job 2'
    assert measurement['jobs'][1]['current_downloads'] == 2
    assert measurement['current_downloads'] == 5
    assert measurement['maximum_downloads'] == 10
    assert measurement['rate_limiter'] == 0


async def test_slow_channel(autojump_clock, nursery, rate_limiter):
    ''' If there are two subscribers to the resource monitor and one is slow, it
    will not prevent delivery to the other subscriber. '''
    crawl_resources_fn = lambda: {
        'current_downloads': 3,
        'maximum_downloads': 10,
        'jobs': [{
            'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'name': 'Test Job',
            'current_downloads': 3,
        }],
    }

    rm = ResourceMonitor(interval=1, buffer_size=300,
        crawl_resources_fn=crawl_resources_fn, rate_limiter=rate_limiter)
    slow_recv = rm.get_channel(channel_size=1)
    fast_recv = rm.get_channel(channel_size=1)
    nursery.start_soon(rm.run)
    # The fast reader gets one measurement per second even though the slow
    # reader is blocked.
    with assert_min_elapsed(3), assert_max_elapsed(4):
        for _ in range(4):
            await fast_recv.receive()
    # Now we close the slow reader and make sure the fast reader still gets
    # measurements.
    await slow_recv.aclose()
    with assert_min_elapsed(3), assert_max_elapsed(4):
        for _ in range(3):
            await fast_recv.receive()

