import asyncio
from bisect import bisect
from collections import defaultdict
from io import BytesIO
import logging
import sys
from time import time
from urllib.parse import urljoin, urlparse

import aiohttp
import lxml.html


log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'
log_formatter = logging.Formatter(log_format, log_date_format)
log_handler = logging.StreamHandler(sys.stderr)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.addHandler(log_handler)


class DomainRateLimiter():
    def __init__(self, domain_intervals, default_interval=5):
        self._all_domains = set()
        self._intervals = defaultdict(lambda: default_interval)
        self._ready_domains = set()
        self._url_finished = asyncio.Future()
        self._wait_domains = list()
        self._wait_times = list()

        for domain, interval in domain_intervals.items():
            self._intervals[domain] = interval
            self._all_domains.add(domain)
            self._ready_domains.add(domain)

    async def select_domain(self, choices):
        # Add any domains that we don't already know about.
        new_domains = choices - self._all_domains
        self._all_domains.update(new_domains)
        self._ready_domains.update(new_domains)

        while True:
            # Peel off all domains that have become ready.
            now = time()
            while len(self._wait_times) > 0 and now >= self._wait_times[0]:
                self._wait_times.pop(0)
                self._ready_domains.add(self._wait_domains.pop(0))

            logger.debug('Domains choices: {}'.format(choices))
            logger.debug('Domains ready: {}'.format(self._ready_domains))
            logger.debug('Current time: {}'.format(time()))
            logger.debug('Domains pending: {}'.format(
                list(zip(self._wait_domains, self._wait_times))
            ))

            # Use a ready domain if possible.
            #
            # TODO: there should be a more orderly way to pick from several
            # ready domains, e.g. the one that was least recently used, in order
            # to ensure all domains are treated equally.
            try:
                domain = (self._ready_domains & choices).pop()
                self._ready_domains.remove(domain)
                logger.debug('Selected domain {}'.format(domain))
                return domain
            except KeyError as e:
                pass

            # Wait until the next domain becomes ready.
            logger.debug('No domains available! Waiting for a rate limit to expire...')
            if len(self._wait_times) == 0:
                await self._url_finished
            else:
                delay = self._wait_times[0] - now
                sleeper = asyncio.ensure_future(asyncio.sleep(delay))
                await asyncio.wait(
                    [sleeper, self._url_finished],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if not sleeper.done():
                    sleeper.cancel()

    def finish_url(self, url):
        domain = urlparse(url).hostname
        next_time = time() + self._intervals[domain]
        index = bisect(self._wait_times, next_time)
        self._wait_times.insert(index, next_time)
        self._wait_domains.insert(index, domain)
        self._url_finished.set_result(None)
        self._url_finished = asyncio.Future()

        logger.debug('Touched {}'.format(url))


class Frontier:
    def __init__(self, rate_limiter, seeds):
        self._domains = set()
        self._domain_queues = defaultdict(asyncio.PriorityQueue)
        self._queue_empty = asyncio.Future()
        self._queue_size = 0
        self._rate_limiter = rate_limiter
        self._seen = set()
        self._url_added = asyncio.Future()

        for seed in seeds:
            domain = urlparse(seed).hostname
            self._domains.add(domain)
            self._domain_queues[domain].put_nowait(seed)

    def add_url(self, url):
        domain = urlparse(url).hostname

        if domain in self._domains and url.endswith('.html') and \
           url not in self._seen:

            logger.debug('Pushing {}'.format(url))
            self._domain_queues[domain].put_nowait(url)
            self._queue_size += 1
            self._seen.add(url)
            self._url_added.set_result(None)
            self._url_added = asyncio.Future()

    def finish_url(self, url):
        domain = urlparse(url).hostname
        self._domain_queues[domain].task_done()
        self._rate_limiter.finish_url(url)
        self._queue_size -= 1

        if self._queue_size == 0:
            self._queue_empty.set_result(None)
            self._queue_empty = asyncio.Future()

    async def get_url(self):
        while True:
            choices = {d for d,q in self._domain_queues.items() if q.qsize() > 0}
            domain_future = asyncio.ensure_future(
                self._rate_limiter.select_domain(choices)
            )
            pending, done = await asyncio.wait(
                (domain_future, self._url_added),
                return_when=asyncio.FIRST_COMPLETED
            )

            if not domain_future.done():
                domain_future.cancel()
                continue
            else:
                domain = domain_future.result()

                try:
                    url = self._domain_queues[domain].get_nowait()
                except asyncio.QueueEmpty:
                    continue

                logger.debug('Popping {}'.format(url))
                return url

    async def join(self):
        await self._queue_empty


class Downloader:
    def __init__(self, frontier, concurrent=10):
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

            logger.debug('Waiting for next domain & URL...')
            url_future = asyncio.ensure_future(self._frontier.get_url())

            finished_future = asyncio.wait(
                (self._frontier.join(), self._downloader_finished)
            )

            done, pending = await asyncio.wait(
                (url_future, finished_future),
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
        logger.info('{} {}'.format(response.status, url))
        body = await response.read()

        for new_url in self._parse_urls(url, body):
            self._frontier.add_url(new_url)

        self._release_download_slot()
        self._frontier.finish_url(url)

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

    # Configure rate limits for each domain. These are the minimum elapsed time
    # (in seconds) between requests to the same domain.
    rate_limiter = DomainRateLimiter({
        'markhaa.se': 2,
        'blog.notmyidea.org': 3,
        'dirkjan.ochtman.nl': 4,
    })

    seeds = [
        'https://markhaa.se',
        'https://blog.notmyidea.org',
        'https://dirkjan.ochtman.nl',
        'http://azizmb.in',
    ]

    frontier = Frontier(rate_limiter, seeds)
    downloader = Downloader(frontier)
    loop = asyncio.get_event_loop()
    logger.info('Starting crawler')
    loop.run_until_complete(downloader.run())
    logger.info('Crawler stopped')
    loop.close()
