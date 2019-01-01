import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
import traceback
from typing import Any

import aiohttp
import aiohttp_socks
import aiohttp_socks.errors
import trio
import trio_asyncio
import w3lib.url
import yarl

from .policy import Policy


logger = logging.getLogger(__name__)
_HTTP_PROXY_SCHEMES = ('http', 'https')
_SOCKS_PROXY_SCHEMES = ('socks4', 'socks4a', 'socks5')


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
    cookie_jar: aiohttp.CookieJar
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
    status_code: int = field(default=None)
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


class Downloader:
    ''' This class is responsible for downloading resources. A new instance is
    created for each crawl job. '''

    def __init__(self, request_channel, response_channel, semaphore):
        '''
        Constructor.

        :param trio.ReceiveChannel request_channel: A Trio channel that receives
            download requests.
        :param trio.SendChannel response_channel: A Trio channel that the
            downloader will send downloaded resources to.
        :param trio.Semaphore semaphore: The downloader acquires the semaphore
            for each download.
        '''
        self._request_channel = request_channel
        self._response_channel = response_channel
        self._semaphore = semaphore

    async def run(self):
        '''
        Run the downloader, including all concurrent download tasks. When
        cancelled, all download tasks are also cancelled.

        :returns: Runs until cancelled.
        '''
        async with trio.open_nursery() as nursery, \
                   trio_asyncio.open_loop() as loop:
            async for request in self._request_channel:
                await self._semaphore.acquire()
                nursery.start_soon(self._download, request)

    async def _download(self, request):
        '''
        Download a requested resource and send the response to an output queue.

        :param DownloadRequest request:
        '''
        try:
            with trio.fail_after(20): # TODO make this part of policy
                response = await self._download_asyncio(request)
            await self._response_channel.send(response)
        finally:
            # self._rate_limiter.reset(request.url) # TODO how to reset rate limiter?
            self._semaphore.release()

    @trio_asyncio.trio2aio
    async def _download_asyncio(self, request):
        '''
        A helper for ``_download()`` that runs on the asyncio event loop. There
        is not a mature Trio library for HTTP that supports SOCKS proxies, so
        we use asyncio libraries instead.

        :param DownloadRequest request:
        '''
        session_args = dict()
        policy = request.policy
        url = request.url
        proxy_type, proxy_url = policy.proxy_rules.get_proxy_url(url)

        if proxy_type in _SOCKS_PROXY_SCHEMES:
            session_args['connector'] = aiohttp_socks.SocksConnector.from_url(
                proxy_url)
        else:
            session_args['connector'] = aiohttp.TCPConnector(verify_ssl=False)

        user_agent = request.policy.user_agents.get_user_agent()
        session_args['headers'] = {'User-Agent': user_agent}
        if request.cookie_jar is not None:
            session_args['cookie_jar'] = request.cookie_jar
        session = aiohttp.ClientSession(**session_args)
        dl_response = DownloadResponse.from_request(request)

        try:
            kwargs = dict()
            if proxy_type in _HTTP_PROXY_SCHEMES:
                kwargs['proxy'] = proxy_url
            if request.method == 'GET':
                if request.form_data is not None:
                    kwargs['params'] = request.form_data
                http_request = session.get(url, **kwargs)
            elif request.method == 'POST':
                if request.form_data is not None:
                    kwargs['data'] = request.form_data
                http_request = session.post(url, **kwargs)
            else:
                raise Exception('Unsupported HTTP method: {}'
                    .format(request.method))
            async with http_request as http_response:
                mime = http_response.headers.get('content-type',
                    'application/octet-stream')
                if not policy.mime_type_rules.should_save(mime):
                    raise MimeNotAllowedError()
                body = await http_response.read()
                dl_response.set_response(http_response, body)
            logger.info('%d %s (cost=%0.2f)', dl_response.status_code,
                dl_response.url, dl_response.cost)
        except asyncio.CancelledError:
            raise
        except MimeNotAllowedError:
            logger.info('MIME %s disallowed by policy for URL %s', mime,
                request.url)
            dl_response.should_save = False
        except (aiohttp.ClientError, aiohttp_socks.errors.SocksError) as err:
            # Don't need a full stack trace for these common exceptions.
            msg = '{}: {}'.format(err.__class__.__name__, err)
            logger.warn('Failed downloading %s: %s', request.url, msg)
            dl_response.set_exception(msg)
        except asyncio.TimeoutError as te:
            logger.warn('Timed out downloading %s', request.url)
            dl_response.set_exception('Timed out')
        except Exception as exc:
            logger.exception('Failed downloading %s', request.url)
            dl_response.set_exception(traceback.format_exc())

        return dl_response
