import argparse
import logging
import os
import signal
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .bootstrap import Bootstrap
from .config import get_config, get_path


class ProcessWatchdog(FileSystemEventHandler):
    ''' Handle watchdog events by restarting a subprocess. '''

    def __init__(self):
        ''' Constructor. '''

        self._logger = logging.getLogger('watchdog')
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
        self._logger = logging.getLogger('reloader')
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
            self._watchdog, str(get_path('starbelly')), recursive=True)
        self._observer.start()

        while True:
            time.sleep(1)

    def shutdown(self, signum, _):
        ''' Exit the reloader. '''
        signame = signal.Signals(signum).name
        self._logger.info('Caught %s (shutting down)', signame)
        self._watchdog.terminate_process()
        self._observer.stop()
        self._observer.join()
        sys.exit(0)


def configure_logging(log_level, error_log):
    ''' Set default format and output stream for logging. '''
    log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    log_formatter = logging.Formatter(log_format, log_date_format)
    log_level = getattr(logging, log_level.upper())
    log_handler = logging.StreamHandler(sys.stderr)
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(log_level)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(log_level)
    logging.getLogger('watchdog').setLevel(logging.INFO)

    if error_log is not None:
        exc_handler = logging.FileHandler(error_log)
        exc_handler.setFormatter(log_formatter)
        exc_handler.setLevel(logging.ERROR)
        logger.addHandler(exc_handler)


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
    arg_parser.add_argument(
        '--error-log',
        help='Copy error logs to the specified file.'
    )
    return arg_parser.parse_args()


def main():
    ''' Set up watchdog or run starbelly. '''
    args = get_args()
    configure_logging(args.log_level, args.error_log)
    config = get_config()

    if args.reload and os.getenv('WATCHDOG_RUNNING') is None:
        reloader = Reloader()
        signal.signal(signal.SIGINT, reloader.shutdown)
        signal.signal(signal.SIGTERM, reloader.shutdown)
        reloader.run()
    else:
        bootstrap = Bootstrap(config, args)
        bootstrap.run()


if __name__ == '__main__':
    main()
