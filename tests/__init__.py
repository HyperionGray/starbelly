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


class AsyncMock:
    ''' A mock that acts like an async def function. '''
    def __init__(self, return_value=None, return_values=None, raises=None,
            side_effect=None):
        self._raises = None
        self._side_effect = None
        self._return_value = None
        self._index = None
        self._call_count = 0
        self._call_args = None
        self._call_kwargs = None

        if raises:
            self._raises = raises
        elif return_values:
            self._return_value = return_values
            self._index = 0
        elif side_effect:
            self._side_effect=side_effect
        else:
            self._return_value = return_value

    @property
    def call_args(self):
        return self._call_args

    @property
    def call_kwargs(self):
        return self._call_kwargs

    @property
    def called(self):
        return self._call_count > 0

    @property
    def call_count(self):
        return self._call_count

    async def __call__(self, *args, **kwargs):
        self._call_args = args
        self._call_kwargs = kwargs
        self._call_count += 1
        if self._raises:
            raise(self._raises)
        elif self._side_effect:
            return await self._side_effect(*args, **kwargs)
        elif self._index is not None:
            return_index = self._index
            self._index += 1
            return self._return_value[return_index]
        else:
            return self._return_value


async def async_iter(iter):
    '''
    Convert a synchronous iterable into an async iterator.

    :param iterable iter:
    '''
    for item in iter:
        await trio.sleep(0)
        yield item


@pytest.fixture
async def asyncio_loop():
    ''' Open an asyncio loop. Useful for things like aiohttp.CookieJar that
    require a global loop. '''
    async with trio_asyncio.open_loop() as loop:
        yield loop


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
