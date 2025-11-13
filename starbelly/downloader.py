import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
import traceback

import aiohttp
import aiohttp_socks
import trio
import trio_asyncio
import w3lib.url
from yarl import URL


logger = logging.getLogger(__name__)
_HTTP_PROXY_SCHEMES = ('http', 'https')
_SOCKS_PROXY_SCHEMES = ('socks4', 'socks4a', 'socks5')
_RDNS_SOCKS_PROXY_SCHEMES = ('socks4a', 'socks5')


class CrawlItemLimitExceeded(Exception):
    ''' The crawl has downloaded the maximum number of items. '''


class MimeNotAllowedError(Exception):
    ''' Indicates that the MIME type of a response is not allowed by policy. '''
    def __init__(self, mime):
        self.mime = mime


@dataclass
class DownloadRequest:
    ''' Represents a resource that needs to be downloaded. '''
    frontier_id: bytes
    job_id: bytes
    method: str
    url: str
    form_data: dict
    cost: float
    canonical_url: str = field(init=False)

    def __post_init__(self):
        ''' Initialize URLs. '''
        self.url = URL(self.url)
        self.canonical_url = w3lib.url.canonicalize_url(str(self.url))

    @classmethod
    def from_frontier_item(cls, frontier_item):
        return cls(frontier_item.frontier_id, frontier_item.job_id,
            method='GET', url=frontier_item.url, form_data=None,
            cost=frontier_item.cost)


@dataclass
class DownloadResponse:
    '''
    Represents the result of downloading a resource, which could contain a
    successful response body, an HTTP error, or an exception.
    '''
    frontier_id: bytes
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

    def __post_init__(self):
        ''' Initialize URL. '''
        self.url = URL(self.url)
        self.canonical_url = w3lib.url.canonicalize_url(str(self.url))
        self.duration = None

    @classmethod
    def from_request(cls, request):
        '''
        Initialize a response from its corresponding request.

        :param DownloadRequest request: The request that generated this
            response.
        '''
        return cls(request.frontier_id, request.cost, request.url,
            request.canonical_url)

    @property
    def is_success(self):
        return self.status_code == 200

    @property
    def is_exception(self):
        return self.exception is not None

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
        self.duration = (self.completed_at - self.started_at).total_seconds()
        self.exception = exception

    def set_response(self, http_response, body):
        ''' Update state from HTTP response. '''
        self.completed_at = datetime.now(timezone.utc)
        self.duration = (self.completed_at - self.started_at).total_seconds()
        self.status_code = http_response.status
        self.headers = http_response.headers
        self.content_type = http_response.content_type
        self.body = body


