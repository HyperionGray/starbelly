'''
This module contains integration tests.

These tests rely on a RethinkDB server running on localhost 28015.
'''
from functools import wraps

import pytest
import trio


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
