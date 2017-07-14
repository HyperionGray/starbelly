'''
A very minimal client that only demonstrates some of the basic features of the
Starbelly API. This is not intended for production use.

This script uses asyncio only because starbelly already has the async websockets
library as a dependency and I didn't want to add a dependency on a synchronous
websockets library just for this sample client. This isn't a good example of
async programming!
'''

import argparse
import asyncio
import binascii
import gzip
import logging
import os
import signal
import ssl
import sys
import termios
import textwrap
import traceback
import tty
from uuid import UUID

import dateutil.parser
from humanize import naturalsize
import websockets
import websockets.exceptions

import protobuf.client_pb2
import protobuf.shared_pb2
import protobuf.server_pb2


logging.basicConfig()
logger = logging.getLogger('sample_client')
DATE_FMT = '%Y-%m-%d %H:%I:%S'


def async_excepthook(type_, exc, tb):
    cause_exc = None
    cause_str = None

    if exc.__cause__ is not None:
        cause_exc = exc.__cause__
        cause_str = 'The above exception was the direct cause ' \
                    'of the following exception:'
    elif exc.__context__ is not None and not exc.__suppress_context__:
        cause_exc = exc.__context__
        cause_str = 'During handling of the above exception, ' \
                    'another exception occurred:'

    if cause_exc:
        async_excepthook(type(cause_exc), cause_exc, cause_exc.__traceback__)

    if cause_str:
        print('\n{}\n'.format(cause_str))

    print('Async Traceback (most recent call last):')
    for frame in traceback.extract_tb(tb):
        head, tail = os.path.split(frame.filename)
        if (head.endswith('asyncio') or tail == 'traceback.py') and \
            frame.name.startswith('_'):
            print('  ...')
            continue
        print('  File "{}", line {}, in {}'
            .format(frame.filename, frame.lineno, frame.name))
        print('    {}'.format(frame.line))
    print('{}: {}'.format(type_.__name__, exc))


async def delete_job(args, socket):
    ''' Delete a job. '''
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.delete_job.job_id = UUID(args.job_id).bytes
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    if message.response.is_success:
        print('Job deleted.')
    else:
        print('Failed to delete job: {}'.format(message.response.error_message))


def get_args():
    ''' Parse command line arguments. '''
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '-v',
        dest='verbosity',
        default='warning',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Set logging verbosity. Defaults to "warning".'
    )

    parser.add_argument(
        'host',
        help='The name or IP of the starbelly host.'
    )

    subparsers = parser.add_subparsers(help='Actions', dest='action')
    subparsers.required = True
    crawl_parser = subparsers.add_parser('crawl', help='Start a crawl.')
    crawl_parser.add_argument('-n', '--name',
        help='Assign a name to this crawl.')
    crawl_parser.add_argument('policy',
        help='A policy ID.')
    crawl_parser.add_argument('seed',
        nargs='+',
        help='One or more seeds.')
    delete_parser = subparsers.add_parser('delete', help='Delete a crawl job.')
    delete_parser.add_argument('job_id', help='Job ID as hex string.')
    list_parser = subparsers.add_parser('list', help='List crawl jobs.')
    list_parser.add_argument('--started-after', metavar='DATETIME',
        help='Show jobs started after given datetime (ISO-8601).')
    list_parser.add_argument('--tag',
        help='Filter by tag.')
    profiler_parser = subparsers.add_parser('profile',
        help='Run CPU profiler.')
    profiler_parser.add_argument('--duration', type=float, default=3.0,
        help='Amount of time to run profile (default 3.0).')
    profiler_parser.add_argument('--sort', default='tottime',
        help='Field to sort profile data on (default "tottime").')
    profiler_parser.add_argument('--top', type=int, default=20,
        help='How many results to display (default 20).')
    rate_limit_parser = subparsers.add_parser('rates',
        help='Show rate limits.')
    rate_limit_parser = subparsers.add_parser('set_rate',
        help='Set a rate limit.')
    rate_limit_parser.add_argument('delay', type=float,
        help='Delay in seconds. (-1 to clear)')
    rate_limit_parser.add_argument('domain',
        nargs='?',
        help='Domain name to rate limit. (If omitted, modifies global limit.)')
    resource_parser = subparsers.add_parser('resources',
        help='Show resource usage.')
    resource_parser.add_argument('--history', type=int, default=1,
        help='The number of historical data points to retrieve (default 1).')
    rate_limit_parser = subparsers.add_parser('set_rate',
        help='Set a rate limit.')
    rate_limit_parser.add_argument('delay', type=float,
        help='Delay in seconds. (-1 to clear)')
    rate_limit_parser.add_argument('domain',
        nargs='?',
        help='Domain name to rate limit. (If omitted, modifies global limit.)')
    show_parser = subparsers.add_parser('show', help='Display a crawl job.')
    show_parser.add_argument('job_id', help='Job ID as hex string.')
    show_parser.add_argument('--items', action='store_true',
        help='Show some of the job\'s items.')
    show_parser.add_argument('--errors', action='store_true',
        help='Show some of the job\'s HTTP errors.')
    show_parser.add_argument('--exceptions', action='store_true',
        help='Show some of the job\'s exceptions.')
    sync_parser = subparsers.add_parser('sync',
        help='Sync items from a job.')
    sync_parser.add_argument('job_id', help='Job ID as hex string.')
    sync_parser.add_argument('-d', '--delay', type=float, default=0,
        help='Delay between printing items (default 0).')
    sync_parser.add_argument('-t', '--token',
        help='To resume syncing, supply a sync token.')
    task_parser = subparsers.add_parser('tasks', help='List async tasks.')
    task_parser.add_argument('--period', type=float, default=3.0,
        help='Seconds between updates (default 3.0).')
    task_parser.add_argument('--top', type=int, default=20,
        help='How many tasks to display (default 20).')

    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.verbosity.upper()))
    return args


