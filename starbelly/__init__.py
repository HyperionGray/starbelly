import asyncio
import os


def get_path(relpath):
    ''' Return absolute path for given path relative to project root. '''

    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(base_dir, relpath))


def handle_future_exception(future):
    '''
    If a future has no return value, then you probably won't call its
    ``result()``, but you still want to detect any exceptions that occur.

    Use this function to automatically raise an exception if a future fails.
    '''

    print('handle_future_Exception')
    future.add_done_callback(lambda f: f.result())