class Downloader:
    ''' This class is responsible for downloading resources. A new instance is
    created for each crawl job. '''

    def __init__(self, job_id, policy, send_channel, recv_channel,
            semaphore, rate_limiter_reset, stats):
        '''
        Constructor.

        :param str job_id: The ID of the job to download requests for.
        :param starbelly.policy.Policy: The policy to use when downloading
            objects.
        :param trio.SendChannel send_channel: A Trio channel that the
            downloader will send downloaded resources to.
        :param trio.ReceiveChannel recv_channel: A Trio channel that receives
            download requests.
        :param trio.Semaphore semaphore: The downloader acquires the semaphore
            for each download.
        :param trio.SendChannel rate_limiter_reset: A Trio channel that can be
            used to reset the rate limiter after each resource is downloaded.
        :param dict stats: A dictionary that the download should store
            statistics in, such as number of items downloaded.
        '''
        self._job_id = job_id
        self._policy = policy
        self._send_channel = send_channel
        self._recv_channel = recv_channel
        self._semaphore = semaphore
        self._rate_limiter_reset = rate_limiter_reset
        self._stats = stats
        self._cookie_jar = None
        self._count = 0

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<Downloader job_id={}>'.format(self._job_id[:8])

    @property
    def count(self):
        '''
        Return number of current downloads in progress.

        :rtype int:
        '''
        return self._count

    async def run(self):
        '''
        Run the downloader, including all concurrent download tasks. When
        cancelled, all download tasks are also cancelled.

        :returns: Runs until cancelled.
        '''
        async with trio.open_nursery() as nursery, \
                   trio_asyncio.open_loop():
            async for request in self._recv_channel:
                await self._semaphore.acquire()
                self._count += 1
                nursery.start_soon(self._download, request)

    async def download(self, request, skip_mime=False):
        '''
        Download a requested resource and return it.

        Note: this is probably not the method you want! Most downloads should be
        sent through the request channel. This method is only for unusual cases
        where we want to download one item and return the response directly to
        the caller, such as a robot.txt or a login page.

        These responses are not included in job statistics and do not get stored
        in the database. The caller should apply their own timeout here.

        :param DownloadRequest request:
        :param bool skip_mime: If True, the MIME type will not be checked
            against the policy.
        :rtype DownloadResponse:
        '''
        async with self._semaphore, trio_asyncio.open_loop():
            response = await self._download_asyncio(request, skip_mime=skip_mime)
        return response

    async def _download(self, request):
        '''
        Download a requested resource and send the response to an output queue.

        :param DownloadRequest request:
        '''
        stats = self._stats
        try:
            response = await self._download_asyncio(request)

            # Update stats before forwarding response.
            stats['item_count'] += 1
            if response.exception:
                stats['exception_count'] += 1
            elif response.is_success:
                stats['http_success_count'] += 1
            else:
                stats['http_error_count'] += 1
            if response.status_code is not None:
                http_status_counts = stats['http_status_counts']
                http_status_counts[response.status_code] = \
                    http_status_counts.get(response.status_code, 0) + 1

            await self._send_channel.send(response)
        except MimeNotAllowedError as exc:
            # MIME errors indicate the response MIME type was not allowed by
            # policy. Create a response with exception info so it's visible in
            # the results.
            response = DownloadResponse.from_request(request)
            response.start()
            response.set_exception(f'MIME type not allowed by policy: {exc.mime}')
            
            # Update stats to track MIME drops
            stats['item_count'] += 1
            stats['exception_count'] += 1
            
            await self._send_channel.send(response)
        finally:
            await self._rate_limiter_reset.send(request.url)
            self._semaphore.release()
            self._count -= 1
            if self._policy.limits.met_item_limit(stats['item_count']):
                raise CrawlItemLimitExceeded()

    @trio_asyncio.aio_as_trio
    async def _download_asyncio(self, request, skip_mime=False):
        '''
        A helper for ``_download()`` that runs on the asyncio event loop. There
        is not a mature Trio library for HTTP that supports SOCKS proxies, so
        we use asyncio libraries instead.

        :param DownloadRequest request:
        '''
        if self._cookie_jar is None:
            self._cookie_jar = aiohttp.CookieJar()
        session_args = {
            'timeout': aiohttp.ClientTimeout(total=20),
            'cookie_jar': self._cookie_jar,
        }
        url = request.url
        proxy_type, proxy_url = self._policy.proxy_rules.get_proxy_url(url)

        if proxy_type in _SOCKS_PROXY_SCHEMES:
            rdns = proxy_type in _RDNS_SOCKS_PROXY_SCHEMES
            session_args['connector'] = aiohttp_socks.SocksConnector.from_url(
                proxy_url, rdns=rdns)
        else:
            session_args['connector'] = aiohttp.TCPConnector(verify_ssl=False)

        user_agent = self._policy.user_agents.get_user_agent()
        session_args['headers'] = {'User-Agent': user_agent}
        session = aiohttp.ClientSession(**session_args)
        dl_response = DownloadResponse.from_request(request)
        dl_response.start()

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
                if not skip_mime and \
                   not self._policy.mime_type_rules.should_save(mime):
                    raise MimeNotAllowedError(mime)
                body = await http_response.read()
                dl_response.set_response(http_response, body)
            logger.info('%r %d %s (cost=%0.2f)', self, dl_response.status_code,
                dl_response.url, dl_response.cost)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            dl_response.set_exception('Timed out')
        except MimeNotAllowedError as exc:
            # This exception re-raises so that instead of being recorded as a
            # failed download, the download is removed from the crawl results
            # altogether.
            logger.error('%r Disallowed MIME "%s": %s', self, exc.mime, url)
            raise
        except (aiohttp.ClientError, aiohttp_socks.SocksError) as err:
            # Don't need a full stack trace for these common exceptions.
            msg = '{}: {}'.format(err.__class__.__name__, err)
            logger.warning('%r Failed downloading %s: %s', self, request.url, msg)
            dl_response.set_exception(msg)
        except Exception:
            logger.exception('%r Failed downloading %s', self, request.url)
            dl_response.set_exception(traceback.format_exc())
        finally:
            await session.close()

        return dl_response
