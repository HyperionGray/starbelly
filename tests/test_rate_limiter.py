from contextlib import contextmanager

import pytest
import trio

from starbelly.crawl import FrontierItem
from starbelly.rate_limiter import Expiry, RateLimiter, GLOBAL_RATE_LIMIT_TOKEN


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


def test_compare_expiry_to_expiry():
    token = b'\x01' * 16
    expiry1 = Expiry(time=1, token=token)
    expiry2 = Expiry(time=2, token=token)


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
    request = FrontierItem('http://domain.example', cost=1)
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
    request1 = FrontierItem('http://domain1.example', cost=1)
    request2 = FrontierItem('http://domain2.example', cost=1)
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
    request1 = FrontierItem('http://domain.example/1', cost=1)
    request2 = FrontierItem('http://domain.example/2', cost=1)
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
    request1 = FrontierItem('http://domain1.example', cost=1)
    request2 = FrontierItem('http://domain2.example', cost=1)
    request3 = FrontierItem('http://domain3.example', cost=1)
    await rl.push(request1)
    await rl.push(request2)
    with assert_min_elapsed(seconds=5):
        nursery.start_soon(remove_one_item, 5)
        await rl.push(request3)
        assert len(rl) == 2
