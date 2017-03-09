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

from . import cancel_futures, get_path, raise_future_exception
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

        self._logger = logging.getLogger('starbelly.watchdog')
        self._process = None

    def dispatch(self, event):
        ''' Restart the subprocess if a source/config file changed. '''

        path = event.src_path
        descr = '{} was {}'.format(event.src_path, event.event_type)

        if path.endswith('.py') or path.endswith('.ini'):
            self._logger.info('%s (Reloading)', descr)
            self.terminate_process()
            self.start_process()

    def join(self):
        ''' Wait for subprocess to exit. '''
        if self._process is not None:
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

    def terminate_process(self):
        ''' Terminate the subprocess. '''
        if self._process is not None:
            try:
                self._process.send_signal(signal.SIGTERM)
                self._process.wait()
                self._process = None
            except ProcessLookupError:
                pass # The process already died.


class Reloader:
    ''' Reloads the subprocess when a source file is modified. '''
    def __init__(self):
        ''' Constructor. '''
        self._logger = logging.getLogger('starbelly.reloader')
        self._observer = None
        self._running = False
        self._watchdog = None

    def run(self):
        ''' Run the reloader. '''

        self._logger.info('Running with reloader...')
        self._watchdog = ProcessWatchdog()
        self._watchdog.start_process()

        self._observer = Observer()
        self._observer.schedule(
            self._watchdog, get_path('starbelly'), recursive=True)
        self._observer.start()

        while True:
            time.sleep(1)

    def shutdown(self, signum, frame):
        ''' Exit the reloader. '''
        signame = signal.Signals(signum).name
        self._logger.info('Caught %s (shutting down)', signame)
        self._watchdog.terminate_process()
        self._observer.stop()
        self._observer.join()
        sys.exit(0)


class Starbelly:
    ''' Main class for bootstrapping the crawler. '''

    def __init__(self, config, args, logger):
        ''' Constructor. '''
        self._args = args
        self._crawl_manager = None
        self._config = config
        self._db_pool = None
        self._downloader = None
        self._idle_task = None
        self._logger = logger
        self._quit_count = 0
        self._rate_limiter = None
        self._server = None
        self._tracker = None

    def run(self):
        ''' Run the event loop. '''

        self._logger.info('Starbelly is starting...')
        r.set_loop_type('asyncio')
        self._db_pool = AsyncRethinkPool(self._db_factory())
        self._tracker = Tracker(self._db_pool)
        self._downloader = Downloader()
        self._rate_limiter = RateLimiter(self._downloader)
        self._crawl_manager = CrawlManager(self._db_pool, self._rate_limiter)

        self._server = Server(
            self._args.ip,
            self._args.port,
            self._db_pool,
            self._crawl_manager,
            self._tracker
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._crawl_manager.startup_check())
        self._rate_limiter.start()
        self._tracker.start()
        loop.run_until_complete(self._server.start())
        self._idle_task = asyncio.ensure_future(self._idle())

        try:
            loop.run_until_complete(self._idle_task)
        except asyncio.CancelledError:
            # Components must be shut down in the proper order.
            loop.run_until_complete(self._server.stop())
            loop.run_until_complete(self._rate_limiter.stop())
            loop.run_until_complete(self._crawl_manager.pause_all_jobs())
            loop.run_until_complete(self._tracker.stop())
            loop.run_until_complete(self._db_pool.close())

            tasks = [t for t in asyncio.Task.all_tasks() if not t.done()]
            if len(tasks) > 0:
                self._logger.error('There are %d unfinished tasks: %r',
                    len(tasks), tasks)
            for t in tasks:
                if hasattr(t, '_meh'):
                    import traceback
                    traceback.print_tb(t._meh)

        loop.close()
        self._logger.info('Starbelly has stopped.')

    def shutdown(self, signum, frame):
        ''' Kill the main task. '''

        loop = asyncio.get_event_loop()
        signame = signal.Signals(signum).name

        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self._quit_count += 1
            if self._quit_count == 1:
                self._logger.warning(
                    'Caught %s: trying graceful shutdown.', signame)
                self._idle_task.cancel()
            elif self._quit_count == 2:
                self._logger.warning(
                    'Caught 2nd %s: shutting down immediately.', signame)
                sys.exit(1)

    def _db_factory(self):
        ''' Returns a function that connects to the database. '''

        db_config = self._config['database']

        def db_connect():
            return r.connect(
                host=db_config['host'],
                port=db_config['port'],
                db=db_config['db'],
                user=db_config['user'],
                password=db_config['password'],
            )

        return db_connect

    async def _idle(self):
        '''
        A dummy coroutine.

        To exit the event loop, it is faster to cancel a process in that loop
        than it is to call loop.stop(). So we use this dummy coroutine to stop
        the entire loop.
        '''
        await asyncio.Event().wait()


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


def get_args():
    ''' Parse command line arguments. '''

    arg_parser = argparse.ArgumentParser(description='Starbelly')

    arg_parser.add_argument(
        '--log-level',
        default='warning',
        metavar='LEVEL',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Set logging verbosity (default: warning)'
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
    ''' Set up watchdog or run starbelly. '''

    args = get_args()
    config = get_config()
    logger = configure_logging(args.log_level)

    if args.reload and os.getenv('WATCHDOG_RUNNING') is None:
        reloader = Reloader()
        signal.signal(signal.SIGINT, reloader.shutdown)
        signal.signal(signal.SIGTERM, reloader.shutdown)
        reloader.run()
    else:
        starbelly = Starbelly(config, args, logger)
        signal.signal(signal.SIGINT, starbelly.shutdown)
        signal.signal(signal.SIGTERM, starbelly.shutdown)
        starbelly.run()


if __name__ == '__main__':
    main()
