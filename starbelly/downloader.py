# from collections import defaultdict, namedtuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
# import traceback
from typing import Any

# import aiohttp
# import aiosocks.connector
# import aiosocks.errors
import trio
import w3lib.url
import yarl

from .policy import Policy


logger = logging.getLogger(__name__)


class MimeNotAllowedError(Exception):
    ''' Indicates that the MIME type of a response is not allowed by policy. '''


@dataclass
class DownloadRequest:
    ''' Represents a resource that needs to be downloaded. '''
    job_id: bytes
    method: str
    url: str
    form_data: dict
    cost: float
    policy: Policy
    cookie_jar: Any = field() # TODO what type for cookie jar?
    canonical_url: str = field(init=False)

    def __post_init__(self):
        ''' Initialize URL. '''
        self.canonical_url = w3lib.url.canonicalize_url(self.url)
        self.url = yarl.URL(self.url)


@dataclass
class DownloadResponse:
    '''
    Represents the result of downloading a resource, which could contain a
    successful response body, an HTTP error, or an exception.
    '''
    cost: float
    url: str
    canonical_url: str
    content_type: str = field(default=None)
    body: bytes = field(default=None)
    started_at: datetime = field(default=None)
    completed_at: datetime = field(default=None)
    exception: str = field(default=None)
    headers: dict = field(default=None)
    should_save: bool = field(default=None)

    @classmethod
    def from_request(cls, request):
        '''
        Initialize a response from its corresponding request.

        :param DownloadRequest request: The request that generated this
            response.
        '''
        return cls(request.cost, request.url, request.canonical_url)

    @property
    def duration(self):
        ''' The time elapsed while downloading this resource. '''
        try:
            return self.completed_at.timestamp() - self.started_at.timestamp()
        except AttributeError:
            # One or both datetimes is None.
            return None

    def start(self):
        ''' Called when the request has been sent and the response is being
        waited for. '''
        self.started_at = datetime.now(timezone.utc)

    def set_exception(self, exception):
        '''
        Indicate that an exception occurred while downloading this resource.

        :param str exception: Traceback of the exception.
        '''
        self.completed_at = datetime.now(timezone.utc)
        self.exception = exception

    def set_response(self, http_response, body):
        ''' Update state from HTTP response. '''
        self.completed_at = datetime.now(timezone.utc)
        self.status_code = http_response.status
        self.headers = http_response.headers
        self.content_type = http_response.content_type
        self.body = body


@dataclass
class _JobDownloaderState:
    '''
    Contains state needed to oversee the download tasks for a single job.
    '''

    send_channel: trio.SendChannel
    recv_channel: trio.ReceiveChannel
    cancel_scope: trio.CancelScope = field(default=None)


