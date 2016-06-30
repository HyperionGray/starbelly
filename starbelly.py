import asyncio
from io import BytesIO
import logging
import sys
from urllib.parse import urljoin

import aiohttp
import lxml.html


logging.basicConfig()
logger = logging.getLogger()


class Frontier:
    def __init__(self, seed):
        self._seed = seed
        self._seen = set()
        self._queue = asyncio.PriorityQueue()
        self._queue.put_nowait(self._seed)

    def add_url(self, url):
        if url.startswith(self._seed) and url.endswith('.html') and \
           url not in self._seen:

            logger.debug('Pushing {}'.format(url))
            self._queue.put_nowait(url)
            self._seen.add(url)

    async def get_url(self):
        url = await self._queue.get()
        logger.debug('Popping {}'.format(url))
        return url


class Downloader:
    def __init__(self, frontier, concurrent=2):
        self._download_count = 0
        self._download_slot = asyncio.Semaphore(concurrent)
        self._downloader_finished = asyncio.Future()
        self._frontier = frontier

    async def get(self, url):
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self._download_count += 1
        with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url) as response:
                await self._handle_response(url, response)

    async def run(self):
        while True:
            logger.debug('Waiting for download slot...')
            await self._download_slot.acquire()

            logger.debug('Waiting for next URL...')
            url_future = asyncio.ensure_future(self._frontier.get_url())
            done, pending = await asyncio.wait(
                (url_future, self._downloader_finished),
                return_when=asyncio.FIRST_COMPLETED
            )
            if url_future.done():
                url = url_future.result()
            else:
                url_future.cancel()
                break

            logger.info('Fetching {}'.format(url))
            task = asyncio.ensure_future(self.get(url))

    async def _handle_response(self, url, response):
        logger.info('{} {}'.format(url, response.status))
        body = await response.read()

        for url in self._parse_urls(url, body):
            self._frontier.add_url(url)

        logger.debug('Releasing download slot...')
        self._release_download_slot()

    def _parse_urls(self, url, html):
        doc = lxml.html.document_fromstring(html)
        for link in doc.iterlinks():
            new_url = urljoin(url, link[2])
            yield new_url

    def _release_download_slot(self):
        self._download_slot.release()
        self._download_count -= 1
        if self._download_count == 0:
            logger.debug('Downloader is out of downloads!')
            self._downloader_finished.set_result(None)
            self._downloader_finished = asyncio.Future()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    frontier = Frontier(seed='https://markhaa.se')
    downloader = Downloader(frontier)
    loop = asyncio.get_event_loop()
    logger.info('Starting crawler')
    loop.run_until_complete(downloader.run())
    logger.info('Crawler stopped')
    loop.close()