def getch():
    '''
    Thanks, stackoverflow.
    http://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user
    '''
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


async def get_rates(args, socket):
    ''' Show rate limits. '''
    current_page = 0
    action = 'm'

    print('| {:40s} | {:5} |'.format('Name', 'Delay'))
    print('-' * 52)

    while action == 'm':
        current_page += 1
        limit = 10
        offset = (current_page - 1) * limit

        request = protobuf.client_pb2.Request()
        request.request_id = 1
        request.get_rate_limits.page.limit = limit
        request.get_rate_limits.page.offset = offset
        request_data = request.SerializeToString()
        await socket.send(request_data)

        message_data = await socket.recv()
        message = protobuf.server_pb2.ServerMessage.FromString(message_data)
        response = message.response
        for rate_limit in response.list_rate_limits.rate_limits:
            name = rate_limit.name
            print('| {:40s} | {:5.3f} |'.format(
                rate_limit.name[:40],
                rate_limit.delay
            ))
        start = offset + 1
        end = offset + len(response.list_rate_limits.rate_limits)
        total = response.list_rate_limits.total
        if end == total:
            print('Showing {}-{} of {}.'.format(start, end, total))
            action = 'q'
        else:
            print('Showing {}-{} of {}. [m]ore or [q]uit?'
                .format(start, end, total))
            action = await asyncio.get_event_loop().run_in_executor(None, getch)    #


async def get_resources(args, socket):
    ''' Display resource consumption. '''

    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.subscribe_resource_monitor.history = args.history
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    response = message.response
    if not response.is_success:
        raise Exception('Server failure: ' + response.error_message)

    while True:
        try:
            message_data = await socket.recv()
            message = protobuf.server_pb2.ServerMessage.FromString(message_data)
            event_type = message.event.WhichOneof('Body')
            if event_type == 'subscription_closed':
                break
            frame = message.event.resource_frame
            print('-- Resource Frame --')
            cpus = ' '.join(['{:3.1f}%'
                .format(cpu.usage) for cpu in frame.cpus])
            print('CPUs: {}'.format(cpus))
            memory = frame.memory
            print('Memory: used={:8s} total={:8s} ({:3.1f}%)'.format(
                naturalsize(memory.used), naturalsize(memory.total),
                100 * memory.used / memory.total))
            print('Disks:')
            for disk in frame.disks:
                print('    {:20s} {:3.1f}% ({:s} free)'.format(disk.mount,
                    100 * disk.used / disk.total,
                    naturalsize(disk.total - disk.used)))
            print('Networks:')
            for network in frame.networks:
                print('    {:10s} sent={:8s} recv={:8s}'.format(network.name,
                    naturalsize(network.sent), naturalsize(network.received)))
            if len(frame.crawls) == 0:
                print('Crawls: (none)')
            else:
                print('Crawls:')
            for crawl in frame.crawls:
                print('    {:8s} frontier={:<9,d} pending={:<9,d}'
                      ' extraction={:<9,d}'
                    .format(binascii.hexlify(crawl.job_id[:4]).decode('ascii'), crawl.frontier,
                    crawl.pending, crawl.extraction))
            print('Rate Limiter: {:9,d}'.format(frame.rate_limiter.count))
            print('Downloader:   {:9,d}'.format(frame.downloader.count))
        except asyncio.CancelledError:
            break


