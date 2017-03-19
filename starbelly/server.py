import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging
from urllib.parse import urlparse

import websockets

from . import cancel_futures, daemon_task
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

    def __init__(self, host, port, db_pool, crawl_manager, tracker):
        ''' Constructor. '''
        self._clients = set()
        self._crawl_manager = crawl_manager
        self._db_pool = db_pool
        self._host = host
        self._port = port
        self._subscriptions = defaultdict(dict)
        self._tracker = tracker
        self._websocket_server = None

        self._handlers = {
            'ping': self._ping,
            'job.cancel': self._cancel_job,
            'job.pause': self._pause_job,
            'job.resume': self._resume_job,
            'job.start': self._start_job,
            'job.subscribe.status': self._subscribe_job_status,
            'job.subscribe.sync': self._subscribe_crawl_sync,
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
                await cancel_futures(*subscriptions)
                del self._subscriptions[websocket]
                self._clients.remove(websocket)
                logger.info('Connection closed: {}:{}'.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                break
            except asyncio.CancelledError:
                try:
                    await websocket.close()
                except websocket.exceptions.InvalidState:
                    pass

    async def run(self):
        ''' Run the websocket server. '''
        try:
            logger.info('Starting server on {}:{}'.format(self._host, self._port))
            self._websocket_server = await websockets.serve(self.handle_connection,
                self._host, self._port)

            # This task idles: it's only purpose is to supervise child tasks.
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info('Ending subscriptions...')
            sub_tasks = list()
            for socket, socket_subs in self._subscriptions.items():
                for subscription_id, subscription in socket_subs.items():
                    sub_tasks.append(subscription)
            await cancel_futures(*sub_tasks)
            logger.info('All subscriptions ended.')

            logger.info('Closing websockets...')
            self._websocket_server.close()
            await self._websocket_server.wait_closed()
            logger.info('All websockets closed.')

    async def _cancel_job(self, socket, job_id):
        ''' Cancel a running or paused job. '''
        await self._crawl_manager.cancel_job(job_id)

    async def _dispatch_command(self, handler, args):
        ''' Dispatch a command received from a client. '''
        if asyncio.iscoroutinefunction(handler):
            response = await handler(**args)
        else:
            response = handler(**args)
        return response

    async def _pause_job(self, socket, job_id):
        ''' Pause a job. '''
        await self._crawl_manager.pause_job(job_id)

    def _ping(self, socket):
        '''
        A client may ping the server to prevent connection timeout.

        This is a no-op.
        '''
        pass

    async def _resume_job(self, socket, job_id):
        ''' Resume a paused job. '''
        await self._crawl_manager.resume_job(job_id)

    async def _start_job(self, socket, name, seeds):
        ''' Handle the start crawl command. '''
        if name.strip() == '':
            url = urlparse(seeds[0])
            name = url.hostname
            if len(seeds) > 1:
                name += '& {} more'.format(len(seeds) - 1)

        job_id = await self._crawl_manager.start_job(name, seeds)
        return {'job_id': job_id}

    def _subscribe_crawl_sync(self, socket, job_id, sync_token=None):
        ''' Handle the subscribe crawl items command. '''
        subscription = CrawlSyncSubscription(
            self._tracker, self._db_pool, socket, job_id, sync_token
        )
        coro = daemon_task(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        return {'subscription_id': subscription.id}

    def _subscribe_job_status(self, socket, min_interval=1):
        ''' Handle the subscribe crawl status command. '''
        subscription = JobStatusSubscription(
            self._tracker, socket, min_interval
        )
        coro = daemon_task(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        return {'subscription_id': subscription.id}

    async def _unsubscribe(self, socket, subscription_id):
        ''' Handle an unsubscribe command. '''
        task = self._subscriptions[socket][subscription_id]
        await cancel_futures(task)
        del self._subscriptions[socket][subscription_id]
        return {'subscription_id': subscription_id}
