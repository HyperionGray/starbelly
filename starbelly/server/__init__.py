from collections import defaultdict
from datetime import datetime, timedelta
from functools import partial
import gzip
import inspect
import logging
import operator
from time import time
from urllib.parse import urlparse

import dateutil.parser
from dateutil.tz import tzlocal
from google.protobuf.message import DecodeError
import rethinkdb as r
from rethinkdb.errors import ReqlNonExistenceError
from trio_websocket import ConnectionClosed, serve_websocket
import trio

from starbelly.starbelly_pb2 import Request, Response, ServerMessage

# Define API handler decorator before importing API implementations, because
# those implementations use this decorator to register themselves with the
# server.
_handlers = dict()
def api_handler(handler):
    '''
    This decorator registers a function as a callable command through the
    API server.
    '''
    _handlers[handler.__name__] = handler
    return handler


class InvalidRequestException(Exception):
    ''' Indicates a request is invalid. '''


from .captcha import *
# from .job import *
from .login import *
from .policy import *
# from .rate_limit import *
# from .schedule import *
# from .subscription import *
from .system import *


logger = logging.getLogger(__name__)


class Server:
    ''' Handles websocket connections from clients and command dispatching. '''

    def __init__(self, host, port, db, crawl_manager, rate_limiter,
            resource_monitor, scheduler):
        '''
        Constructor

        :param str host: The hostname to serve on.
        :param int port: The port to serve on, or zero to automatically pick a
            port.
        :param starbelly.db.ServerDb db: A database layer.
        :param starbelly.job.CrawlManager crawl_manager: A crawl manager.
        :param starbelly.rate_limiter.RateLimiter: A rate limiter.
        :param starbelly.resource_monitor.ResourceMonitor resource_monitor: A
            resource monitor.
        :param starbelly.schedule.Scheduler scheduler: A scheduler.
        '''
        self._host = host
        self._port = port
        self._db = db
        self._crawl_manager = crawl_manager
        self._rate_limiter = rate_limiter
        self._resource_monitor = resource_monitor
        self._scheduler = scheduler

    @property
    def port(self):
        return self._port

    async def run(self, *, task_status=trio.TASK_STATUS_IGNORED):
        '''
        Run the websocket server.

        To ensure that the server is ready, call ``await
        nursery.start(server.run)``.

        :returns: Runs until cancelled.
        '''
        logger.info('Starting server on %s:%d', self._host, self._port)
        async with trio.open_nursery() as nursery:
            serve_fn = partial(serve_websocket, self._handle_connection,
                self._host, self._port, ssl_context=None,
                handler_nursery=nursery)
            server = await nursery.start(serve_fn)
            self._port = server.port
            task_status.started()
        logger.info('Server stopped')

    async def _handle_connection(self, request):
        '''
        Handle an incoming connection.

        :param request: A WebSocket connection request.
        '''
        headers = dict(request.headers)
        #TODO get client ip/port/path from websocket? should it be part of request?
        # websocket.remote_address[0]
        client_ip = headers.get('X-CLIENT-IP') or '?.?.?.?'
        websocket = await request.accept()
        logger.info('Connection opened: client=%s path=%s', client_ip,
            websocket.path)
        connection = Connection(client_ip, websocket, self._db,
            self._crawl_manager, self._rate_limiter, self._resource_monitor,
            self._scheduler)
        await connection.run()


class Connection:
    def __init__(self, client_ip, ws, db, crawl_manager, rate_limiter,
            resource_monitor, scheduler):
        '''
        Constructor.

        :param str client_ip: The IP address of the client that opened this
            connection.
        :param trio_websocket.WebSocketConnection ws: A websocket connection.
        :param starbelly.db.ServerDb: A database layer.
        :param starbelly.job.CrawlManager crawl_manager: A crawl manager.
        :param starbelly.rate_limiter.RateLimiter: A rate limiter.
        :param starbelly.resource_monitor.ResourceMonitor resource_monitor: A
            resource monitor.
        :param starbelly.schedule.Scheduler scheduler: A scheduler.
        '''
        self._client_ip = client_ip
        self._ws = ws
        self._db = db
        self._crawl_manager = crawl_manager
        self._rate_limiter = rate_limiter
        self._resource_monitor = resource_monitor
        self._scheduler = scheduler
        self._nursery = None

    async def run(self):
        '''
        Run the connection: read requests and send responses.

        This opens an internal nursery in case background tasks, like
        subscriptions, need to be started.

        :returns: This runs until the connection is closed.
        '''
        try:
            async with trio.open_nursery() as nursery:
                self._nursery = nursery
                while True:
                    request_data = await self._ws.get_message()
                    nursery.start_soon(self._handle_request, request_data)
        except ConnectionClosed:
            logger.info('Connection closed for %s', self._client_ip)
        except Exception as e:
            logger.exception('Connection exception')
        finally:
            await self._ws.aclose()

    async def _handle_request(self, request_data):
        '''
        Handle a single API request.

        :param request: A protobuf request object.
        '''
        start = trio.current_time()
        message = ServerMessage()
        message.response.is_success = False
        request = None

        try:
            # Prepare response.
            request = Request.FromString(request_data)
            message.response.request_id = request.request_id

            # Find an appropriate handler.
            command_name = request.WhichOneof('Command')
            if command_name is None:
                raise InvalidRequestException('No command specified')
            command = getattr(request, command_name)
            try:
                handler = _handlers[command_name]
            except KeyError:
                raise InvalidRequestException('Invalid command name: {}'
                    .format(command_name)) from None

            # Inject dependencies into argument list, then call the handler.
            argspec = inspect.getargspec(handler)
            args = list()
            for var in argspec[0]:
                logger.debug('var=%s', var)
                if var == 'command':
                    args.append(command)
                elif var == 'nursery':
                    args.append(self._nursery)
                elif var == 'rate_limiter':
                    args.append(self._rate_limiter)
                elif var == 'response':
                    args.append(message.response)
                elif var == 'scheduler':
                    args.append(self._scheduler)
                elif var == 'websocket':
                    args.append(self._ws)
                else:
                    raise Exception('Unknown dependency "{}" in handler {}()'
                        .format(var, command_name))

            await handler(*args)
            message.response.is_success = True
            elapsed = trio.current_time() - start
            logger.info('Request OK %s %s %s %0.3fs', command_name,
                self._client_ip, elapsed)
        except DecodeError:
            # Failure to decode a protobuf message means that the connection
            # is severely damaged; raise to the nursery so we can close the
            # entire connection.
            raise
        except InvalidRequestException as ire:
            error_message = str(ire)
            logger.error('Request ERROR %s %s (%s)', command_name,
                self._client_ip, error_message)
            message.response.error_message = error_message
        except Exception as exc:
            logger.exception('Exception while handling request:\n%r',
                request)
            message.response.error_message = 'A server exception occurred'

        message_data = message.SerializeToString()
        await self._ws.send_message(message_data)
