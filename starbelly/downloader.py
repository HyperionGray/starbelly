import asyncio

import aiohttp

from . import logger


class Downloader:
    def __init__(self, frontier, concurrent=10, max_depth=10):
        self.is_running = False

        self._download_count = 0
        self._download_slot = asyncio.Semaphore(concurrent)
        self._downloader_finished = asyncio.Future()
        self._frontier = frontier

    async def fetch_item(self, crawl_item):
        msg = 'Fetching {} (depth={})'
        logger.info(msg.format(crawl_item.url, crawl_item.depth))
        self._download_count += 1
        connector = aiohttp.TCPConnector(verify_ssl=False)
        with aiohttp.ClientSession(connector=connector) as session:
            crawl_item.start()
            async with session.get(crawl_item.url) as response:
                await self._handle_response(crawl_item, response)

    async def run(self):
        self.is_running = True
        logger.debug('Downloader is starting...')

        while True:
            logger.debug('Waiting for download slot...')
            await self._download_slot.acquire()

            logger.debug('Waiting for next domain & URL...')
            crawl_item_future = asyncio.ensure_future(self._frontier.get_item())

            finished_future = asyncio.wait(
                (self._frontier.join(), self._downloader_finished)
            )

            done, pending = await asyncio.wait(
                (crawl_item_future, finished_future),
                return_when=asyncio.FIRST_COMPLETED
            )

            if crawl_item_future.done():
                crawl_item = crawl_item_future.result()
            else:
                crawl_item_future.cancel()
                break

            task = asyncio.ensure_future(self.fetch_item(crawl_item))

        logger.debug('Downloader has stopped.')
        self.is_running = False

    async def _handle_response(self, crawl_item, response):
        url = crawl_item.url
        status = response.status
        logger.info('{} {}'.format(status, url))
        body = await response.read()
        crawl_item.finish(status, response.headers, body)
        self._release_download_slot()

    def _release_download_slot(self):
        self._download_slot.release()
        self._download_count -= 1
        if self._download_count == 0:
            logger.debug('Downloader is out of downloads!')
            # TODO I've used this pattern of using a future to unblock a
            # coroutine in several places, but I think asyncio.Condition is
            # more appropriate.
            self._downloader_finished.set_result(None)
            self._downloader_finished = asyncio.Future()
