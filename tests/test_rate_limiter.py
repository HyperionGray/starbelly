from contextlib import contextmanager
from uuid import UUID

import pytest
import trio

from . import fail_after
from starbelly.rate_limiter import (
    Expiry,
    get_domain_token,
    GLOBAL_RATE_LIMIT_TOKEN,
    RateLimiter,
)
from starbelly.downloader import DownloadRequest


@contextmanager
def assert_min_elapsed(seconds=None):
    '''
    Fail the test if the execution of a block takes less than ``seconds``.
    '''
    start = trio.current_time()
    yield
    elapsed = trio.current_time() - start
    assert elapsed >= seconds, 'Completed in under {} seconds'.format(seconds)


@contextmanager
def assert_max_elapsed(seconds=None):
    '''
    Fail the test if the execution of a block takes longer than ``seconds``.
    '''
    try:
        with trio.fail_after(seconds):
            yield
    except trio.TooSlowError:
        pytest.fail('Failed to complete within {} seconds'.format(seconds))


def make_request(job_id, url):
    ''' Make a download request object. '''
    return DownloadRequest(
        job_id=job_id,
        method='GET',
        url=url,
        form_data=None,
        cost=1.0,
        policy=None,
        cookie_jar=None
    )


def test_expiry_repr():
    token = b'\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff'
    expiry = Expiry(time=1.5, token=token)
    assert repr(expiry) == \
        'Expiry(time=1.500, token=00112233445566778899aabbccddeeff)'


def test_compare_expiry_to_expiry():
    token = b'\x01' * 16
    expiry1 = Expiry(time=1, token=token)
    expiry2 = Expiry(time=1, token=token)
    expiry3 = Expiry(time=2, token=token)
    assert expiry1 == expiry2
    assert expiry2 < expiry3


def test_compare_expiry_to_float():
    token = b'\x01' * 16
    expiry1 = Expiry(time=2, token=token)
    assert expiry1 > 1.5
    assert 1.5 < expiry1
    assert expiry1 == 2.0


async def test_one_request(nursery):
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(1)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    job_recv = rl.add_job(job_id)
    assert rl.job_count == 1
    nursery.start_soon(rl.run)
    request = make_request(job_id, 'http://domain.example')
    await request_send.send(request)
    job_request = await job_recv.receive()
    assert job_request is request


async def test_two_requests_different_domains(nursery):
    '''
    The requests are for separate domains, so the rate limiter will emit both
    requests without delay.
    '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)
    request1 = make_request(job_id, 'http://domain1.example')
    request2 = make_request(job_id, 'http://domain2.example')
    await request_send.send(request1)
    await request_send.send(request2)
    with assert_max_elapsed(seconds=1):
        job_request1 = await job_recv.receive()
        job_request2 = await job_recv.receive()
        assert job_request1 is request1
        assert job_request2 is request2


async def test_two_requests_same_domain(autojump_clock, nursery):
    '''
    The requests are for the same domain, so the rate limiter will impose a
    10 second delay between the reset of the first request and issuing the
    second request.
    '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)
    request1 = make_request(job_id, 'http://domain.example/1')
    request2 = make_request(job_id, 'http://domain.example/2')
    await request_send.send(request1)
    await request_send.send(request2)
    job_request1 = await job_recv.receive()
    with assert_min_elapsed(seconds=10):
        await reset_send.send(job_request1.url)
        job_request2 = await job_recv.receive()
    assert job_request1 is request1
    assert job_request2 is request2


async def test_rate_limiter_over_capacity(autojump_clock, nursery):
    '''
    The rate limiter will be over capacity when the 3rd item is added and will
    block for 5 seconds until ``remove_one_request()`` reads one item from the
    rate limiter.
    '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)
    request1 = make_request(job_id, 'http://domain1.example')
    request2 = make_request(job_id, 'http://domain2.example')
    request3 = make_request(job_id, 'http://domain3.example')
    await request_send.send(request1)
    await request_send.send(request2)

    async def read_one_request(when):
        await trio.sleep(when)
        await job_recv.receive()

    with assert_min_elapsed(seconds=5):
        async with trio.open_nursery() as inner:
            inner.start_soon(read_one_request, 5)
            await request_send.send(request3)


async def test_token_limit_supercedes_global_limit(autojump_clock, nursery):
    '''
    If a limit is set on a domain token, that rate limit is used, otherwise the
    global rate limit is used.
    '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    token = get_domain_token('domain.example')
    rl.set_rate_limit(token, 2)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)

    # These two requests should take ~2 seconds due to the domain rate limit.
    with assert_max_elapsed(seconds=2.5):
        request1 = make_request(job_id, 'http://domain.example/1')
        request2 = make_request(job_id, 'http://domain.example/2')
        await request_send.send(request1)
        await request_send.send(request2)
        await job_recv.receive()
        await reset_send.send(request1.url)
        await job_recv.receive()
        await reset_send.send(request2.url)

    # Now if we delete the domain rate limit, the next two requests should take
    # 10 seconds due to the global rate limit.
    await trio.sleep(2)
    rl.delete_rate_limit(token)
    with assert_min_elapsed(seconds=10):
        request3 = make_request(job_id, 'http://domain.example/3')
        request4 = make_request(job_id, 'http://domain.example/4')
        await request_send.send(request3)
        await request_send.send(request4)
        await job_recv.receive()
        await reset_send.send(request3.url)
        await job_recv.receive()
        await reset_send.send(request4.url)

    # Deleting a non-existent token has no effect:
    rl.delete_rate_limit(token)


async def test_skip_expired_limit_if_nothing_pending(autojump_clock, nursery):
    ''' The rate limit for domain1 will expire before the rate limit for
    domain2, but since domain1 has no pending requests, it will wait for domain2
    to become available again. '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    token1 = get_domain_token('domain1.example')
    token2 = get_domain_token('domain2.example')
    rl.set_rate_limit(token1, 1)
    rl.set_rate_limit(token2, 2)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)
    request1 = make_request(job_id, 'http://domain1.example')
    request2a = make_request(job_id, 'http://domain2.example/a')
    request2b = make_request(job_id, 'http://domain2.example/b')
    await request_send.send(request1)
    await request_send.send(request2a)
    await request_send.send(request2b)
    with assert_min_elapsed(seconds=2):
        job_request1 = await job_recv.receive()
        await reset_send.send(request1.url)
        job_request2a = await job_recv.receive()
        await reset_send.send(request2a.url)
        job_request2b = await job_recv.receive()
        await reset_send.send(request2b.url)
    assert job_request1 is request1
    assert job_request2a is request2a
    assert job_request2b is request2b


async def test_push_after_get(autojump_clock, nursery):
    ''' If a job is waiting for a request but nothing is pending, then the rate
    limiter will wait until it receives a request. '''
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    semaphore = trio.Semaphore(2)
    request_send, request_recv = trio.open_memory_channel(0)
    reset_send, reset_recv = trio.open_memory_channel(0)
    rl = RateLimiter(semaphore, request_recv, reset_recv)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    job_recv = rl.add_job(job_id)
    nursery.start_soon(rl.run)
    request = make_request(job_id, 'http://domain.example')

    async def wait_to_send():
        await trio.sleep(2)
        await request_send.send(request)

    with assert_min_elapsed(seconds=2):
        nursery.start_soon(wait_to_send)
        job_request = await job_recv.receive()
    assert job_request is request

