from contextlib import contextmanager
from functools import wraps
import pathlib
import sys

import pytest
import trio


# Add starbelly package to the path. Not sure how to do this with pipenv
# instead?
pkg = pathlib.Path(__file__).parent.parent
sys.path.append(str(pkg))


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
