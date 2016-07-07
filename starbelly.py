import asyncio
from bisect import bisect
from collections import defaultdict
import json
from io import BytesIO
import logging
import sys
from time import time
from urllib.parse import urljoin, urlparse

import aiohttp
import lxml.html
import websockets


log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'
log_formatter = logging.Formatter(log_format, log_date_format)
log_handler = logging.StreamHandler(sys.stderr)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.addHandler(log_handler)


class DomainRateLimiter():
    def __init__(self, default_interval=5):
        self._all_domains = set()
        self._intervals = defaultdict(lambda: default_interval)
        self._ready_domains = set()
        self._url_finished = asyncio.Future()
        self._wait_domains = list()
        self._wait_times = list()

    def finish_url(self, url):
        domain = urlparse(url).hostname
        next_time = time() + self._intervals[domain]
        index = bisect(self._wait_times, next_time)
        self._wait_times.insert(index, next_time)
        self._wait_domains.insert(index, domain)
        self._url_finished.set_result(None)
        self._url_finished = asyncio.Future()

        logger.debug('Touched {}'.format(url))

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

    def set_domain(self, domain, interval):
        self._intervals[domain] = interval
        self._all_domains.add(domain)
        self._ready_domains.add(domain)


class Frontier:
    def __init__(self, rate_limiter):
        self._domains = set()
        self._domain_queues = defaultdict(asyncio.PriorityQueue)
        self._queue_empty = asyncio.Future()
        self._queue_size = 0
        self._rate_limiter = rate_limiter
        self._seen = set()
        self._url_added = asyncio.Future()

    def add_seed(self, seed):
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
        self.is_running = False

    async def get(self, url):
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self._download_count += 1
        with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(url) as response:
                await self._handle_response(url, response)

    async def run(self):
        self.is_running = True
        logger.debug('Downloader is starting...')

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

        logger.debug('Downloader has stopped.')
        self.is_running = False

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


class Server:
    def __init__(self, host, port, frontier, downloader, rate_limiter):
        self._downloader = downloader
        self._frontier = frontier
        self._host = host
        self._port = port
        self._rate_limiter = rate_limiter

        self._handlers = {
            'start_crawl': self._start_crawl,
        }

    async def handle_connection(self, websocket, path):
        logger.info('Websocket connection from {}:{}, path={}'.format(
            websocket.remote_address[0],
            websocket.remote_address[1],
            path
        ))
        while True:
            try:
                request = json.loads(await websocket.recv())
                logger.debug('Received command: '.format(request))
                command = request['command']
                args = request['args']
                response = {'id': request['id'], 'type': 'response'}
                try:
                    response['data'] = await self._dispatch_command(
                        self._handlers[command],
                        args
                    )
                    response['success'] = True
                except Exception as e:
                    if isinstance(e, KeyError):
                        msg = 'Invalid command: {}'
                        response['error'] = msg.format(command)
                    else:
                        response['error'] = str(e)
                    response['success'] = False
                    msg = 'Error while handling request: {}'
                    logger.exception(msg.format(request))
                await websocket.send(json.dumps(response))
            except websockets.exceptions.ConnectionClosed:
                logger.info('Connection closed: {}:{}'.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                return

    def start(self):
        return websockets.serve(
            self.handle_connection,
            self._host,
            self._port
        )

    async def _dispatch_command(self, handler, args):
        if asyncio.iscoroutine(handler):
            return await handler(**args)
        else:
            return handler(**args)

    def _start_crawl(self, seeds):
        # Add to frontier.
        for seed in seeds:
            url = seed['url']
            rate_limit = seed.get('rate_limit', None)

            if rate_limit is not None:
                rate_limit = float(rate_limit)
                parsed = urlparse(url)
                self._rate_limiter.set_domain(parsed.hostname, rate_limit)

            self._frontier.add_seed(url)

        # Make sure the downloader is running.
        if not self._downloader.is_running:
            asyncio.ensure_future(self._downloader.run())

        return 'Crawling from {} seeds'.format(len(seeds))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    rate_limiter = DomainRateLimiter()
    frontier = Frontier(rate_limiter)
    downloader = Downloader(frontier)
    server = Server('localhost', 8001, frontier, downloader, rate_limiter)

    loop = asyncio.get_event_loop()
    logger.info('Starting server')
    loop.run_until_complete(server.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info('Received interrupt... trying graceful shutdown.')
        remaining_tasks = asyncio.Task.all_tasks()
        for task in remaining_tasks:
            task.cancel()
        if len(remaining_tasks) > 0:
            loop.run_until_complete(asyncio.wait(remaining_tasks))

    loop.close()
    logger.info('Server is stopped.')

