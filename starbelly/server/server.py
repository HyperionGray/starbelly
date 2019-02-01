import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import cProfile
import gzip
import logging
import operator
import pstats
from time import time
from urllib.parse import urlparse

import dateutil.parser
from dateutil.tz import tzlocal
from protobuf.client_pb2 import Request
from protobuf.server_pb2 import Response, ServerMessage
import protobuf.shared_pb2
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
import websockets
import websockets.exceptions


logger = logging.getLogger(__name__)


class InvalidRequestException(Exception):
    ''' Indicates a request is invalid. '''


class Server:
    ''' Handles websocket connections from clients and command dispatching. '''

    def __init__(self, host, port, db_pool, crawl_manager, subscription_manager,
                 tracker, rate_limiter, policy_manager, resource_monitor,
                 scheduler):
        ''' Constructor. '''
        self._clients = set()
        self._crawl_manager = crawl_manager
        self._db_pool = db_pool
        self._host = host
        self._policy_manager = policy_manager
        self._port = port
        self._rate_limiter = rate_limiter
        self._resource_monitor = resource_monitor
        self._scheduler = scheduler
        self._subscription_manager = subscription_manager
        self._tracker = tracker
        self._websocket_server = None

    async def handle_connection(self, websocket, path):
        ''' Handle an incoming connection. '''
        self._clients.add(websocket)
        pending_requests = set()
        client_ip = websocket.request_headers.get('X-Client-IP') or \
                    websocket.remote_address[0]
        logger.info('Connection opened: client=%s path=%s', client_ip, path)

        try:
            while True:
                request_task = None
                request_data = await websocket.recv()
                request_task = daemon_task(
                    self._handle_request(client_ip, websocket, request_data))
                pending_requests.add(request_task)
                request_task.add_done_callback(
                    lambda task: pending_requests.remove(task))
                del request_task
        except websockets.exceptions.ConnectionClosed as cc:
            await self._subscription_manager.close_for_socket(websocket)
            await cancel_futures(*pending_requests)
            logger.info('Connection closed: client=%s code=%d reason="%s"',
                client_ip, cc.code, cc.reason)
        except asyncio.CancelledError:
            await cancel_futures(*pending_requests)
            try:
                await websocket.close()
            except websocket.exceptions.InvalidState:
                pass
            raise
        finally:
            self._clients.remove(websocket)

    async def run(self):
        ''' Run the websocket server. '''
        try:
            logger.info('Starting server on {}:{}'.format(self._host, self._port))
            self._websocket_server = await websockets.serve(self.handle_connection,
                self._host, self._port)

            # This task idles: it's only purpose is to supervise child tasks.
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info('Closing websockets...')
            self._websocket_server.close()
            await self._websocket_server.wait_closed()
            logger.info('All websockets closed.')

    async def _handle_request(self, client_ip, websocket, request_data):
        ''' Handle a single request/response pair. '''
        request = Request.FromString(request_data)
        start = time()

        try:
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
            elapsed = time() - start
            logger.info('Request OK %s %s %0.3fs', command_name, client_ip,
                elapsed)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if isinstance(e, InvalidRequestException):
                elapsed = time() - start
                logger.error('Request ERROR %s %s %0.3fs', command_name,
                    client_ip, elapsed)
            else:
                logger.exception('Exception while handling request:\n%r',
                    request)
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
            logger.error('Cannot send uninitialized response:\n%r', response)
