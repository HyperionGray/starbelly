from contextlib import contextmanager
from functools import wraps
import pathlib
from os.path import dirname
from sys import path
from unittest.mock import Mock

import pytest
import trio
import trio_asyncio


# Add this project to the Python path.
path.append(dirname(dirname(__file__)))


@pytest.fixture
async def asyncio_loop():
    ''' Open an asyncio loop. Useful for things like aiohttp.CookieJar that
    require a global loop. '''
    async with trio_asyncio.open_loop() as loop:
        yield loop


@contextmanager
def assert_min_elapsed(seconds):
    '''
    Fail the test if the execution of a block takes less than ``seconds``.
    '''
    start = trio.current_time()
    yield
    elapsed = trio.current_time() - start
    assert elapsed >= seconds, 'Completed in under {} seconds'.format(seconds)


@contextmanager
def assert_max_elapsed(seconds):
    '''
    Fail the test if the execution of a block takes longer than ``seconds``.
    '''
    try:
        with trio.fail_after(seconds):
            yield
    except trio.TooSlowError:
        pytest.fail('Failed to complete within {} seconds'.format(seconds))


@contextmanager
def assert_elapsed(seconds, delta=0.1):
    '''
    Fail the test if the execution of a block takes more than seconds+delta time
    or less than seconds-delta time.
    '''
    with assert_min_elapsed(seconds-delta), assert_max_elapsed(seconds+delta):
        yield


def get_mock_coro(return_value):
    ''' Return a coroutine that can be assigned to a test mock. '''
    async def mock_coro(*args, **kwargs):
        return return_value

    return Mock(wraps=mock_coro)


class fail_after:
    ''' This decorator fails if the runtime of the decorated function (as
    measured by the Trio clock) exceeds the specified value. '''
    def __init__(self, seconds):
        self._seconds = seconds

    def __call__(self, fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            with trio.move_on_after(self._seconds) as cancel_scope:
                await fn(*args, **kwargs)
            if cancel_scope.cancelled_caught:
                pytest.fail('Test runtime exceeded the maximum {} seconds'
                    .format(self._seconds))
        return wrapper


async def async_iter(iter):
    '''
    Convert a sychronous iterator into an async iterator.

    :param iterable iter:
    '''
    for item in iter:
        await trio.sleep(0)
        yield item
