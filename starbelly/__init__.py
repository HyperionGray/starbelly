import asyncio
import os

import logging
logger = logging.getLogger(__name__)


def get_path(relative_path=None):
    """ Return an absolute path to a project relative path. """

    root_path = os.path.dirname(os.path.dirname(__file__))

    if relative_path is None:
        return root_path
    else:
        return os.path.abspath(os.path.join(root_path, relative_path))


def raise_future_exception(future):
    '''
    If a future has no return value, then you probably won't call its
    ``result()``, but you still want to detect any exceptions that occur.

    This silently swallows CanceledError, but any other exception is raised.
    '''

    def raise_exception(f):
        try:
            f.result()
        except asyncio.CancelledError:
            pass
        except:
            raise

    future.add_done_callback(raise_exception)
