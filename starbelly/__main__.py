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

from . import cancel_futures, daemon_task, get_path
from .db import AsyncRethinkPool
from .config import get_config
from .crawl import CrawlManager
from .downloader import Downloader
from .policy import PolicyManager
from .rate_limiter import RateLimiter
from .robots import RobotsTxtManager
from .server import Server
from .subscription import SubscriptionManager
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
        file = os.path.basename(path)
        descr = '{} was {}'.format(event.src_path, event.event_type)

        if (file.endswith('.py') and not file.startswith('test_')) or \
            file.endswith('.ini'):
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


def print_tasks(logger):
    ''' this needs to be separate from monitor_tasks to prevent holding resources open '''
    from collections import Counter
    tasks = asyncio.Task.all_tasks()
    task_names = list()

    for task in tasks:
        task_name = task._coro.__qualname__
        if task._source_traceback:
            frame = task._source_traceback[-1]
            if '/starbelly/__init__.py' in frame[0] or '/asyncio/' in frame[0]:
                frame = task._source_traceback[-2]
            task_name += ' %s:%s' % (frame[0], frame[1])
        task_names.append(task_name)

    counter = Counter(task_names)
    task_str = 'TASK MONITOR:\ntotal=%d\n'
    task_args = [len(tasks)]

    for task_name, count in counter.most_common(10):
        task_str += '%d\t%s\n'
        task_args.extend([count, task_name])
    logger.error(task_str, *task_args)


async def monitor_tasks(logger):
    while True:
        print_tasks(logger)
        await asyncio.sleep(15)


class Starbelly:
    ''' Main class for bootstrapping the crawler. '''

    def __init__(self, config, args, logger):
        ''' Constructor. '''
        self._args = args
        self._config = config
        self._logger = logger
        self._main_task = None
        self._quit_count = 0

    async def run(self):
        ''' The main task. '''
        db_pool = AsyncRethinkPool(self._db_factory())
        tracker = Tracker(db_pool)
        policy_manager = PolicyManager(db_pool)
        rate_limiter = RateLimiter(db_pool)
        downloader = Downloader(rate_limiter)
        robots_txt_manager = RobotsTxtManager(db_pool, rate_limiter)
        crawl_manager = CrawlManager(db_pool, rate_limiter, downloader,
            robots_txt_manager)
        subscription_manager = SubscriptionManager(db_pool)
        server = Server(
            self._args.ip,
            self._args.port,
            db_pool,
            crawl_manager,
            subscription_manager,
            tracker,
            rate_limiter,
            policy_manager
        )

        try:
            await crawl_manager.startup_check()
            await rate_limiter.initialize()
            downloader.start()
            tracker_task = daemon_task(tracker.run())
            server_task = daemon_task(server.run())
            # task_monitor = daemon_task(monitor_tasks(self._logger)) #TODO

            # This main task idles after startup: it only supervises other
            # tasks.
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Components must be shut down in the proper order.
            await subscription_manager.close_all()
            await cancel_futures(server_task)
            await crawl_manager.pause_all_jobs()
            await downloader.stop()
            await cancel_futures(tracker_task)
            await db_pool.close()
            # await cancel_futures(task_monitor) #TODO


    def shutdown(self, signum, frame):
        ''' Kill the main task. '''

        loop = asyncio.get_event_loop()
        signame = signal.Signals(signum).name

        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self._quit_count += 1
            if self._quit_count == 1:
                self._logger.warning(
                    'Caught %s: trying graceful shutdown.', signame)
                self._main_task.cancel()
            elif self._quit_count == 2:
                self._logger.warning(
                    'Caught 2nd %s: shutting down immediately.', signame)
                sys.exit(1)

    def start(self):
        ''' Start the event loop. '''
        self._logger.info('Starbelly is starting...')
        r.set_loop_type('asyncio')
        loop = asyncio.get_event_loop()
        self._main_task = asyncio.ensure_future(self.run())
        loop.run_until_complete(self._main_task)

        # Check if any tasks weren't properly cleaned up.
        tasks = [t for t in asyncio.Task.all_tasks() if not t.done()]
        if len(tasks) > 0:
            self._logger.error('There are %d unfinished tasks: %r',
                len(tasks), tasks)

        loop.close()
        self._logger.info('Starbelly has stopped.')

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
        starbelly.start()


if __name__ == '__main__':
    main()
