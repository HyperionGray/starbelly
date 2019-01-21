'''
A Python REPL for Starbelly.

This "shell" imports useful modules and sets up the application
configuration, database pool, and other useful features. This shell
is intended for use with Python's interactive flag, i.e.:

    $ python3 -im tools.shell
    >>> config['database']['user']
    'starbelly-app'

You can also load this in Jupyter Notebook by running this in the first cell:

    from tools.shell import *

The shell is handy for development and debugging in order to execute
sections of Starbelly without running the entire server.
'''

import functools
import logging
import sys

# import IPython
# from IPython import embed
from IPython.terminal.embed import InteractiveShellEmbed
from rethinkdb import RethinkDB
import trio

import starbelly.config
from starbelly.version import __version__


# Globals exposed in the shell:
r = RethinkDB()
r.set_loop_type('trio')
logger = None
config = None


def run_query(query, super_user=False):
    ''' Run ``query`` on RethinkDB and return result. '''
    async def async_query():
        db_config = config['database']
        kwargs = {
            'host': db_config['host'],
            'port': db_config['port'],
            'db': db_config['db'],
            'user': db_config['user'],
            'password': db_config['password'],
        }
        if super_user:
            kwargs['user'] = db_config['super_user']
            kwargs['password'] = db_config['super_password']
        async with trio.open_nursery() as nursery:
            kwargs['nursery'] = nursery
            connect_db = functools.partial(r.connect, **kwargs)
            conn = await connect_db()
            try:
                result = await query.run(conn)
            finally:
                await conn.close()
            return result

    return trio.run(async_query)


def print_results(results):
    '''
    Pretty print RethinkDB query results.

    This method correctly handles different types of results, such as a
    cursor, list, etc.
    '''
    async def async_print_results():
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

    trio.run(async_print_results)


def setup():
    ''' Set up configuration and logging. '''
    global config, logger
    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    log_date_format = '%H:%M:%S'
    log_formatter = logging.Formatter(log_format, log_date_format)
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger('tools.shell')
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    config = starbelly.config.get_config()


def main():
    ''' Run IPython shell. '''
    ipy_shell = InteractiveShellEmbed(
        banner1=f'IPython Shell: Starbelly v{__version__}')
    ipy_shell.magic('autoawait trio')
    ipy_shell()


setup()
if __name__ == '__main__':
    main()
else:
    print(f'Starbelly v{__version__} Shell')

