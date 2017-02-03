import asyncio
import base64
import json
import logging
from time import time
from urllib.parse import urljoin, urlparse

import lxml.html

from . import handle_future_exception
from .frontier import Frontier
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class CrawlJob:
    ''' Implements core crawling behavior and state. '''

    _running_jobs = dict()

    _next_id = 0
    _status_digit_to_name = {
        1: 'information',
        2: 'success',
        3: 'redirect',
        4: 'not_found',
        5: 'error',
    }

    def __init__(self, downloader, rate_limiter, seeds, max_depth=3):
        ''' Constructor. '''
        self.crawl_item_completed = PubSub()
        self.id_ = self.next_id()
        self.max_depth = max_depth
        self.status_updated = PubSub()
        self.seeds = seeds

        self._completed_items = list() # TODO will replace with DB
        self._downloader = downloader
        self._download_tasks = dict()
        self._frontier = Frontier(rate_limiter)
        self._running = False

        self.status = {
            'seed': self.seeds[0], # TODO should store list of seeds
            'status': 'running',
            'information': 0,
            'success': 0,
            'redirect': 0,
            'not_found': 0,
            'error': 0,
        }

    @classmethod
    def next_id(cls):
        ''' Generate a unique ID for each crawl instance. '''
        id_ = cls._next_id
        cls._next_id += 1
        return id_

    @classmethod
    def pause_all_jobs(cls):
        '''
        Pause all currently running jobs.

        This will allow current downloads to finish.
        '''

        running_jobs = list(cls._running_jobs.values())

        for job in running_jobs:
            job.cancel()

        return asyncio.gather(
            *running_jobs,
            return_exceptions=True
        )

    def items(self, start_index):
        ''' Retrieve items from this crawl, beginning at ``start_index``. '''
        return self._completed_items[start_index:]

    def start(self):
        '''
        Starts the crawl.

        Returns a future that fires when the crawl finishes.
        '''
        task = asyncio.ensure_future(self._run())
        self.__class__._running_jobs[self] = task
        handle_future_exception(task)
        return task

    def _handle_download(self, crawl_item_future):
        ''' Called when a download finishes. '''

        crawl_item = crawl_item_future.result()

        if crawl_item.exception is None:
            status_first_digit = crawl_item.status_code // 100
            status_category = self.__class__._status_digit_to_name[status_first_digit]
            self.status[status_category] += 1
            updates = {status_category: self.status[status_category]}
            self.status_updated.publish(self, updates)
            self._completed_items.append(crawl_item)
            self.crawl_item_completed.publish(crawl_item)

            if self._running and crawl_item.depth < self.max_depth:
                for new_url in self._parse_urls(crawl_item):
                    parsed = urlparse(new_url)
                    if parsed.path.endswith('.html'):
                        self._frontier.add_item(
                            CrawlItem(new_url, depth=crawl_item.depth + 1)
                        )

        del self._download_tasks[crawl_item]
        self._frontier.complete_item(crawl_item)

    def _parse_urls(self, crawl_item):
        '''
        Extract links from a crawl item.

        TODO move into new link extractor class
        '''
        doc = lxml.html.document_fromstring(crawl_item.body)
        for link in doc.iterlinks():
            new_url = urljoin(crawl_item.url, link[2])
            yield new_url

    async def _run(self):
        '''
        Main crawling logic.

        Returns when the crawl is finished.
        '''

        logger.info('Crawl #{} starting...'.format(self.id_))

        for seed in self.seeds:
            self._frontier.add_item(CrawlItem(seed, depth=0))

        self._running = True

        try:
            while self._running:
                crawl_item = await self._frontier.get_item()
                dl_task = await self._downloader.schedule_download(crawl_item)
                dl_task.add_done_callback(self._handle_download)
                self._download_tasks[crawl_item] = dl_task

                if len(self._frontier) == 0 and len(self._download_tasks) == 0:
                    logger.debug('Crawl #{} is complete.'.format(self._id_))
                    del self.__class__._running_jobs[self]
                    self.status['status'] = 'complete'
                    self.status_updated.publish(self, {'status': 'complete'})
                    self._running = False
        except asyncio.CancelledError:
            logger.info('Crawl #{} is pausing...'.format(self.id_))
            if len(self._download_tasks) > 0:
                logger.info(
                    'Crawl #{} is waiting for {} downloads to finish...'
                    .format(self.id_, len(self._download_tasks))
                )
                await asyncio.gather(*self._download_tasks.values())
                logger.info('Crawl #{} is pausing...'.format(self.id_))

                self.status['status'] = 'paused'
                self.status_updated.publish(self, {'status': 'paused'})

        logger.info('Crawl #{} has stopped.'.format(self.id_))
        del self.__class__._running_jobs[self]


class CrawlItem:
    ''' Represents a resource to be crawled and the result of crawling it. '''

    def __init__(self, url, depth):
        ''' Constructor. '''
        self.body = None
        self.completed_at = None
        self.depth = depth
        self.exception = None
        self.headers = None
        self.parsed_url = urlparse(url)
        self.started_at = None
        self.status_code = None
        self.url = url

    def finish(self, status_code, headers, body):
        ''' Update with crawl result. '''
        self.body = body
        self.completed_at = time()
        self.duration = self.completed_at - self.started_at
        self.headers = headers
        self.status = 'complete'
        self.status_code = status_code

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
        self._has_update = asyncio.Event()
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
            done, pending = await asyncio.wait((sleeper, self._has_update.wait()))
            for p in pending:
                p.cancel()
            self._has_update.clear()

    def _update_crawl_status(self, crawl, new_status):
        ''' Merge new crawl status into existing crawl status. '''
        if crawl.id_ not in self._status:
            self._status[crawl.id_] = new_status
        else:
            self._status[crawl.id_].update(new_status)

        self._has_update.set()
