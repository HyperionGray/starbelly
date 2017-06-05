import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import gzip
import logging
from time import time
from urllib.parse import urlparse
from uuid import UUID

from protobuf.client_pb2 import Request
from protobuf.server_pb2 import Response, ServerMessage
import protobuf.shared_pb2
import websockets
import websockets.exceptions

from . import cancel_futures, raise_future_exception
from .pubsub import PubSub
from .subscription import CrawlSyncSubscription, JobStatusSubscription


logger = logging.getLogger(__name__)


class InvalidRequestException(Exception):
    ''' Indicates a request is invalid. '''


class Server:
    ''' Handles websocket connections from clients and command dispatching. '''

    def __init__(self, host, port, db_pool, crawl_manager, subscription_manager,
                 tracker, rate_limiter, policy_manager):
        ''' Constructor. '''
        self._clients = set()
        self._crawl_manager = crawl_manager
        self._db_pool = db_pool
        self._host = host
        self._policy_manager = policy_manager
        self._port = port
        self._rate_limiter = rate_limiter
        self._subscription_manager = subscription_manager
        self._tracker = tracker
        self._websocket_server = None

        self._request_handlers = {
            'delete_job': self._delete_job,
            'delete_policy': self._delete_policy,
            'get_job': self._get_job,
            'get_job_items': self._get_job_items,
            'get_policy': self._get_policy,
            'get_rate_limits': self._get_rate_limits,
            'list_jobs': self._list_jobs,
            'list_policies': self._list_policies,
            'ping': self._ping,
            'set_job_run_state': self._set_job_run_state,
            'set_policy': self._set_policy,
            'set_rate_limit': self._set_rate_limit,
            'start_job': self._start_job,
            'subscribe_job_sync': self._subscribe_crawl_sync,
            'subscribe_job_status': self._subscribe_job_status,
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
                await self._subscription_manager.close_for_socket(websocket)
                await cancel_futures(*pending_requests)
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
            finally:
                pending_requests.discard(request_task)

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

    async def _delete_job(self, command, socket):
        ''' Delete a job. '''
        job_id = str(UUID(bytes=command.job_id))
        await self._crawl_manager.delete_job(job_id)
        return Response()

    async def _delete_policy(self, command, socket):
        ''' Delete a policy. '''
        policy_id = str(UUID(bytes=command.policy_id))
        await self._policy_manager.delete_policy(policy_id)
        return Response()

    async def _handle_request(self, websocket, request_data):
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
            logger.info('Request OK %s %s %0.3fs', command_name,
                websocket.remote_address[0], elapsed)
        except Exception as e:
            logger.exception('Error while handling request:\n%r', request)
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

    async def _get_job(self, command, socket):
        ''' Get status for a single job. '''
        job_id = str(UUID(bytes=command.job_id))
        job_doc = await self._crawl_manager.get_job(job_id)
        response = Response()
        if job_doc is None:
            response.is_success = False
            response.error_message = f'No job exists with ID={job_id}'
        else:
            job = response.job
            job.job_id = UUID(job_doc['id']).bytes
            for seed in job_doc['seeds']:
                job.seeds.append(seed)
            self._policy_manager.convert_doc_to_pb(job_doc['policy'], job.policy)
            job.name = job_doc['name']
            job.item_count = job_doc['item_count']
            job.http_success_count = job_doc['http_success_count']
            job.http_error_count = job_doc['http_error_count']
            job.exception_count = job_doc['exception_count']
            job.started_at = job_doc['started_at'].isoformat()
            if job_doc['completed_at'] is not None:
                job.completed_at = job_doc['completed_at'].isoformat()
            run_state = job_doc['run_state'].upper()
            job.run_state = protobuf.shared_pb2.JobRunState.Value(run_state)
            http_status_counts = job_doc['http_status_counts']
            for status_code, count in http_status_counts.items():
                job.http_status_counts[int(status_code)] = count
        return response

    async def _get_job_items(self, command, socket):
        ''' Get a page of items (crawl responses) from a job. '''
        job_id = str(UUID(bytes=command.job_id))
        limit = command.page.limit
        offset = command.page.offset
        total_items, item_docs = await self._crawl_manager.get_job_items(
            job_id, command.include_success, command.include_error,
            command.include_exception, limit, offset)
        response = Response()
        response.list_items.total = total_items
        compression_ok = command.compression_ok
        for item_doc in item_docs:
            item = response.list_items.items.add()

            if item_doc['join'] is None:
                item.is_body_compressed = False
            elif item_doc['join']['is_compressed'] and not compression_ok:
                item.body = gzip.decompress(item_doc['join']['body'])
                item.is_body_compressed = False
            else:
                item.body = item_doc['join']['body']
                item.is_body_compressed = item_doc['join']['is_compressed']
            if item_doc.get('charset') is not None:
                item.charset = item_doc['charset']
            if 'content_type' in item_doc:
                item.content_type = item_doc['content_type']
            if 'exception' in item_doc:
                item.exception = item_doc['exception']
            if 'status_code' in item_doc:
                item.status_code = item_doc['status_code']
            for key, value in item_doc.get('headers', {}).items():
                if value is None:
                    value = ''
                item.headers[key] = value
            item.cost = item_doc['cost']
            item.job_id = UUID(item_doc['job_id']).bytes
            item.completed_at = item_doc['completed_at'].isoformat()
            item.started_at = item_doc['started_at'].isoformat()
            item.duration = item_doc['duration']
            item.url = item_doc['url']
            item.url_can = item_doc['url_can']
            item.is_success = item_doc['is_success']
        return response

    async def _get_policy(self, command, socket):
        ''' Get a single policy. '''
        policy_id = str(UUID(bytes=command.policy_id))
        policy_doc = await self._policy_manager.get_policy(policy_id)
        response = Response()
        self._policy_manager.convert_doc_to_pb(policy_doc, response.policy)
        return response

    async def _get_rate_limits(self, command, socket):
        ''' Get a page of rate limits. '''
        limit = command.page.limit
        offset = command.page.offset
        count, rate_limits = await self._rate_limiter.get_limits(limit, offset)

        response = Response()
        response.list_rate_limits.total = count

        for rate_limit in rate_limits:
            rl = response.list_rate_limits.rate_limits.add()
            rl.name = rate_limit['name']
            rl.delay = rate_limit['delay']
            if rate_limit['type'] == 'domain':
                rl.domain = rate_limit['domain']

        return response

    async def _list_jobs(self, command, socket):
        ''' Return a list of jobs. '''
        limit = command.page.limit
        offset = command.page.offset
        job_docs = await self._crawl_manager.list_jobs(limit, offset)
        count = await self._crawl_manager.count_jobs()

        response = Response()
        response.list_jobs.total = count

        for job_doc in job_docs:
            job = response.list_jobs.jobs.add()
            job.job_id = UUID(job_doc['id']).bytes
            job.name = job_doc['name']
            job.item_count = job_doc['item_count']
            job.http_success_count = job_doc['http_success_count']
            job.http_error_count = job_doc['http_error_count']
            job.exception_count = job_doc['exception_count']
            job.started_at = job_doc['started_at'].isoformat()
            if job_doc['completed_at'] is not None:
                job.completed_at = job_doc['completed_at'].isoformat()
            run_state = job_doc['run_state'].upper()
            job.run_state = protobuf.shared_pb2.JobRunState \
                .Value(run_state)
            http_status_counts = job_doc['http_status_counts']
            for status_code, count in http_status_counts.items():
                job.http_status_counts[int(status_code)] = count

        return response

    async def _list_policies(self, command, socket):
        ''' Get a list of policies. '''
        limit = command.page.limit
        offset = command.page.offset
        count, policies = await self._policy_manager.list_policies(
            limit, offset)

        response = Response()
        response.list_policies.total = count

        for policy_doc in policies:
            policy = response.list_policies.policies.add()
            policy.policy_id = UUID(policy_doc['id']).bytes
            policy.name = policy_doc['name']
            policy.created_at = policy_doc['created_at'].isoformat()
            policy.updated_at = policy_doc['updated_at'].isoformat()

        return response

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

    async def _set_policy(self, command, socket):
        '''
        Create or update a single policy.

        If the policy ID is set, then update the corresponding policy.
        Otherwise, create a new policy.
        '''
        policy = self._policy_manager.convert_pb_to_doc(command.policy)
        policy_id = await self._policy_manager.set_policy(policy)
        response = Response()
        if policy_id is not None:
            response.new_policy.policy_id = UUID(policy_id).bytes
        return response

    async def _set_rate_limit(self, command, socket):
        ''' Set a rate limit. '''
        rate_limit = command.rate_limit
        delay = rate_limit.delay if rate_limit.HasField('delay') else None

        if rate_limit.HasField('domain'):
            await self._rate_limiter.set_domain_limit(rate_limit.domain, delay)
        else:
            await self._rate_limiter.set_global_limit(delay)

        return Response()

    async def _start_job(self, command, socket):
        ''' Handle the start crawl command. '''
        name = command.name
        policy_id = str(UUID(bytes=command.policy_id))
        seeds = command.seeds

        if name.strip() == '':
            url = urlparse(seeds[0])
            name = url.hostname
            if len(seeds) > 1:
                name += '& {} more'.format(len(seeds) - 1)

        job_id = await self._crawl_manager.start_job(seeds, policy_id, name)
        response = Response()
        response.new_job.job_id = UUID(job_id).bytes
        return response

    async def _subscribe_crawl_sync(self, command, socket):
        ''' Handle the subscribe crawl items command. '''
        job_id = str(UUID(bytes=command.job_id))
        compression_ok = command.compression_ok

        if command.HasField('sync_token'):
            sync_token = command.sync_token
        else:
            sync_token = None

        subscription = CrawlSyncSubscription(
            self._tracker, self._db_pool, socket, job_id, compression_ok,
            sync_token
        )

        self._subscription_manager.add(subscription)
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
        self._subscription_manager.add(subscription)
        response = Response()
        response.new_subscription.subscription_id = subscription.id
        return response

    async def _unsubscribe(self, command, socket):
        ''' Handle an unsubscribe command. '''
        subscription_id = command.subscription_id
        await self._subscription_manager.unsubscribe(socket, subscription_id)
        return Response()
