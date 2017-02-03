import asyncio
import json
import logging
from urllib.parse import urlparse

import websockets

from .crawl import CrawlJob, CrawlItemsListener, CrawlStatusListener
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class Server:
    ''' Handles websocket connections from clients and command dispatching. '''

    def __init__(self, host, port, downloader, rate_limiter):
        ''' Constructor. '''
        self._clients = set()
        self._crawl_jobs = set()
        self._crawl_started = PubSub()
        self._downloader = downloader
        self._host = host
        self._port = port
        self._rate_limiter = rate_limiter
        self._subscriptions = dict()

        self._handlers = {
            'ping': self._ping,
            'start_crawl': self._start_crawl,
            'subscribe_crawl_items': self._subscribe_crawl_items,
            'subscribe_crawl_status': self._subscribe_crawl_status,
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
                await websocket.send(json.dumps(response))
            except websockets.exceptions.ConnectionClosed:
                self._clients.remove(websocket)
                logger.info('Connection closed: {}:{}'.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                return
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

        for subscription in self._subscriptions.values():
            subscription.cancel()

        # Work on a copy of self._clients, because disconnects will modify the
        # set while we are iterating.
        logger.info('Closing websockets...')
        for client in list(self._clients):
            await client.close()
        logger.info('All websockets closed.')

    async def _dispatch_command(self, handler, args):
        ''' Dispatch a command received from a client. '''
        if asyncio.iscoroutine(handler):
            return await handler(**args)
        else:
            return handler(**args)

    def _ping(self, socket):
        '''
        A client may ping the server to prevent connection timeout.

        This is a no-op.
        '''
        pass

    def _start_crawl(self, socket, seeds):
        ''' Handle the start crawl command. '''
        seed_urls = list()

        for seed in seeds:
            url = seed['url']
            seed_urls.append(url)
            rate_limit = seed.get('rate_limit', None)

            if rate_limit is not None:
                parsed = urlparse(url)
                self._rate_limiter.set_domain_limit(parsed.hostname, rate_limit)

        crawl_job = CrawlJob(self._downloader, self._rate_limiter, seed_urls)
        crawl_task = crawl_job.start()
        self._crawl_jobs.add(crawl_job)
        self._crawl_started.publish(crawl_job)
        return {'crawl_id': crawl_job.id_}

    def _subscribe_crawl_items(self, socket, crawl_id, sync_token=None):
        ''' Handle the subscribe crawl items command. '''
        crawl_id = int(crawl_id)
        matching_crawls = [c for c in self._crawl_jobs if c.id_ == crawl_id]

        if len(matching_crawls) != 1:
            msg = 'Crawl ID={} matched {} crawls! (expected 1)'
            raise ValueError(msg.format(crawl_id, len(matching_crawls)))

        crawl = matching_crawls[0]
        subscription = CrawlItemsListener(socket, crawl, sync_token)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _subscribe_crawl_status(self, socket, min_interval=1):
        ''' Handle the subscribe crawl status command. '''
        subscription = CrawlStatusListener(socket, min_interval)

        for crawl in self._crawl_jobs:
            subscription.add_crawl(crawl)

        def add_crawl(crawl):
            subscription.add_crawl(crawl)

        self._crawl_started.listen(add_crawl)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _unsubscribe(self, socket, subscription_id):
        ''' Handle an unsubscribe command. '''
        subscription_id = int(subscription_id)
        self._subscriptions[subscription_id].cancel()
        return {'subscription_id': subscription_id}
