import asyncio
import os


def get_path(relative_path=None):
    """ Return an absolute path to a project relative path. """

    root_path = os.path.dirname(os.path.dirname(__file__))

    if relative_path is None:
        return root_path
    else:
        return os.path.abspath(os.path.join(root_path, relative_path))


def handle_future_exception(future):
    '''
    If a future has no return value, then you probably won't call its
    ``result()``, but you still want to detect any exceptions that occur.

    Use this function to automatically raise an exception if a future fails.
    '''

    future.add_done_callback(lambda f: f.result())
