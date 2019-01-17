from contextlib import contextmanager
from functools import wraps
import pathlib
import sys

import pytest
import trio
import trio_asyncio


# Add starbelly package to the path. Not sure how to do this with pipenv
# instead?
pkg = pathlib.Path(__file__).parent.parent
sys.path.append(str(pkg))


@pytest.fixture
async def asyncio_loop():
    ''' Open an asyncio loop. Useful for things like aiohttp.CookieJar that
    require a global loop. '''
    async with trio_asyncio.open_loop() as loop:
        yield


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
