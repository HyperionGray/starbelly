from contextlib import contextmanager
from functools import wraps
import pathlib
from os.path import dirname
from sys import path

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
