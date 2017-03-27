import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse
from uuid import UUID

from protobuf.client_pb2 import Request
from protobuf.server_pb2 import Response, ServerMessage
import protobuf.shared_pb2
import websockets
import websockets.exceptions

from . import cancel_futures, daemon_task, raise_future_exception
from .pubsub import PubSub
from .subscription import CrawlSyncSubscription, JobStatusSubscription


logger = logging.getLogger(__name__)


class InvalidRequestException(Exception):
    ''' Indicates a request is invalid. '''


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

        self._request_handlers = {
            'ping': self._ping,
            'set_job_run_state': self._set_job_run_state,
            'start_job': self._start_job,
            'subscribe_job_sync': self._subscribe_crawl_sync,
            'subscribe_jobs_status': self._subscribe_job_status,
            'unsubscribe': self._unsubscribe,
        }

    async def handle_connection(self, websocket, path):
        ''' Handle an incoming connection. '''
        self._clients.add(websocket)
        pending_requests = set()
        logger.info('Websocket connection from %s:%s, path=%s',
            websocket.remote_address[0],
            websocket.remote_address[1],
            path
        )

        while True:
            try:
                request_data = await websocket.recv()
                request_task = asyncio.ensure_future(
                    self._handle_request(websocket, request_data))
                pending_requests.add(request_task)
                raise_future_exception(request_task)
            except websockets.exceptions.ConnectionClosed:
                subscriptions = self._subscriptions[websocket].values()
                await cancel_futures(*pending_requests)
                await cancel_futures(*subscriptions)
                del self._subscriptions[websocket]
                self._clients.remove(websocket)
                logger.info('Connection closed: %s:%s',
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                )
                break
            except asyncio.CancelledError:
                await cancel_futures(*pending_requests)
                try:
                    await websocket.close()
                except websocket.exceptions.InvalidState:
                    pass
                break

    async def _handle_request(self, websocket, request_data):
        ''' Handle a single request/response pair. '''
        try:
            request = Request.FromString(request_data)
            command_name = request.WhichOneof('Command')

            if command_name is None:
                raise InvalidRequestException('No command specified')

            command = getattr(request, command_name)

            try:
                handler = self._request_handlers[command_name]
            except KeyError:
                raise InvalidRequestException(
                    'Invalid command name: {}'.format(command_name)
                )

            response = await handler(command, websocket)
            response.request_id = request.request_id
            response.is_success = True
        except Exception as e:
            logger.exception('Error while handling request: %r', request)
            response = Response()
            response.is_success = False
            response.error_message = str(e)
            try:
                response.request_id = request.request_id
            except:
                # A parsing failure could lead to request or request_id not
                # being defined. There's nothing we can do to fix this.
                pass

        if response.IsInitialized():
            message = ServerMessage()
            message.response.MergeFrom(response)
            message_data = message.SerializeToString()
            await websocket.send(message_data)
        else:
            # This could happen, e.g. if the request_id is not set.
            logger.error('Cannot send uninitialized response: %r', response)

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

    async def _ping(self, command, socket):
        '''
        A client may ping the server to prevent connection timeout.

        This sends back whatever string was sent.
        '''
        response = Response()
        response.ping.pong = command.pong
        return response

    async def _set_job_run_state(self, command, socket):
        ''' Set a job's run state, i.e. paused, running, etc. '''

        job_id = str(UUID(bytes=command.job_id))
        run_state = command.run_state

        if run_state == protobuf.shared_pb2.CANCELLED:
            await self._crawl_manager.cancel_job(job_id)
        elif run_state == protobuf.shared_pb2.PAUSED:
            await self._crawl_manager.pause_job(job_id)
        elif run_state == protobuf.shared_pb2.RUNNING:
            await self._crawl_manager.resume_job(job_id)
        else:
            raise Exception('Not allowed to set job run state: {}'
                .format(run_state))

        return Response()

    async def _start_job(self, command, socket):
        ''' Handle the start crawl command. '''
        name = command.name
        seeds = command.seeds

        if name.strip() == '':
            url = urlparse(seeds[0])
            name = url.hostname
            if len(seeds) > 1:
                name += '& {} more'.format(len(seeds) - 1)

        job_id = await self._crawl_manager.start_job(name, seeds)
        response = Response()
        response.new_job.job_id = UUID(job_id).bytes
        return response

    async def _subscribe_crawl_sync(self, command, socket):
        ''' Handle the subscribe crawl items command. '''
        job_id = str(UUID(bytes=command.job_id))

        if command.HasField('sync_token'):
            sync_token = command.sync_token
        else:
            sync_token = None

        subscription = CrawlSyncSubscription(
            self._tracker, self._db_pool, socket, job_id, sync_token
        )

        coro = daemon_task(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        response = Response()
        response.new_subscription.subscription_id = subscription.id
        return response

    async def _subscribe_job_status(self, command, socket):
        ''' Handle the subscribe crawl status command. '''
        subscription = JobStatusSubscription(
            self._tracker,
            socket,
            command.min_interval
        )
        coro = daemon_task(subscription.run())
        self._subscriptions[socket][subscription.id] = coro
        response = Response()
        response.new_subscription.subscription_id = subscription.id
        return response

    async def _unsubscribe(self, command, socket):
        ''' Handle an unsubscribe command. '''
        subscription_id = command.subscription_id
        task = self._subscriptions[socket][subscription_id]
        await cancel_futures(task)
        del self._subscriptions[socket][subscription_id]
        return Response()