async def list_jobs(args, socket):
    ''' List crawl jobs on the server. '''
    current_page = 0
    action = 'm'

    print('| {:20s} | {:32s} | {:9s} | {:19s} | {:5s} |'
        .format('Name', 'ID', 'Status', 'Started', 'Items'))
    print('-' * 101)

    while action == 'm':
        current_page += 1
        limit = 10
        offset = (current_page - 1) * limit

        request = protobuf.client_pb2.Request()
        request.request_id = 1
        request.list_jobs.page.limit = limit
        request.list_jobs.page.offset = offset
        if args.started_after is not None:
            try:
                started_after = dateutil.parser.parse(args.started_after)
            except:
                logger.error('Invalid date "%s" (must be YYYY-MM-DDTHH:mm:ssZ)',
                    args.started_after)
            request.list_jobs.started_after = started_after.isoformat()
        if args.tag is not None:
            request.list_jobs.tag = args.tag
        request_data = request.SerializeToString()
        await socket.send(request_data)

        message_data = await socket.recv()
        message = protobuf.server_pb2.ServerMessage.FromString(message_data)
        response = message.response
        for job in response.list_jobs.jobs:
            run_state = protobuf.shared_pb2.JobRunState.Name(job.run_state)
            print('| {:20s} | {:32s} | {:9s} | {:19s} | {:5d} |'.format(
                job.name[:20],
                binascii.hexlify(job.job_id).decode('ascii'),
                run_state,
                job.started_at[:19],
                job.item_count
            ))
        end = offset + len(response.list_jobs.jobs)
        start = offset + 1 if end > 0 else 0
        total = response.list_jobs.total
        if end == total:
            print('Showing {}-{} of {}.'.format(start, end, total))
            action = 'q'
        else:
            print('Showing {}-{} of {}. [m]ore or [q]uit?'
                .format(start, end, total))
            action = await asyncio.get_event_loop().run_in_executor(None, getch)


async def main():
    ''' Main entry point. '''
    args = get_args()

    actions = {
        'crawl': start_crawl,
        'delete': delete_job,
        'list': list_jobs,
        'profile': profile,
        'rates': get_rates,
        'resources': get_resources,
        'set_rate': set_rate,
        'show': show_job,
        'sync': sync_job,
        'tasks': tasks,
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    url = 'wss://{}/ws/'.format(args.host)
    logger.info('Connecting to %s', url)
    socket = await websockets.connect(url, ssl=ssl_context, max_queue=1)

    try:
        await actions[args.action](args, socket)
    except websockets.exceptions.ConnectionClosed as cc:
        # Nothing we can do here except exit.
        logger.error('Connection unexpectedly closed: code=%s reason="%s"',
            cc.code, cc.reason)
    finally:
        try:
            await socket.close(4000, 'sample_client process is complete')
        except:
            pass


async def profile(args, socket):
    ''' Run the CPU profiler. '''
    # Map client sort keys to server sort keys.
    sort_keys = {
        'calls': 'calls',
        'nrcalls': 'non_recursive_calls',
        'tottime': 'total_time',
        'cumtime': 'cumulative_time',
        'file': 'file',
        'function': 'function',
        'line': 'line_number',
    }
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.performance_profile.duration = args.duration

    try:
        request.performance_profile.sort_by = sort_keys[args.sort]
    except KeyError:
        logger.error('Invalid sort key: {}'.format(args.sort))
        return

    request.performance_profile.top_n = args.top
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)

    if not message.response.is_success:
        print('Server error: {}'.format(message.response.error_message))
        return

    profile = message.response.performance_profile
    print('Total Calls: {:d}\nTotal Time: {:0.3f}\n'
        .format(profile.total_calls, profile.total_time))
    print('{:8s} {:8s} {:8s} {:8s} {}'
        .format('calls', 'nrcalls', 'tottime', 'cumtime', 'file function:line_number'))
    for function in profile.functions:
        location = '{} {}:{}'.format(
            function.file, function.function, function.line_number)
        print('{:<8d} {:<8d} {:<8.3f} {:<8.3f} {:s}'
            .format(function.calls, function.non_recursive_calls,
            function.total_time,
                    function.cumulative_time, location))


