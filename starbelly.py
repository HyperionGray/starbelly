import asyncio
import base64
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


class Crawl:
    _next_id = 0
    _status_digit_to_name = {
        1: 'information',
        2: 'success',
        3: 'redirect',
        4: 'not_found',
        5: 'error',
    }

    @classmethod
    def next_id(cls):
        id_ = cls._next_id
        cls._next_id += 1
        return id_

    def __init__(self, seeds, downloader, frontier, max_depth=3):
        self.crawl_item_completed = PubSub()
        self.id_ = self.next_id()
        self.max_depth = max_depth
        self.stats_updated = PubSub()
        self.when_complete = asyncio.Future()

        self._completed_items = list()
        self._downloader = downloader
        self._frontier = frontier
        self._pending_items = set()
        self._seeds = seeds

        self.stats = {
            'seed': self._seeds[0], # TODO should store list of seeds
            'status': 'running',
            'information': 0,
            'success': 0,
            'redirect': 0,
            'not_found': 0,
            'error': 0,
        }

    def items(self, start_index):
        return self._completed_items[start_index:]

    async def run(self):
        logger.info('Crawl #{} starting...'.format(self.id_))
        for seed in self._seeds:
            crawl_item = CrawlItem(seed, depth=0)
            self._add_item(crawl_item, seed=True)

        if not self._downloader.is_running:
            asyncio.ensure_future(self._downloader.run())

        await self.when_complete
        logger.info('Crawl #{} complete.'.format(self.id_))

    def _add_item(self, crawl_item, seed=False):
        try:
            if seed:
                self._frontier.add_seed(crawl_item)
            else:
                self._frontier.add_item(crawl_item)
            self._pending_items.add(crawl_item)
            crawl_item.when_complete.add_done_callback(self._complete_item)
        except FrontierException:
            pass

    def _complete_item(self, crawl_item_future):
        crawl_item = crawl_item_future.result()
        self._pending_items.remove(crawl_item)
        self._completed_items.append(crawl_item)
        self._update_stats(crawl_item)
        self.crawl_item_completed.publish(crawl_item)

        if crawl_item.depth < self.max_depth:
            for new_url in self._parse_urls(crawl_item):
                parsed = urlparse(new_url)
                if parsed.path.endswith('.html'):
                    self._add_item(
                        CrawlItem(new_url, depth=crawl_item.depth + 1)
                    )

        if len(self._pending_items) == 0:
            self.when_complete.set_result(None)
            self.stats['status'] = 'complete'
            updates = {'status': 'complete'}
            self.stats_updated.publish(self, updates)

    def _parse_urls(self, crawl_item):
        doc = lxml.html.document_fromstring(crawl_item.body)
        for link in doc.iterlinks():
            new_url = urljoin(crawl_item.url, link[2])
            yield new_url

    def _update_stats(self, crawl_item):
        status_first_digit = crawl_item.status_code // 100
        stat_category = Crawl._status_digit_to_name[status_first_digit]
        self.stats[stat_category] += 1
        updates = {stat_category: self.stats[stat_category]}
        self.stats_updated.publish(self, updates)


class CrawlItem:
    def __init__(self, url, depth):
        self.body = None
        self.completed_at = None
        self.depth = depth
        self.headers = None
        self.parsed_url = urlparse(url)
        self.started_at = None
        self.status_code = None
        self.url = url
        self.when_complete = asyncio.Future()

    def finish(self, status_code, headers, body):
        self.body = body
        self.completed_at = time()
        self.duration = self.completed_at - self.started_at
        self.headers = headers
        self.status = 'complete'
        self.status_code = status_code
        self.when_complete.set_result(self)

    def start(self):
        self.started_at = time()


class CrawlListener:
    _next_id = 0

    @classmethod
    def next_id(cls):
        id_ = CrawlListener._next_id
        CrawlListener._next_id += 1
        return id_


