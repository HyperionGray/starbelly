import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import get_path
from .downloader import Downloader
from .frontier import Frontier
from .rate_limiter import DomainRateLimiter
from .server import Server


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
                    self._process.kill()
                    self._process.wait()
                    self._process = None
                except ProcessLookupError:
                    pass # The process already died.
            self.start_process()

    def start_process(self):
        ''' Start the subprocess. '''

        if self._process is not None:
            msg = 'Cannot start subprocess if it is already running.'
            raise RuntimeError(msg)

        time.sleep(1)
        args = [sys.executable, '-m', __package__] + sys.argv[1:]
        env = {'WATCHDOG_RUNNING': '1'}
        self._process = subprocess.Popen(args, env=env)


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
        # dest='log_level',
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
    logger = configure_logging(args.log_level)

    rate_limiter = DomainRateLimiter()
    frontier = Frontier(rate_limiter)
    downloader = Downloader(frontier)
    server = Server(args.ip, args.port, frontier, downloader, rate_limiter)

    if args.reload and os.getenv('WATCHDOG_RUNNING') is None:
        print('Running with reloader...')
        start_watchdog()
    else:
        logger.info('Starting server on {}:{}'.format(args.ip, args.port))
        start_server_loop(logger, server)


def start_server_loop(logger, server):
    ''' Start event loop and and schedule the server to run. '''

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info('Caught SIGINT... trying graceful shutdown.')
        remaining_tasks = asyncio.Task.all_tasks()
        for task in remaining_tasks:
            task.cancel()
        if len(remaining_tasks) > 0:
            loop.run_until_complete(asyncio.wait(remaining_tasks))

    loop.close()
    logger.info('Server has stopped.')


def start_watchdog():
    ''' Start the watchdog (i.e. reloader). '''

    watchdog = ProcessWatchdog()
    watchdog.start_process()

    observer = Observer()
    observer.schedule(watchdog, get_path('starbelly'), recursive=True)
    observer.schedule(watchdog, get_path('static'), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nReloader caught SIGINT: shutting down.')
        observer.stop()
    observer.join()


if __name__ == '__main__':
    main()