class Downloader:
    ''' This class is responsible for downloading resources. '''

    def __init__(self, request_channel, response_channel, concurrent):
        '''
        Constructor.

        :param trio.ReceiveChannel request_channel: A Trio channel that receives
            download requests.
        :param trio.SendChannel response_channel: A Trio channel that the
            downloader will send downloaded resources to.
        :param int concurrent: The maximum number of concurrent downloads.
        '''
        self._job_tasks = dict()
        self._request_channel = request_channel
        self._response_channel = response_channel
        self._capacity_limiter = trio.CapacityLimiter(concurrent)

    def count(self):
        ''' Return number of active downloads. '''
        return sum(len(dls) for dls in self._downloads_by_job.values())

    def add_job(self, job_id):


    def remove_job(self, job_id):
        '''
        Cancel any pending downloads for the specified job. Clean up all
        associated tasks.

        :param bytes job_id: The job ID to cancel downloads for.
        '''
        self._cancel_scopes[job_id].cancel()

    async def run(self):
        '''
        Run the downloader, including all concurrent download tasks. When
        cancelled, all download tasks are also cancelled.

        :returns: Runs until cancelled.
        '''
        async with trio.open_nursery() as nursery:
            while True:
                await self._capacity_limiter.acquire()
                request = await self._request_channel.receive()
                try:
                    job_nursery = self._job_nurseries[request.job_id]
                except KeyError:
                    job_nursery = _JobDownloaderState(
                        *trio.open_memory_channel(0))
                    nursery.start_soon()
                    self._job_nurseries[request.job_id] = job_nursery
                job_nursery.start_soon(self._download, request)

    async def _run_job_nursery(self, job_nursery):
        '''
        Creates a nursery for all downloads beginning to a particular job.

        :returns: Runs until cancelled.
        '''
        async with trio.open_nursery() as nursery:
            self._job_nurseries

    # async def _download(self, download_request):
    #     ''' Download a URL and send the result to an output queue. '''
    #     try:
    #         response = await self._download_helper(download_request)
    #         await self._response_channel.send(response)
    #         self._rate_limiter.reset(download_request.url)
    #     finally:
    #         task = asyncio.Task.current_task()
    #         job_id = download_request.job_id
    #         job_downloads = self._downloads_by_job[job_id]
    #         job_downloads.remove(task)
    #         if len(job_downloads) == 0:
    #             del self._downloads_by_job[job_id]
    #         self._capacity_limiter.release()

    # async def _download_helper(self, download_request):
    #     ''' A helper to ``_download()``. '''
    #     HTTP_PROXY = ('http', 'https')
    #     SOCKS_PROXY = ('socks4', 'socks4a', 'socks5')
    #     session_args = dict()
    #     policy = download_request.policy
    #     url = download_request.url
    #     proxy_type, proxy_url = policy.proxy_rules.get_proxy_url(url)

    #     if proxy_type in SOCKS_PROXY:
    #         session_args['connector'] = aiosocks.connector.ProxyConnector(
    #             remote_resolve=(proxy_type != 'socks4'),
    #             verify_ssl=False
    #         )
    #         session_args['request_class'] = \
    #             aiosocks.connector.ProxyClientRequest
    #     else:
    #         session_args['connector'] = aiohttp.TCPConnector(verify_ssl=False)

    #     user_agent = download_request.policy.user_agents.get_user_agent()
    #     session_args['headers'] = {'User-Agent': user_agent}
    #     if download_request.cookie_jar is not None:
    #         session_args['cookie_jar'] = download_request.cookie_jar
    #     session = aiohttp.ClientSession(**session_args)
    #     dl_response = DownloadResponse(download_request)

    #     try:
    #         async with timeout(20), session:
    #             kwargs = dict()
    #             if proxy_url is not None:
    #                 kwargs['proxy'] = proxy_url
    #             if download_request.method == 'GET':
    #                 if download_request.form_data is not None:
    #                     kwargs['params'] = download_request.form_data
    #                 http_request = session.get(url, **kwargs)
    #             elif download_request.method == 'POST':
    #                 if download_request.form_data is not None:
    #                     kwargs['data'] = download_request.form_data
    #                 http_request = session.post(url, **kwargs)
    #             else:
    #                 raise Exception('Unsupported HTTP method: {}'
    #                     .format(download_request.method))
    #             async with http_request as http_response:
    #                 mime = http_response.headers.get('content-type',
    #                     'application/octet-stream')
    #                 if not policy.mime_type_rules.should_save(mime):
    #                     raise MimeNotAllowedError()
    #                 body = await http_response.read()
    #                 dl_response.set_response(http_response, body)
    #         logger.info('%d %s (cost=%0.2f)', dl_response.status_code,
    #             dl_response.url, dl_response.cost)
    #     except asyncio.CancelledError:
    #         raise
    #     except MimeNotAllowedError:
    #         logger.info('MIME %s disallowed by policy for URL %s', mime,
    #             download_request.url)
    #         dl_response.should_save = False
    #     except (aiohttp.ClientError, aiosocks.errors.SocksError) as err:
    #         # Don't need a full stack trace for these common exceptions.
    #         msg = '{}: {}'.format(err.__class__.__name__, err)
    #         logger.warn('Failed downloading %s: %s', download_request.url, msg)
    #         dl_response.set_exception(msg)
    #     except asyncio.TimeoutError as te:
    #         logger.warn('Timed out downloading %s', download_request.url)
    #         dl_response.set_exception('Timed out')
    #     except Exception as exc:
    #         logger.exception('Failed downloading %s', download_request.url)
    #         dl_response.set_exception(traceback.format_exc())

    #     return dl_response
