import asyncio
from collections import namedtuple
import logging

import aiohttp
import async_timeout

logger = logging.getLogger(__name__)


class Downloader:
    '''
    This class is responsible for downloading crawl items.

    TODO The constructor takes a ``concurrent`` argument that limits
    simultaneous downloads, but a better strategy would be to somehow monitor
    bandwidth and keep adding concurrent downloads until resources are maxed
    out.
    '''

    def __init__(self, concurrent=10):
        ''' Constructor. '''
        self._slot = asyncio.Semaphore(concurrent)

    async def schedule_download(self, crawl_item):
        '''
        Schedule an item to be downloaded.

        This method waits for a download slot, then schedules a download. It
        returns when the download is *scheduled*, not when the download is
        complete.

        Returns a future that finishes when the item is downloaded.
        '''
        await self._slot.acquire()
        return asyncio.ensure_future(self._download(crawl_item))

    async def _download(self, crawl_item):
        '''
        Download a crawl item.

        Releases a download slot when the download is finished, updates the
        crawl item with the response data, and returns the crawl item.
        '''

        msg = 'Fetching {} (depth={})'
        logger.info(msg.format(crawl_item.url, crawl_item.depth))
        connector = aiohttp.TCPConnector(verify_ssl=False)

        try:
            with aiohttp.ClientSession(connector=connector) as session:
                crawl_item.start()
                with async_timeout.timeout(10):
                    async with session.get(crawl_item.url) as response:
                        status = response.status
                        logger.info('{} {}'.format(status, crawl_item.url))
                        body = await response.read()
                        self._slot.release()
                        crawl_item.finish(int(status), response.headers, body)
                        return crawl_item
        except (aiohttp.ClientResponseError, asyncio.TimeoutError) as exc:
            logger.error('Failed downloading {}'.format(crawl_item.url))
            crawl_item.exception = exc
            return crawl_item
