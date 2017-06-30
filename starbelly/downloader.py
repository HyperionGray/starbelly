import asyncio
from collections import defaultdict, namedtuple
from datetime import datetime
import logging
import traceback

import aiohttp
import aiosocks.connector
import async_timeout
import cchardet as chardet
from dateutil.tz import tzlocal
import w3lib.url

from . import cancel_futures, daemon_task, raise_future_exception


logger = logging.getLogger(__name__)


class MimeNotAllowedError(Exception):
    ''' Indicates that the MIME type of a response is not allowed by policy. '''


class Downloader:
    '''
    This class is responsible for downloading resources.

    The constructor takes a ``concurrent`` argument that limits
    simultaneous downloads, but a better strategy would be to somehow monitor
    bandwidth and keep adding concurrent downloads until resources are maxed
    out. This also needs to take into account how quickly writes can be ingested
    into the database.
    '''

    def __init__(self, rate_limiter, concurrent=10):
        ''' Constructor. '''
        self._download_task = None
        self._downloads_by_job = defaultdict(set)
        self._rate_limiter = rate_limiter
        self._rate_limit_task = None
        self._request_queue = asyncio.Queue(maxsize=1)
        self._semaphore = asyncio.Semaphore(concurrent)

    def count(self):
        ''' Return number of active downloads. '''
        return sum(len(dls) for dls in self._downloads_by_job.values())

    async def download_task(self):
        ''' Read requests from download queue. '''
        try:
            while True:
                await self._semaphore.acquire()
                request = await self._request_queue.get()
                download_task = asyncio.ensure_future(self._download(request))
                self._downloads_by_job[request.job_id].add(download_task)
        except asyncio.CancelledError:
            # Cancellation is okay: cancel all downloads.
            downloads = list()
            for dj in self._downloads_by_job.values():
                downloads.extend(dj)
            await cancel_futures(*downloads)

    async def rate_limiter_task(self):
        '''
        Get requests from the rate limiter and add them to the download queue.
        '''
        while True:
            request = await self._rate_limiter.get_next_request()
            await self._request_queue.put(request)

    async def remove_job(self, job_id, finish_downloads=True):
        '''
        Remove any pending downloads for the specified job.

        If ``finish_downloads`` is True, then wait for downloads to finish.
        Otherwise, cancel downloads.
        '''
        # Make a copy of the jobs list since the original list will change as
        # jobs finish.
        try:
            tasks = list(self._downloads_by_job[job_id])
        except KeyError:
            # No pending items for this job.
            tasks = []

        if len(tasks) > 0:
            if finish_downloads:
                logger.info('Waiting on %s downloads for job=%s...',
                    len(tasks), job_id[:8])
                await asyncio.gather(*tasks)
            else:
                logger.info('Cancelling %s downloads for job=%s...',
                    len(tasks), job_id[:8])
                await cancel_futures(*tasks)
            logger.info('All downloads for job=%s are done.', job_id[:8])

    def start(self):
        ''' Start all tasks. '''
        self._download_task = daemon_task(self.download_task())
        self._rate_limit_task = daemon_task(self.rate_limiter_task())

    async def stop(self):
        '''
        Shut down subordinate tasks.

        This shuts down
        '''
        await cancel_futures(self._download_task, self._rate_limit_task)
        self._download_task = None
        self._rate_limit_task = None

    async def _download(self, download_request):
        ''' Download a URL and send the result to an output queue. '''
        try:
            response = await self._download_helper(download_request)
            await download_request.output_queue.put(response)
            self._rate_limiter.reset(download_request.url)
        finally:
            task = asyncio.Task.current_task()
            job_id = download_request.job_id
            job_downloads = self._downloads_by_job[job_id]
            job_downloads.remove(task)
            if len(job_downloads) == 0:
                del self._downloads_by_job[job_id]
            self._semaphore.release()

    async def _download_helper(self, download_request):
        ''' A helper to ``_download()``. '''
        HTTP_PROXY = ('http', 'https')
        SOCKS_PROXY = ('socks4', 'socks4a', 'socks5')
        session_args = dict()
        policy = download_request.policy
        url = download_request.url
        proxy_type, proxy_url = policy.proxy_rules.get_proxy_url(url)

        if proxy_type in SOCKS_PROXY:
            session_args = {
                'connector': aiosocks.connector.ProxyConnector(
                    remote_resolve=(proxy_type != 'socks4'),
                    verify_ssl=False),
                'request_class': aiosocks.connector.ProxyClientRequest,
            }
        else:
            session_args = {
                'connector': aiohttp.TCPConnector(verify_ssl=False),
            }

        user_agent = download_request.policy.user_agents.get_user_agent()
        session_args['headers'] = {'User-Agent': user_agent}
        session = aiohttp.ClientSession(**session_args)
        dl_response = DownloadResponse(download_request)

        try:
            with session, async_timeout.timeout(20):
                if proxy_url is None:
                    getter = session.get(url)
                else:
                    getter = session.get(url, proxy=proxy_url)
                async with getter as http_response:
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
                download_request.url)
            dl_response.should_save = False
        except Exception as exc:
            logger.error('Failed downloading %s (exc=%r)', download_request.url,
                exc)
            dl_response.set_exception(traceback.format_exc())

        return dl_response


class DownloadRequest:
    ''' Represents a resource that needs to be downloaded. '''

    def __init__(self, job_id, url, cost, policy, output_queue):
        ''' Constructor. '''
        self.job_id = job_id
        self.url = url
        self.url_can = w3lib.url.canonicalize_url(url).encode('ascii')
        self.cost = cost
        self.policy = policy
        self.output_queue = output_queue


class DownloadResponse:
    '''
    Represents the result of downloading a resource, which could contain a
    successful response body, an HTTP error, or an exception.
    '''
    def __init__(self, download_request):
        ''' Construct a result from a ``DownloadRequest`` object. '''
        self.body = None
        self.charset = None
        self.completed_at = None
        self.content_type = None
        self.cost = download_request.cost
        self.duration = None
        self.exception = None
        self.headers = None
        self.should_save = True
        self.started_at = datetime.now(tzlocal())
        self.status_code = None
        self.url = download_request.url
        self.url_can = download_request.url_can

    def set_exception(self, exception):
        ''' Update state to indicate exception occurred. '''
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.exception = exception

    def set_response(self, http_response, body):
        ''' Update state from HTTP response. '''
        self.completed_at = datetime.now(tzlocal())
        self.duration = self.completed_at - self.started_at
        self.status_code = http_response.status
        self.headers = http_response.headers
        self.content_type = http_response.content_type
        if http_response.charset is not None:
            self.charset = http_response.charset
        else:
            self.charset = chardet.detect(body)['encoding']
        self.body = body
