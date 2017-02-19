import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging
from urllib.parse import urlparse

import websockets

from . import raise_future_exception
from .crawl import CrawlJob
from .pubsub import PubSub
from .subscription import CrawlSyncSubscription, JobStatusSubscription


logger = logging.getLogger(__name__)


def custom_json(obj):
    '''
    Handles JSON serialization for objects that are not natively supported.
    '''
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    raise TypeError('Type {} cannot be serialized in JSON.'
        .format(obj.__class__.__name__))


class Server:
    ''' Handles websocket connections from clients and command dispatching. '''

    def __init__(self, host, port, downloader, rate_limiter, db_pool, tracker):
        ''' Constructor. '''
        self._clients = set()
        self._crawl_jobs = set()
        self._crawl_started = PubSub()
        self._db_pool = db_pool
        self._downloader = downloader
        self._host = host
        self._port = port
        self._rate_limiter = rate_limiter
        self._subscriptions = defaultdict(dict)
        self._tracker = tracker

        self._handlers = {
            'ping': self._ping,
            'start_crawl': self._start_crawl,
            'subscribe_crawl_sync': self._subscribe_crawl_sync,
            'subscribe_job_status': self._subscribe_job_status,
            'unsubscribe': self._unsubscribe,
        }

    async def handle_connection(self, websocket, path):
        ''' Handle an incoming connection. '''
        self._clients.add(websocket)
        logger.info('Websocket connection from {}:{}, path={}'.format(
            websocket.remote_address[0],
            websocket.remote_address[1],
            path
        ))

        while True:
            try:
                request = json.loads(await websocket.recv())
                logger.debug('Received command: {}'.format(request))
                command = request['command']
                args = request['args'] or {}
                args['socket'] = websocket

                response = {
                    'command_id': request['command_id'],
                    'type': 'response',
                }

                try:
                    data = await self._dispatch_command(
                        self._handlers[command],
                        args
                    )
                    if data is None:
                        data = {}
                    response['data'] = data
                    response['success'] = True
                except Exception as e:
                    if isinstance(e, KeyError):
                        msg = 'Invalid command: {}'
                        response['error'] = msg.format(command)
                    else:
                        response['error'] = str(e)
                    response['success'] = False
                    msg = 'Error while handling request: {}'
                    logger.exception(msg.format(request))
                await websocket.send(json.dumps(response, default=custom_json))
            except websockets.exceptions.ConnectionClosed:
                subscriptions = self._subscriptions[websocket].values()
                for subscription in subscriptions:
                    subscription.cancel()
                await asyncio.gather(*subscriptions, return_exceptions=True)
                del self._subscriptions[websocket]
                self._clients.remove(websocket)
                logger.info('Connection closed: {}:{}'.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                break
            except asyncio.CancelledError:
                msg = 'Connection handler canceled; closing socket {}:{}.'
                logger.info(msg.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                try:
                    await websocket.close()
                except websockets.exceptions.InvalidState:
                    pass

    def start(self):
        ''' Start the websocket server. Returns a coroutine. '''
        logger.info('Starting server on {}:{}'.format(self._host, self._port))
        return websockets.serve(self.handle_connection, self._host, self._port)

    async def stop(self):
        ''' Gracefully stop the websocket server. '''

        logger.info('Ending subscriptions...')
        to_gather = list()
        for socket, socket_subs in self._subscriptions.items():
            for subscription_id, subscription in socket_subs.items():
                subscription.cancel()
                to_gather.append(subscription)
        await asyncio.gather(*to_gather, return_exceptions=True)
        self._subscriptions.clear()
        logger.info('All subscriptions ended.')

        # Work on a copy of self._clients, because disconnects will modify the
        # set while we are iterating.
        logger.info('Closing websockets...')
        for client in list(self._clients):
            await client.close()
        logger.info('All websockets closed.')

    async def _dispatch_command(self, handler, args):
        ''' Dispatch a command received from a client. '''
        if asyncio.iscoroutinefunction(handler):
            response = await handler(**args)
        else:
            response = handler(**args)
        return response

    def _ping(self, socket):
        '''
        A client may ping the server to prevent connection timeout.

        This is a no-op.
        '''
        pass

    async def _start_crawl(self, socket, name, seeds):
        ''' Handle the start crawl command. '''
        logger.info('name={} seeds={}'.format(name, seeds))

        if name.strip() == '':
            url = urlparse(seeds[0])
            name = url.hostname
            if len(seeds) > 1:
                name += '& {} more'.format(len(seeds) - 1)

        crawl_job = CrawlJob(
            name,
            self._db_pool,
            self._downloader,
            self._rate_limiter,
            seeds
        )

        await crawl_job.save_job()
        crawl_task = crawl_job.start()
        self._crawl_jobs.add(crawl_job)
        self._crawl_started.publish(crawl_job)
        return {'crawl_id': crawl_job.id}

    def _subscribe_crawl_sync(self, socket, crawl_id, sync_token=None):
        ''' Handle the subscribe crawl items command. '''
        subscription = CrawlSyncSubscription(
            self._tracker, self._db_pool, socket, crawl_id, sync_token
        )
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        raise_future_exception(coro)
        return {'subscription_id': subscription.id}

    def _subscribe_job_status(self, socket, min_interval=1):
        ''' Handle the subscribe crawl status command. '''
        subscription = JobStatusSubscription(
            self._tracker, socket, min_interval
        )
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        raise_future_exception(coro)
        return {'subscription_id': subscription.id}

    async def _unsubscribe(self, socket, subscription_id):
        ''' Handle an unsubscribe command. '''
        task = self._subscriptions[socket][subscription_id]
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        del self._subscriptions[socket][subscription_id]
        return {'subscription_id': subscription_id}