async def set_rate(args, socket):
    ''' Set a rate limit. '''
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    rate_limit = request.set_rate_limit.rate_limit
    if args.domain is not None:
        rate_limit.domain = args.domain
    if args.delay >= 0:
        rate_limit.delay = args.delay
    if not (rate_limit.HasField('domain') or rate_limit.HasField('delay')):
        logger.error('Delay must be >= 0 if domain not specified.')
        return
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    if message.response.is_success:
        domain = '(global)' if args.domain is None else args.domain
        delay = args.delay if args.delay >= 0 else '(deleted)'
        print('Set rate limit: {}={}'.format(domain, delay))
    else:
        print('Failed to set rate limit: {}'
            .format(message.response.error_message))


async def show_job(args, socket):
    ''' Show a single job. '''
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.get_job.job_id = UUID(args.job_id).bytes
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    job = message.response.job
    run_state = protobuf.shared_pb2.JobRunState.Name(job.run_state)
    started_at = dateutil.parser.parse(job.started_at).strftime(DATE_FMT)
    if job.HasField('completed_at'):
        completed_at = dateutil.parser.parse(job.completed_at).strftime(DATE_FMT)
    else:
        completed_at = 'N/A'
    print('ID:           {}'.format(UUID(bytes=job.job_id)))
    print('Name:         {}'.format(job.name))
    print('Run State:    {}'.format(run_state))
    print('Started At:   {}'.format(started_at))
    print('Completed At: {}'.format(completed_at))
    print('Items Count:  success={}, error={}, exception={} (total={})'.format(
        job.http_success_count, job.http_error_count, job.exception_count,
        job.item_count
    ))

    print('Seeds:')
    for seed in job.seeds:
        print(' * {}'.format(seed))

    if len(job.http_status_counts) > 0:
        print('HTTP Status Codes:')
        for code, count in job.http_status_counts.items():
            print(' * {:d}: {:d}'.format(code, count))

    if args.items or args.errors or args.exceptions:
        request = protobuf.client_pb2.Request()
        request.request_id = 1
        request.get_job_items.job_id = UUID(args.job_id).bytes
        request.get_job_items.include_success = args.items
        request.get_job_items.include_error = args.errors
        request.get_job_items.include_exception = args.exceptions
        request_data = request.SerializeToString()
        await socket.send(request_data)

        message_data = await socket.recv()
        message = protobuf.server_pb2.ServerMessage.FromString(message_data)
        items = message.response.list_items.items
        total = message.response.list_items.total

        if len(items) == 0:
            print('No items matching the requested flags'
                ' (success={} errors={} exceptions={})'
                .format(args.items, args.errors, args.exceptions))
        else:
            print('\nShowing {} of {} matching items (success={} errors={}'
                ' exceptions={})'.format(len(items), total, args.items,
                args.errors, args.exceptions))
            for item in items:
                started_at = dateutil.parser.parse(item.started_at) \
                    .strftime(DATE_FMT)
                completed_at = dateutil.parser.parse(item.completed_at) \
                    .strftime(DATE_FMT)
                if item.HasField('body'):
                    if item.is_body_compressed:
                        body = gzip.decompress(item.body)
                    else:
                        body = item.body
                else:
                    body = None
                print('\n' + '=' * 60)
                print('{}'.format(item.url))
                print('Status: {}\nCost: {}\nContent-Type: {}'.format(
                    item.status_code, item.cost, item.content_type))
                print('Started: {}\nCompleted: {}\nDuration: {}s '.format(
                    started_at, completed_at, item.duration))
                if body is not None:
                    print('Body: {}'.format(repr(body)))
                if item.HasField('exception'):
                    print('Exception: \n{}'.format(
                        textwrap.indent(item.exception, prefix='> ')))


