import asyncio
import logging
from collections import defaultdict


logger = logging.getLogger(__name__)


class FrontierException(Exception):
    ''' A generic exception that occurs in a ``Frontier`` instance. '''
    pass


class Frontier:
    '''
    Manages the crawl queue, i.e. items that are planned to be downloaded.
    '''

    def __init__(self, rate_limiter):
        ''' Constructor. '''
        self._domains = set()
        self._domain_queues = defaultdict(asyncio.Queue)
        self._queue_empty = asyncio.Future()
        self._queue_size = 0
        self._rate_limiter = rate_limiter
        self._seen = set()
        self._url_added = asyncio.Future()

    def add_item(self, crawl_item):
        ''' Add an item to be downloaded. '''
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
        ''' Add a crawl seed to be downloaded. '''
        self._domains.add(crawl_item.parsed_url.hostname)
        self.add_item(crawl_item)

    def complete_item(self, crawl_item_future):
        ''' Mark an item in the frontier as being completed. '''
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
        ''' Select the next item to download from the queue. '''
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
        ''' Wait until the crawl queue is empty. '''
        await self._queue_empty

    def _check_queue_empty(self):
        ''' If the queue is empty, trigger the ``_queue_empty`` future. '''
        if self._queue_size == 0:
            self._queue_empty.set_result(None)
            self._queue_empty = asyncio.Future()
