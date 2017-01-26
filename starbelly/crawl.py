import asyncio
import base64
import json
import logging
from time import time
from urllib.parse import urljoin, urlparse

import lxml.html

from .frontier import FrontierException
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class Crawl:
    ''' Represents the state of a crawl. '''

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
        ''' Generate a unique ID for each crawl instance. '''
        id_ = cls._next_id
        cls._next_id += 1
        return id_

    def __init__(self, seeds, downloader, frontier, max_depth=3):
        ''' Constructor. '''
        self.crawl_item_completed = PubSub()
        self.id_ = self.next_id()
        self.max_depth = max_depth
        self.status_updated = PubSub()
        self.when_complete = asyncio.Future()

        self._completed_items = list()
        self._downloader = downloader
        self._frontier = frontier
        self._pending_items = set()
        self._seeds = seeds

        self.status = {
            'seed': self._seeds[0], # TODO should store list of seeds
            'status': 'running',
            'information': 0,
            'success': 0,
            'redirect': 0,
            'not_found': 0,
            'error': 0,
        }

    def items(self, start_index):
        ''' Retrive items from this crawl, beginning at ``start_index``. '''
        return self._completed_items[start_index:]

    async def run(self):
        ''' Start running a crawl. '''
        logger.info('Crawl #{} starting...'.format(self.id_))
        for seed in self._seeds:
            crawl_item = CrawlItem(seed, depth=0)
            self._add_item(crawl_item, seed=True)

        if not self._downloader.is_running:
            asyncio.ensure_future(self._downloader.run())

        await self.when_complete
        logger.info('Crawl #{} complete.'.format(self.id_))

    def _add_item(self, crawl_item, seed=False):
        ''' Add an item to be crawled. '''
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
        ''' Update state after successfully crawling an item. '''
        crawl_item = crawl_item_future.result()
        self._pending_items.remove(crawl_item)
        self._completed_items.append(crawl_item)
        self._update_status(crawl_item)
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
            self.status['status'] = 'complete'
            updates = {'status': 'complete'}
            self.status_updated.publish(self, updates)

    def _parse_urls(self, crawl_item):
        ''' Extract links from a crawl item. '''
        doc = lxml.html.document_fromstring(crawl_item.body)
        for link in doc.iterlinks():
            new_url = urljoin(crawl_item.url, link[2])
            yield new_url

    def _update_status(self, crawl_item):
        ''' Update crawl status. '''
        status_first_digit = crawl_item.status_code // 100
        status_category = Crawl._status_digit_to_name[status_first_digit]
        self.status[status_category] += 1
        updates = {status_category: self.status[status_category]}
        self.status_updated.publish(self, updates)


class CrawlItem:
    ''' Represents a resource to be crawled and the result of crawling it. '''

    def __init__(self, url, depth):
        ''' Constructor. '''
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
        ''' Update with crawl result. '''
        self.body = body
        self.completed_at = time()
        self.duration = self.completed_at - self.started_at
        self.headers = headers
        self.status = 'complete'
        self.status_code = status_code
        self.when_complete.set_result(self)

    def start(self):
        '''
        This method should be called when the network request for the resource
        is sent.
        '''
        self.started_at = time()


class CrawlListener:
    ''' A base class for implementing a subscription stream. '''
    _next_id = 0

    @classmethod
    def next_id(cls):
        ''' Generate a unique ID for a crawl listener. '''
        id_ = CrawlListener._next_id
        CrawlListener._next_id += 1
        return id_


class CrawlItemsListener(CrawlListener):
    ''' A subscription stream that emits each item as it is crawled. '''

    def __init__(self, socket, crawl, sync_token=None):
        ''' Constructor. '''
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

    async def run(self):
        ''' Start the subscription. '''
        while True:
            crawl_item = await self._queue.get()
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
            await self._socket.send(json.dumps(message))


class CrawlStatusListener(CrawlListener):
    '''
    A subscription stream that emits updates about the status of one or more
    crawls.

    The first emitted event will contain the complete status of the crawl;
    subsequent events will only include fields that have changed since the
    previous event.
    '''

    def __init__(self, socket, min_interval):
        ''' Constructor. '''
        self.id_ = self.next_id()
        self._has_update = asyncio.Future()
        self._min_interval = min_interval
        self._socket = socket
        self._status = dict()

    def add_crawl(self, crawl):
        ''' Add a crawl to this subscription. '''
        self._status[crawl.id_] = dict(crawl.status)
        crawl.status_updated.listen(self._update_crawl_status)

    def remove_crawl(self, crawl):
        ''' Remove a crawl from this subscription. '''
        crawl.status_updated.cancel(self._update_crawl_status)

    async def run(self):
        ''' Start the subscription stream. '''
        while True:
            if len(self._status) > 0:
                message = {
                    'type': 'event',
                    'subscription_id': self.id_,
                    'data': dict(self._status),
                }

                self._status = dict()
                await self._socket.send(json.dumps(message))

            sleeper = asyncio.sleep(self._min_interval)
            await asyncio.wait((sleeper, self._has_update))

    def _update_crawl_status(self, crawl, new_status):
        ''' Merge new crawl status into existing crawl status. '''
        if crawl.id_ not in self._status:
            self._status[crawl.id_] = new_status
        else:
            self._status[crawl.id_].update(new_status)

        self._has_update.set_result(None)
        self._has_update = asyncio.Future()
