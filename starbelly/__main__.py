import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time

import rethinkdb as r
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import get_path
from .db import AsyncRethinkPool
from .config import get_config
from .crawl import CrawlManager
from .downloader import Downloader
from .rate_limiter import RateLimiter
from .server import Server
from .tracker import Tracker


class ProcessWatchdog(FileSystemEventHandler):
    ''' Handle watchdog events by restarting a subprocess. '''

    def __init__(self):
        ''' Constructor. '''

        self._process = None

    def dispatch(self, event):
        ''' Restart the subprocess if a source/config file changed. '''

        path = event.src_path
        descr = '({} was {})'.format(event.src_path, event.event_type)

        if path.endswith('.py') or path.endswith('.ini'):
            print('Reloading server... ' + descr)
            if self._process is not None:
                try:
                    self._process.send_signal(signal.SIGINT)
                    self._process.wait()
                    self._process = None
                except ProcessLookupError:
                    pass # The process already died.
            self.start_process()

    def join(self):
        ''' Wait for subprocess to exit. '''
        self._process.wait()

    def start_process(self):
        ''' Start the subprocess. '''

        if self._process is not None:
            msg = 'Cannot start subprocess if it is already running.'
            raise RuntimeError(msg)

        time.sleep(1)
        args = [sys.executable, '-m', __package__] + sys.argv[1:]
        new_env = dict(os.environ)
        new_env['WATCHDOG_RUNNING'] = '1'
        self._process = subprocess.Popen(args, env=new_env)


def configure_logging(log_level):
    ''' Set default format and output stream for logging. '''

    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    log_formatter = logging.Formatter(log_format, log_date_format)
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger('starbelly')
    logger.addHandler(log_handler)
    logger.setLevel(getattr(logging, log_level.upper()))

    return logger


def db_factory(db_config):
    ''' Returns a function that connects to the database. '''

    def db_connect():
        return r.connect(
            host=db_config['host'],
            port=db_config['port'],
            db=db_config['db'],
            user=db_config['user'],
            password=db_config['password'],
        )

    return db_connect


def get_args():
    ''' Parse command line arguments. '''

    arg_parser = argparse.ArgumentParser(description='Starbelly')

    arg_parser.add_argument(
        '--log-level',
        default='info',
        metavar='LEVEL',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Set logging verbosity (default: info)'
    )

    arg_parser.add_argument(
        '--ip',
        default='127.0.0.1',
        help='The IP address to bind to (default: 127.0.0.1)'
    )

    arg_parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='The TCP port to bind to (default: 8000)'
    )

    arg_parser.add_argument(
        '--reload',
        action='store_true',
        help='Auto-reload when code or static assets are modified.'
    )

    return arg_parser.parse_args()


def main():
    ''' Launch the server. '''

    args = get_args()
    config = get_config()
    logger = configure_logging(args.log_level)

    if args.reload and os.getenv('WATCHDOG_RUNNING') is None:
        print('Running with reloader...')
        start_watchdog()
    else:
        start_loop(config, args, logger)


def start_loop(config, args, logger):
    ''' Start event loop and and schedule high-level tasks. '''

    r.set_loop_type('asyncio')
    db_pool = AsyncRethinkPool(db_factory(config['database']))
    tracker = Tracker(db_pool)
    downloader = Downloader()
    rate_limiter = RateLimiter(downloader)
    crawl_manager = CrawlManager(db_pool, rate_limiter)
    server = Server(args.ip, args.port, db_pool, crawl_manager, tracker)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    rate_limiter.start()
    tracker.start()

    try:
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info('Caught SIGINT: trying graceful shutdown.')
            # Shut down different components in a specific order, e.g. crawls
            # need to finish downloading before the downloader stops.
            loop.run_until_complete(server.stop())
            loop.run_until_complete(rate_limiter.stop())
            loop.run_until_complete(crawl_manager.pause_all_jobs())
            loop.run_until_complete(tracker.stop())
            loop.run_until_complete(db_pool.close())
    except KeyboardInterrupt:
        logger.info('Caught 2nd SIGINT: shutting down immediately.')

    loop.close()
    logger.info('Server has stopped.')


def start_watchdog():
    ''' Start the watchdog (i.e. reloader). '''

    watchdog = ProcessWatchdog()
    watchdog.start_process()

    observer = Observer()
    observer.schedule(watchdog, get_path('starbelly'), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nReloader caught SIGINT: shutting down.')
        observer.stop()

    watchdog.join()
    observer.join()


if __name__ == '__main__':
    main()