class CrawlItemsListener(CrawlListener):

    def __init__(self, socket, crawl, sync_token=None):
        self.id_ = self.next_id()
        self._crawl = crawl
        self._queue = asyncio.Queue()
        self._socket = socket
        self._crawl.crawl_item_completed.listen(self._queue.put_nowait)

        # Decode sync token and immediately load any unsynced items from
        # the crawl into our local queue.
        if sync_token is None:
            self._index = 0
        else:
            self._index = int(base64.b64decode(sync_token))

        for item in self._crawl.items(self._index):
            self._queue.put_nowait(item)

        print('finished init, qsize={}'.format(self._queue.qsize()))

    async def run(self):
        while True:
            print('item listener: waiting for queue...')
            print(self._queue.qsize())
            crawl_item = await self._queue.get()
            print('after await')
            self._index += 1
            index_bytes = str(self._index).encode('utf8')
            sync_token = base64.b64encode(index_bytes).decode('utf8')
            body = base64.b64encode(crawl_item.body).decode('utf8')
            message = {
                'type': 'event',
                'subscription_id': self.id_,
                'data': {
                    'body': body,
                    'completed_at': crawl_item.completed_at,
                    'crawl_id': self._crawl.id_,
                    'depth': crawl_item.depth,
                    'duration': crawl_item.duration,
                    'headers': dict(crawl_item.headers),
                    'started_at': crawl_item.started_at,
                    'status_code': crawl_item.status_code,
                    'sync_token': sync_token,
                    'url': crawl_item.url,
                },
            }
            print('item listener: sending message'.format(message))
            await self._socket.send(json.dumps(message))


class CrawlStatsListener(CrawlListener):
    def __init__(self, socket, min_interval):
        self.id_ = self.next_id()
        self._has_update = asyncio.Future()
        self._min_interval = min_interval
        self._socket = socket
        self._stats = dict()

    def add_crawl(self, crawl):
        self._stats[crawl.id_] = dict(crawl.stats)
        crawl.stats_updated.listen(self._update_crawl_stats)

    def remove_crawl(self, crawl):
        crawl.stats_updated.cancel(self._update_crawl_stats)

    async def run(self):
        while True:
            if len(self._stats) > 0:
                message = {
                    'type': 'event',
                    'subscription_id': self.id_,
                    'data': dict(self._stats),
                }

                self._stats = dict()
                await self._socket.send(json.dumps(message))

            sleeper = asyncio.sleep(self._min_interval)
            await asyncio.wait((sleeper, self._has_update))

    def _update_crawl_stats(self, crawl, new_stats):
        if crawl.id_ not in self._stats:
            self._stats[crawl.id_] = new_stats
        else:
            self._stats[crawl.id_].update(new_stats)

        self._has_update.set_result(None)
        self._has_update = asyncio.Future()


