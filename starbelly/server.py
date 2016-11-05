import asyncio
import json
import logging
from urllib.parse import urlparse

import websockets

from .crawl import Crawl, CrawlItemsListener, CrawlStatsListener
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class Server:
    def __init__(self, host, port, frontier, downloader, rate_limiter):
        self._crawls = list()
        self._crawl_started = PubSub()
        self._downloader = downloader
        self._frontier = frontier
        self._host = host
        self._port = port
        self._rate_limiter = rate_limiter
        self._subscriptions = dict()

        self._handlers = {
            'start_crawl': self._start_crawl,
            'subscribe_crawl_items': self._subscribe_crawl_items,
            'subscribe_crawl_stats': self._subscribe_crawl_stats,
            'unsubscribe': self._unsubscribe,
        }

    async def handle_connection(self, websocket, path):
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
                args = request['args']
                args['socket'] = websocket

                response = {
                    'command_id': request['command_id'],
                    'type': 'response',
                }

                try:
                    response['data'] = await self._dispatch_command(
                        self._handlers[command],
                        args
                    )
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
        return websockets.serve(
            self.handle_connection,
            self._host,
            self._port
        )

    async def _dispatch_command(self, handler, args):
        if asyncio.iscoroutine(handler):
            return await handler(**args)
        else:
            return handler(**args)

    def _start_crawl(self, socket, seeds):
        seed_urls = list()

        for seed in seeds:
            url = seed['url']
            seed_urls.append(url)
            rate_limit = seed.get('rate_limit', None)

            if rate_limit is not None:
                parsed = urlparse(url)
                self._rate_limiter.set_domain_limit(parsed.hostname, rate_limit)

        crawl = Crawl(seed_urls, self._downloader, self._frontier)
        asyncio.ensure_future(crawl.run())
        self._crawls.append(crawl)
        self._crawl_started.publish(crawl)
        return {'crawl_id': crawl.id_}

    def _subscribe_crawl_items(self, socket, crawl_id, sync_token=None):
        crawl_id = int(crawl_id)
        matching_crawls = [c for c in self._crawls if c.id_ == crawl_id]

        if len(matching_crawls) != 1:
            msg = 'Crawl ID={} matched {} crawls! (expected 1)'
            raise ValueError(msg.format(crawl_id, len(matching_crawls)))

        crawl = matching_crawls[0]
        subscription = CrawlItemsListener(socket, crawl, sync_token)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _subscribe_crawl_stats(self, socket, min_interval=1):
        subscription = CrawlStatsListener(socket, min_interval)

        for crawl in self._crawls:
            subscription.add_crawl(crawl)

        def add_crawl(crawl):
            subscription.add_crawl(crawl)

        self._crawl_started.listen(add_crawl)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _unsubscribe(self, socket, subscription_id):
        subscription_id = int(subscription_id)
        self._subscriptions[subscription_id].cancel()
        return {'subscription_id': subscription_id}
