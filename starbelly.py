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

    async def pop_url(self):
        url = await self._queue.get()
        logger.debug('Popping {}'.format(url))
        return url

    async def push_url(self, url):
        if not url.startswith(self._seed):
            logger.debug('Out of domain: {}'.format(url))
            return
        if not url.endswith('.html'):
            logger.debug('Not HTML: {}'.format(url))
            return
        if url in self._seen:
            logger.debug('Duplicate: {}'.format(url))
            return

        logger.debug('Pushing {}'.format(url))
        await self._queue.put(url)
        self._seen.add(url)


class Crawler:
    def __init__(self, frontier):
        self._frontier = frontier
        self._sempaphore = asyncio.Semaphore(10)

    async def get(self, url):
        conn = aiohttp.TCPConnector(verify_ssl=False)
        logger.info('Fetching {}'.format(url))
        with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url) as response:
                await self._handle_response(url, response)

    async def run(self):
        while frontier._queue.qsize() > 0:
            url = await self._frontier.pop_url()
            await(self.get(url))

    async def _handle_response(self, url, response):
        logger.info('{} {}'.format(url, response.status))
        body = await response.read()
        for url in self._parse_hrefs(url, body):
            await self._frontier.push_url(url)

    def _parse_hrefs(self, url, html):
        doc = lxml.html.document_fromstring(html)
        for link in doc.iterlinks():
            new_url = urljoin(url, link[2])
            yield new_url


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    frontier = Frontier(seed='https://markhaa.se')
    crawler = Crawler(frontier)
    loop = asyncio.get_event_loop()
    logger.info('Starting crawler')
    loop.run_until_complete(crawler.run())
    logger.info('Crawler stopped')
    loop.close()
