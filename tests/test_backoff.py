from . import assert_elapsed
from starbelly.backoff import ExponentialBackoff


async def test_backoff_no_change(autojump_clock):
    ''' Backoff starts at 1, so 3 iterations takes ~2 seconds. '''
    with assert_elapsed(2):
        loop_count = 0
        async for _ in ExponentialBackoff(min_=1, max_=64):
            loop_count += 1
            if loop_count == 3:
                break


async def test_backoff_increase(autojump_clock):
    ''' Increase backoff on each loop. Backoffs should be equal to 1, 2, 4,
    8, 16, 16, but the first value is skipped, so the total is ~46 seconds. '''
    with assert_elapsed(seconds=46):
        loop_count = 0
        backoff = ExponentialBackoff(min_=1, max_=16)
        async for n in backoff:
            backoff.increase()
            loop_count += 1
            if loop_count == 6: break


async def test_backoff_returns_value(autojump_clock):
    ''' Backoff returns the current value. Increase up to max and then decrease
    back to starting point. '''
    backoff = ExponentialBackoff(min_=1, max_=8)
    assert await backoff.__anext__() == 0
    assert await backoff.__anext__() == 1
    backoff.increase()
    assert await backoff.__anext__() == 2
    backoff.increase()
    assert await backoff.__anext__() == 4
    backoff.increase()
    assert await backoff.__anext__() == 8
    backoff.increase()
    assert await backoff.__anext__() == 8
    backoff.decrease()
    assert await backoff.__anext__() == 4
    backoff.decrease()
    assert await backoff.__anext__() == 2
    backoff.decrease()
    assert await backoff.__anext__() == 1
    backoff.decrease()
    assert await backoff.__anext__() == 1
