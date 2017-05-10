'''
A Python REPL for Starbelly.

This "shell" imports useful modules and sets up the application configuration,
database pool, and other useful features. This shell is intended for use with
Python's interactive flag, i.e.:

    $ python3 -im starbelly.shell
    >>> config['database']['user']
    'starbelly-app'

The shell is handy for development and debugging in order to execute sections of
Starbelly without running the entire server.
'''

import asyncio
import logging
import sys

import rethinkdb as r

from starbelly import VERSION
import starbelly.config
import starbelly.crawl
import starbelly.db
import starbelly.downloader
import starbelly.policy
import starbelly.rate_limiter
import starbelly.robots
import starbelly.server
import starbelly.tracker


def __configure_logging():
    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    log_date_format = '%H:%M:%S'
    log_formatter = logging.Formatter(log_format, log_date_format)
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger('starbelly')
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def __db_connect():
    db_config = config['database']
    return r.connect(
         host=db_config['host'],
         port=db_config['port'],
         db=db_config['db'],
         user=db_config['user'],
         password=db_config['password'],
    )


__configure_logging()
config = starbelly.config.get_config()
loop = asyncio.get_event_loop()
r.set_loop_type('asyncio')
db_pool = starbelly.db.AsyncRethinkPool(__db_connect)
logger = logging.getLogger('starbelly.shell')

logger.info(f'Starbelly Shell v{VERSION}')