async def start_crawl(args, socket):
    ''' Start a new crawl. '''
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.set_job.run_state = protobuf.shared_pb2.RUNNING
    request.set_job.policy_id = UUID(args.policy).bytes
    if args.name:
        request.set_job.name = args.name
    for seed in args.seed:
        request.set_job.seeds.append(seed)
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    if message.response.is_success:
        job_id = binascii.hexlify(message.response.new_job.job_id)
        print('Started job: {}'.format(job_id.decode('ascii')))
    else:
        print('Failed to start job: {}'.format(message.response.error_message))


async def sync_job(args, socket):
    ''' Sync items from a job. '''

    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.subscribe_job_sync.job_id = binascii.unhexlify(args.job_id)
    if args.token is not None:
        request.subscribe_job_sync.sync_token = binascii.unhexlify(args.token)
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    response = message.response
    if not response.is_success:
        raise Exception('Server failure: ' + response.error_message)
    else:
        subscription_id = response.new_subscription.subscription_id

    print('| {:50s} | {:5s} | {:4s} | {:10s} |'
        .format('URL', 'Cost', 'Code', 'Size (KB)'))
    print('-' * 82)
    sync_token = None

    try:
        while True:
            message_data = await socket.recv()
            message = protobuf.server_pb2.ServerMessage.FromString(message_data)
            event_type = message.event.WhichOneof('Body')
            if event_type == 'subscription_closed':
                print('-- End of crawl results ---')
                break
            item = message.event.sync_item.item
            if item.HasField('body'):
                body_len = '{:10.2f}'.format(len(item.body) / 1024)
            else:
                body_len = 'N/A'
            if item.HasField('exception'):
                status = 'exc'
            else:
                status = str(item.status_code)

            print('| {:50s} | {:5.1f} | {:>4s} | {:>10s} |'.format(
                item.url[:50],
                item.cost,
                status,
                body_len
            ))
            # Update sync_token _after_ successfully processing the item.
            sync_token = message.event.sync_item.token
            await asyncio.sleep(args.delay)
    except asyncio.CancelledError:
        print('Interrupted! Cancelling subscription...'
             ' (this may take a few seconds)')
        request = protobuf.client_pb2.Request()
        request.request_id = 2
        request.unsubscribe.subscription_id = subscription_id
        request_data = request.SerializeToString()
        await socket.send(request_data)

        # Keep reading events until we see the subscription has ended.
        while True:
            message_data = await socket.recv()
            message = protobuf.server_pb2.ServerMessage.FromString(message_data)
            if message.WhichOneof('MessageType') == 'response':
                break
        if not message.response.is_success:
            logger.error('Could not unsubscribe: %s', response.error_message)
        token = binascii.hexlify(sync_token).decode('ascii')
        print('To resume sync, use token: {}'.format(token))
        raise


async def tasks(args, socket):
    ''' Display asyncio tasks. '''

    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.subscribe_task_monitor.period = args.period
    request.subscribe_task_monitor.top_n = args.top
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    response = message.response
    if not response.is_success:
        raise Exception('Server failure: ' + response.error_message)

    while True:
        try:
            message_data = await socket.recv()
            message = protobuf.server_pb2.ServerMessage.FromString(message_data)
            event_type = message.event.WhichOneof('Body')
            if event_type == 'subscription_closed':
                break
            task_monitor = message.event.task_monitor
            print('-- {} Tasks --'.format(task_monitor.count))
            for task in task_monitor.tasks:
                print('    {:5d} {}'.format(task.count, task.name))
        except asyncio.CancelledError:
            break


if __name__ == '__main__':
    sys.excepthook = async_excepthook
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main())
    signal.signal(signal.SIGINT, lambda sig, frame: main_task.cancel())
    loop.run_until_complete(main_task)
    loop.close()
