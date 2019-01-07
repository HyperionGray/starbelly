from functools import wraps
import pathlib
import sys

import pytest
import trio


# Add starbelly package to the path. Not sure how to do this with pipenv
# instead?
pkg = pathlib.Path(__file__).parent.parent
sys.path.append(str(pkg))


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
