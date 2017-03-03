import asyncio
from collections import namedtuple
import logging

import aiohttp
import async_timeout

from . import raise_future_exception

logger = logging.getLogger(__name__)


class Downloader:
    '''
    This class is responsible for downloading crawl items.

    TODO The constructor takes a ``concurrent`` argument that limits
    simultaneous downloads, but a better strategy would be to somehow monitor
    bandwidth and keep adding concurrent downloads until resources are maxed
    out. This also needs to take into account how quickly writes can be ingested
    into the database.
    '''

    def __init__(self, concurrent=10):
        ''' Constructor. '''
        self._semaphore = asyncio.Semaphore(concurrent)
        self._task = None

    async def push(self, crawl_item):
        '''
        Schedule an item for download.

        Blocks if the downloader is busy.
        '''
        await self._semaphore.acquire()
        task = asyncio.ensure_future(self._download(crawl_item))
        raise_future_exception(task)

    async def _download(self, crawl_item):
        ''' Download a crawl item and update it with the response. '''
        try:
            connector = aiohttp.TCPConnector(verify_ssl=False)
            with aiohttp.ClientSession(connector=connector) as session:
                crawl_item.set_start()
                with async_timeout.timeout(10):
                    async with session.get(crawl_item.url) as response:
                        status = response.status
                        logger.info('%d %s (cost=%0.2f)', status,
                            crawl_item.url, crawl_item.cost)
                        body = await response.read()
                        crawl_item.set_response(status, response.headers, body)
        except (aiohttp.ClientResponseError, asyncio.TimeoutError) as exc:
            logger.error('Failed downloading {}'.format(crawl_item.url))
            crawl_item.set_exception(exc)

        self._semaphore.release()
