import asyncio
import logging
from collections import defaultdict


logger = logging.getLogger(__name__)


class Frontier:
    '''
    Manages the crawl queue, i.e. items that are planned to be downloaded.

    TODO: implement a persistent queue.
    '''

    def __init__(self, rate_limiter):
        ''' Constructor. '''
        self._domain_queues = defaultdict(asyncio.Queue)
        self._queue_has_url = asyncio.Event()
        self._queue_size = 0
        self._rate_limiter = rate_limiter
        self._seen = set()

    def __len__(self):
        ''' Frontier length is the number of items in the queue. '''
        return self._queue_size

    def add_item(self, crawl_item):
        ''' Add an item to be downloaded. '''
        url = crawl_item.url
        parsed = crawl_item.parsed_url
        domain = parsed.hostname
        normalized_url = '{}://{}{}?{}'.format(
            parsed.scheme, parsed.hostname, parsed.path, parsed.query
        )

        # TODO remove: this will be handled by a crawl policy
        if normalized_url in self._seen:
            return

        logger.debug('Pushing {}'.format(url))
        self._domain_queues[domain].put_nowait(crawl_item)
        self._queue_size += 1
        self._seen.add(normalized_url)
        self._queue_has_url.set()

    def complete_item(self, crawl_item):
        ''' Mark an item in the frontier as being completed. '''
        url = crawl_item.url
        domain = crawl_item.parsed_url.hostname
        self._domain_queues[domain].task_done()
        self._rate_limiter.touch_domain(domain)

    async def get_item(self):
        ''' Select the next item to download from the queue. '''
        while True:
            await self._queue_has_url.wait()
            choices = [d for d,q in self._domain_queues.items() if q.qsize() > 0]
            domain = await self._rate_limiter.select_domain(choices)

            try:
                crawl_item = self._domain_queues[domain].get_nowait()
                self._queue_size -= 1

                if self._queue_size == 0:
                    self._queue_has_url.clear()
            except asyncio.QueueEmpty:
                continue

            msg = 'Popping {} (depth={})'
            logger.debug(msg.format(crawl_item.url, crawl_item.depth))
            return crawl_item
