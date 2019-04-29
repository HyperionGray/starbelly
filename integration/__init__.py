'''
This module contains integration tests.

These tests rely on a RethinkDB server running on localhost 28015.
'''
from functools import wraps

import pytest
from rethinkdb import RethinkDB
import trio

from starbelly.config import get_config

# Add this project to the Python path:
from os.path import dirname
from sys import path
path.append(dirname(dirname(__file__)))


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


@pytest.fixture
async def db_pool(nursery):
    r = RethinkDB()
    r.set_loop_type('trio')
    db_config = get_config()['database']
    db_pool = r.ConnectionPool(
        host=db_config['host'],
        port=db_config['port'],
        db='integration_testing',
        user=db_config['super_user'],
        password=db_config['super_password'],
        nursery=nursery
    )
    async with db_pool.connection() as conn:
        await r.db_create('integration_testing').run(conn)
    yield db_pool
    async with db_pool.connection() as conn:
        await r.db_drop('integration_testing').run(conn)
    await db_pool.close()
