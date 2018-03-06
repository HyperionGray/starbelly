'''
A Python REPL for Starbelly.

This "shell" imports useful modules and sets up the application
configuration, database pool, and other useful features. This shell
is intended for use with Python's interactive flag, i.e.:

    $ python3 -im starbelly.shell
    >>> config['database']['user']
    'starbelly-app'

You can also load this in Jupyter Notebook by running this in the first cell:

    from starbelly.shell import *

The shell is handy for development and debugging in order to execute
sections of Starbelly without running the entire server.
'''

import asyncio
import logging
import queue
import sys
import time
import threading

import rethinkdb as r

from starbelly import VERSION
import starbelly.config
# import starbelly.crawl
import starbelly.db
import starbelly.downloader
import starbelly.policy
import starbelly.rate_limiter
import starbelly.robots
import starbelly.server
import starbelly.tracker


def crun(coroutine):
    '''
    Run ``coroutine`` on our custom loop.

    In some contexts, e.g. Jupyter notebook, there may already be an event loop
    running so we create our own loop and run it in a separate thread.
    '''
    def run_coro(coro, output_q):
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        output_q.put(result)

    q = queue.Queue()
    thread = threading.Thread(target=run_coro, args=(coroutine, q))
    thread.start()
    thread.join()
    return q.get()


def enable_jupyter():
    ''' Set up Jupyter event loop integration. '''
    from ipykernel.eventloops import register_integration

    def loop_asyncio(kernel):
        loop = asyncio.get_event_loop()

        def kernel_handler():
            loop.call_soon(kernel.do_one_iteration)
            loop.call_later(kernel._poll_interval, kernel_handler)

        loop.call_soon(kernel_handler)

        try:
            if not loop.is_running():
                loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    register_integration(loop_asyncio, 'asyncio')


def qiter(cursor, function=None):
    '''
    Iterate through results in RethinkDB ``cursor``.

    If ``function`` is defined, then ``function`` is called  on each item.
    '''
    async def _qiter(cursor, function):
        if function is None:
            try:
                async for item in cursor:
                    pass
            finally:
                await cursor.close()
            return None
        else:
            results = list()
            try:
                async for item in cursor:
                    results.append(function(item))
            finally:
                await cursor.close()
            return results

    return crun(_qiter(cursor, function))


def qrun(query, pool=None):
    ''' Run ``query`` on RethinkDB and return result. '''
    global db_pool
    pool = pool or db_pool
    async def _qrun(query):
        async with pool.connection() as conn:
            return await query.run(conn)
    return crun(_qrun(query))


def qshow(results):
    '''
    Query show: Display RethinkDB query results.

    This method correctly handles different types of results, such as a
    cursor, list, etc.
    '''
    async def _qshow(results):
        MAX_ITEMS = 100
        INDENT = '    '
        if isinstance(results, list):
            len_ = len(results)
            print(f'RethinkDB List (len={len_}): [')
            for item in results[:MAX_ITEMS]:
                print(f'{INDENT}{item},')
            if len_ > MAX_ITEMS:
                print(f'{INDENT}...')
            print(']')
        elif isinstance(results, r.Cursor):
            print('RethinkDB Cursor: [')
            item_count = 0
            try:
                async for item in results:
                    if item_count > MAX_ITEMS:
                        print(f'{INDENT}...')
                    print(f'{INDENT}{item},')
                    item_count += 1
            finally:
                await results.close()
            print(']')
        else:
            type_ = type(results)
            logger.error(f'RethinkDB UNKNOWN TYPE: {type_}')
            print(f'RethinkDB UNKNOWN: {results}')
    return crun(_qshow(results))


def __configure_logging():
    ''' The shell's logging is a bit different from the rest of the app. '''
    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    log_date_format = '%H:%M:%S'
    log_formatter = logging.Formatter(log_format, log_date_format)
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger('starbelly')
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def __db_connect():
    '''
    A helper function for getting a DB connection.

    Don't call this directly! Use the ``db_pool`` instance instead.
    '''
    db_config = config['database']
    return r.connect(
         host=db_config['host'],
         port=db_config['port'],
         db=db_config['db'],
         user=db_config['user'],
         password=db_config['password'],
    )


def __db_super_connect():
    '''
    A helper function for getting a DB connection as super user.

    Don't call this directly! Use the ``super_db_pool`` instance instead.
    '''
    db_config = config['database']
    return r.connect(
         host=db_config['host'],
         port=db_config['port'],
         db=db_config['db'],
         user=db_config['super_user'],
         password=db_config['super_password'],
    )


# The standard `if __name__ == "__main__"` guard isn't used here because we may
# want to import this in contexts where it isn't the main module but we still
# want the side effects, e.g. in a Jupyter notebook.
__configure_logging()
config = starbelly.config.get_config()
r.set_loop_type('asyncio')
loop = asyncio.new_event_loop()
db_pool = starbelly.db.AsyncRethinkPool(__db_connect)
super_db_pool = starbelly.db.AsyncRethinkPool(__db_super_connect)
logger = logging.getLogger('starbelly.shell')
logger.info(f'Starbelly Shell v{VERSION}')
