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
import logging
import ssl

import websockets
import websockets.exceptions

import protobuf.client_pb2
import protobuf.server_pb2


logging.basicConfig()
logger = logging.getLogger('sample_client')


def get_args():
    ''' Parse command line arguments. '''
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '-v',
        dest='verbosity',
        default='info',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        help='Set logging verbosity. Defaults to "info".'
    )

    parser.add_argument(
        'host',
        help='The name or IP of the starbelly host.'
    )

    subparsers = parser.add_subparsers(help='Actions', dest='action')
    list_parser = subparsers.add_parser('list', help='List crawl jobs.')
    sync_parser = subparsers.add_parser('sync',
        help='Sync crawl items from a job.')
    sync_parser.add_argument('job_id',
        help='Job ID as hex string.')
    sync_parser.add_argument('-d', '--delay', type=float, default=0,
        help='Delay between printing items (default 0).')
    sync_parser.add_argument('-t', '--token',
        help='To resume syncing, supply a sync token.')

    args = parser.parse_args()
    logger.setLevel(getattr(logging, args.verbosity.upper()))
    return args


async def list_jobs(args, socket):
    ''' List crawl jobs on the server. '''
    request = protobuf.client_pb2.Request()
    request.request_id = 1
    request.list_jobs.page.limit = 10
    request_data = request.SerializeToString()
    await socket.send(request_data)

    message_data = await socket.recv()
    message = protobuf.server_pb2.ServerMessage.FromString(message_data)
    response = message.response
    print('| {:20s} | {:32s} | {:19s} | {:5s} |'
        .format('Name', 'ID', 'Started', 'Items'))
    print('-' * 89)
    for job in response.list_jobs.jobs:
        print('| {:20s} | {:32s} | {:19s} | {:5d} |'.format(
            job.name[:20],
            binascii.hexlify(job.job_id).decode('ascii'),
            job.started_at[:19],
            job.item_count
        ))


async def main():
    ''' Main entry point. '''
    args = get_args()

    actions = {
        'list': list_jobs,
        'sync': sync_job,
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    url = 'wss://{}/ws/'.format(args.host)
    logger.info('Connecting to %s', url)

    socket = await websockets.connect(url, ssl=ssl_context)
    await actions[args.action](args, socket)
    if socket.open:
        await socket.close()


async def sync_job(args, socket):
    ''' Sync crawl items from a job. '''

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

    print('| {:50s} | {:5s} | {:10s} |'.format('URL', 'Cost', 'Size (KB)'))
    print('-' * 75)
    sync_token = None

    try:
        while True:
            message_data = await socket.recv()
            message = protobuf.server_pb2.ServerMessage.FromString(message_data)
            event_type = message.event.WhichOneof('Body')
            if event_type == 'subscription_closed':
                print('-- End of crawl results ---')
                break
            item = message.event.crawl_item
            print('| {:50s} | {:5.1f} | {:10.2f} |'.format(
                item.url[:50],
                item.cost,
                len(item.body) / 1024
            ))
            sync_token = item.sync_token
            await asyncio.sleep(args.delay)
    except asyncio.CancelledError:
        logger.info('Interrupted! To resume sync, use token: {}'
            .format(binascii.hexlify(sync_token).decode('ascii')))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main())
    try:
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        main_task.cancel()
        loop.run_until_complete(main_task)
    except websockets.exceptions.ConnectionClosed:
        logger.error('Server unexpectedly closed the connection.')
    loop.close()
