from contextlib import contextmanager

import pytest
import trio

from starbelly.rate_limiter import Expiry, RateLimiter, GLOBAL_RATE_LIMIT_TOKEN
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


def make_request(url, job=b'job1'):
    ''' Make a download request object. '''
    return DownloadRequest(
        job_id=job,
        url=url,
        cost=1,
        policy=None,
        output_queue=None,
        cookie_jar=None,
    )


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


async def test_limiter_is_initially_empty():
    rl = RateLimiter(capacity=1)
    assert len(rl) == 0


async def test_negative_capacity():
    with pytest.raises(ValueError):
        rl = RateLimiter(capacity=-1)


async def test_one_request():
    rl = RateLimiter(capacity=1)
    request = make_request('http://domain.example')
    await rl.push(request)
    assert len(rl) == 1
    next_request = await rl.get_next_request()
    assert next_request is request


async def test_two_requests_different_domains():
    '''
    The requests are for separate domains, so the rate limiter will emit both
    requests without delay.
    '''
    rl = RateLimiter(capacity=2)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    request1 = make_request('http://domain1.example')
    request2 = make_request('http://domain2.example')
    await rl.push(request1)
    await rl.push(request2)
    assert len(rl) == 2
    with assert_max_elapsed(seconds=1):
        next_request1 = await rl.get_next_request()
        rl.reset(next_request1.url)
        next_request2 = await rl.get_next_request()
        rl.reset(next_request2.url)
        assert next_request1 is request1
        assert next_request2 is request2


async def test_two_requests_same_domain(autojump_clock):
    '''
    The requests are for the same domain, so the rate limiter will impose a
    10 second delay between requests.
    '''
    rl = RateLimiter(capacity=2)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    request1 = make_request('http://domain.example/1')
    request2 = make_request('http://domain.example/2')
    await rl.push(request1)
    await rl.push(request2)
    assert len(rl) == 2
    with assert_min_elapsed(seconds=10):
        next_request1 = await rl.get_next_request()
        rl.reset(next_request1.url)
        next_request2 = await rl.get_next_request()
        rl.reset(next_request2.url)
        assert next_request1 is request1
        assert next_request2 is request2


async def test_rate_limiter_over_capacity(autojump_clock, nursery):
    '''
    The rate limiter will be over capacity when the 3rd item is added and will
    block for 5 seconds until ``remove_one_item()`` removes an item from the
    rate limiter.
    '''
    async def remove_one_item(when):
        nonlocal rl
        await trio.sleep(when)
        next_request1 = await rl.get_next_request()

    rl = RateLimiter(capacity=2)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    request1 = make_request('http://domain1.example')
    request2 = make_request('http://domain2.example')
    request3 = make_request('http://domain3.example')
    await rl.push(request1)
    await rl.push(request2)
    with assert_min_elapsed(seconds=5):
        nursery.start_soon(remove_one_item, 5)
        await rl.push(request3)
        assert len(rl) == 2


async def test_token_limit_supercedes_global_limit(autojump_clock):
    '''
    If a limit is set on a domain token, that rate limit is used, otherwise the
    global rate limit is used.
    '''
    rl = RateLimiter(capacity=3)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    token = rl.get_domain_token('domain.example')
    rl.set_rate_limit(token, 2)
    # These two requests should take ~2 seconds due to the domain rate limit.
    with assert_max_elapsed(seconds=2.5):
        request1 = make_request('http://domain.example/1')
        await rl.push(request1)
        request2 = make_request('http://domain.example/2')
        await rl.push(request2)
        next_request1 = await rl.get_next_request()
        rl.reset(request1.url)
        next_request2 = await rl.get_next_request()
        rl.reset(request2.url)
    # Let the domain timeout elapse.
    await trio.sleep(2)
    # Now if we delete the domain rate limit, the next two requests should take
    # 10 seconds due to the global rate limit.
    rl.delete_rate_limit(token)
    with assert_min_elapsed(seconds=10):
        request3 = make_request('http://domain.example/3')
        await rl.push(request3)
        request4 = make_request('http://domain.example/4')
        await rl.push(request4)
        next_request3 = await rl.get_next_request()
        rl.reset(request3.url)
        next_request4 = await rl.get_next_request()
        rl.reset(request4.url)
    # Deleting a non-existent token has no effect:
    rl.delete_rate_limit(token)


async def test_skip_expired_limit_if_nothing_pending(autojump_clock):
    ''' The rate limit for domain1 will expire before the rate limit for
    domain2, but since domain1 has no pending requests, it will rate for domain2
    to become available again. '''
    rl = RateLimiter(capacity=3)
    token1 = rl.get_domain_token('domain1.example')
    token2 = rl.get_domain_token('domain2.example')
    rl.set_rate_limit(token1, 1)
    rl.set_rate_limit(token2, 2)
    request1 = make_request('http://domain1.example')
    request2a = make_request('http://domain2.example/a')
    request2b = make_request('http://domain2.example/b')
    await rl.push(request1)
    await rl.push(request2a)
    await rl.push(request2b)
    with assert_min_elapsed(seconds=2):
        next_request1 = await rl.get_next_request()
        rl.reset(request1.url)
        next_request2a = await rl.get_next_request()
        rl.reset(request2a.url)
        next_request2b = await rl.get_next_request()
        rl.reset(request2b.url)
    assert next_request1 is request1
    assert next_request2a is request2a
    assert next_request2b is request2b


async def test_remove_job():
    rl = RateLimiter(capacity=3)
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    request1 = make_request('http://domain1.example', job=b'job1')
    request2 = make_request('http://domain2.example', job=b'job2')
    await rl.push(request1)
    await rl.push(request2)
    rl.remove_job(b'job1')
    assert len(rl) == 1


async def test_push_after_get(autojump_clock, nursery):
    ''' If nothing is pending, then get_next_request() will wait for another
    task to call push(). '''
    async def wait_push():
        nonlocal rl, request
        await trio.sleep(2)
        await rl.push(request)
    rl = RateLimiter(capacity=1)
    request = make_request('http://domain.example')
    rl.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, 10)
    with assert_min_elapsed(seconds=2):
        nursery.start_soon(wait_push)
        next_request = await rl.get_next_request()
    assert next_request == request