class DomainRateLimiter:
    def __init__(self, default_interval=5):
        self._all_domains = set()
        self._domain_touched = asyncio.Future()
        self._intervals = defaultdict(lambda: default_interval)
        self._ready_domains = set()
        self._wait_domains = list()
        self._wait_times = list()

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
                await self._domain_touched
            else:
                delay = self._wait_times[0] - now
                sleeper = asyncio.ensure_future(asyncio.sleep(delay))
                await asyncio.wait(
                    [sleeper, self._domain_touched],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if not sleeper.done():
                    sleeper.cancel()

    def set_domain_limit(self, domain, interval):
        self._intervals[domain] = interval
        self._all_domains.add(domain)
        self._ready_domains.add(domain)

    def touch_domain(self, domain):
        interval = self._intervals[domain]

        if interval == 0:
            self._ready_domains.add(domain)
        else:
            next_time = time() + self._intervals[domain]
            index = bisect(self._wait_times, next_time)
            self._wait_times.insert(index, next_time)
            self._wait_domains.insert(index, domain)

        if not self._domain_touched.done():
            self._domain_touched.set_result(None)

        self._domain_touched = asyncio.Future()
        logger.debug('Touched domain {}'.format(domain))


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


class Frontier:
    def __init__(self, rate_limiter):
        self._domains = set()
        self._domain_queues = defaultdict(asyncio.Queue)
        self._queue_empty = asyncio.Future()
        self._queue_size = 0
        self._rate_limiter = rate_limiter
        self._seen = set()
        self._url_added = asyncio.Future()

    def add_item(self, crawl_item):
        url = crawl_item.url
        parsed = crawl_item.parsed_url
        domain = parsed.hostname
        normalized_url = '{}://{}{}?{}'.format(
            parsed.scheme, parsed.hostname, parsed.path, parsed.query
        )

        if domain not in self._domains or normalized_url in self._seen:
            raise FrontierException()

        logger.debug('Pushing {}'.format(url))
        self._domain_queues[domain].put_nowait(crawl_item)
        self._queue_size += 1
        self._seen.add(normalized_url)
        self._url_added.set_result(None)
        self._url_added = asyncio.Future()
        crawl_item.when_complete.add_done_callback(self.complete_item)

    def add_seed(self, crawl_item):
        self._domains.add(crawl_item.parsed_url.hostname)
        self.add_item(crawl_item)

    def complete_item(self, crawl_item_future):
        crawl_item = crawl_item_future.result()
        url = crawl_item.url
        domain = crawl_item.parsed_url.hostname
        self._domain_queues[domain].task_done()
        self._rate_limiter.touch_domain(domain)
        self._queue_size -= 1

        # Check if the queue is empty, but wait until after other callbacks on
        # crawl item have completed -- they may add more items to the queue.
        asyncio.get_event_loop().call_soon(self._check_queue_empty)

    async def get_item(self):
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
                    crawl_item = self._domain_queues[domain].get_nowait()
                except asyncio.QueueEmpty:
                    continue

                msg = 'Popping {} (depth={})'
                logger.debug(msg.format(crawl_item.url, crawl_item.depth))
                return crawl_item

    async def join(self):
        await self._queue_empty

    def _check_queue_empty(self):
        if self._queue_size == 0:
            self._queue_empty.set_result(None)
            self._queue_empty = asyncio.Future()


class FrontierException(Exception):
    pass


class PubSub:
    def __init__(self):
        self._callbacks = set()

    def cancel(self, callback):
        self._callbacks.remove(callback)

    def listen(self, callback):
        self._callbacks.add(callback)

    def publish(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


class Server:
    def __init__(self, host, port, frontier, downloader, rate_limiter):
        self._crawls = list()
        self._crawl_started = PubSub()
        self._downloader = downloader
        self._frontier = frontier
        self._host = host
        self._port = port
        self._rate_limiter = rate_limiter
        self._subscriptions = dict()

        self._handlers = {
            'start_crawl': self._start_crawl,
            'subscribe_crawl_items': self._subscribe_crawl_items,
            'subscribe_crawl_stats': self._subscribe_crawl_stats,
            'unsubscribe': self._unsubscribe,
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
                args['socket'] = websocket

                response = {
                    'command_id': request['command_id'],
                    'type': 'response',
                }

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
            except asyncio.CancelledError:
                msg = 'Connection handler canceled; closing socket {}:{}.'
                logger.info(msg.format(
                    websocket.remote_address[0],
                    websocket.remote_address[1],
                ))
                try:
                    await websocket.close()
                except websockets.exceptions.InvalidState:
                    pass

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

    def _start_crawl(self, socket, seeds):
        seed_urls = list()

        for seed in seeds:
            url = seed['url']
            seed_urls.append(url)
            rate_limit = seed.get('rate_limit', None)

            if rate_limit.strip() != '':
                rate_limit = float(rate_limit)
                parsed = urlparse(url)
                self._rate_limiter.set_domain_limit(parsed.hostname, rate_limit)

        crawl = Crawl(seed_urls, downloader, frontier)
        asyncio.ensure_future(crawl.run())
        self._crawls.append(crawl)
        self._crawl_started.publish(crawl)
        return {'crawl_id': crawl.id_}

    def _subscribe_crawl_items(self, socket, crawl_id, sync_token=None):
        crawl_id = int(crawl_id)
        matching_crawls = [c for c in self._crawls if c.id_ == crawl_id]

        if len(matching_crawls) != 1:
            msg = 'Crawl ID={} matched {} crawls! (expected 1)'
            raise ValueError(msg.format(crawl_id, len(matching_crawls)))

        crawl = matching_crawls[0]
        subscription = CrawlItemsListener(socket, crawl, sync_token)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _subscribe_crawl_stats(self, socket, min_interval=1):
        subscription = CrawlStatsListener(socket, min_interval)

        for crawl in self._crawls:
            subscription.add_crawl(crawl)

        def add_crawl(crawl):
            subscription.add_crawl(crawl)

        self._crawl_started.listen(add_crawl)
        coro = asyncio.ensure_future(subscription.run())
        self._subscriptions[subscription.id_] = coro
        return {'subscription_id': subscription.id_}

    def _unsubscribe(self, socket, subscription_id):
        subscription_id = int(subscription_id)
        self._subscriptions[subscription_id].cancel()
        return {'subscription_id': subscription_id}


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
