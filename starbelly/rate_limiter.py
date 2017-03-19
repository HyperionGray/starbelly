import asyncio
from collections import deque, namedtuple
import hashlib
from heapq import heappop, heappush
import logging
from time import time
import urllib.parse

from . import cancel_futures


logger = logging.getLogger(__name__)
Expiry = namedtuple('TokenExpiry', ['time', 'token'])


class RateLimiter:
    '''
    This class is responsible for enforcing rate limits.

    The rate limiter acts as a bottleneck between the multiple crawl frontiers
    and the downloader, enforcing the configured rate limits.

    A queue is maintained for each domain that has pending requests to it. When
    a rate limit expires for a given domain, the next URL in the corresponding
    domain queue is sent to the downloader. (If the domain queue is empty, the
    queue is deleted.) The rate limiter has a fixed capacity; when the number
    of URLs buffered in the rate limiter exceeds this capacity, subsequent calls
    to ``add()`` will block until some capacity is available; these calls will
    be served in the order they are made.

    In order to provide some flexibility, rate limits are not strictly tied
    to individual domains. Each URL is mapped to a "rate limit token". URLs
    with the same token will be placed into the same queue. This system will
    allow a flexible rate limiting policies in the future, such as applying a
    single rate limit to a set of domains.
    '''

    def __init__(self, downloader, capacity=1e4, default_limit=1):
        ''' Constructor. '''
        self._default_limit = default_limit
        self._downloader = downloader
        self._expires = list()
        self._expiry_added = asyncio.Event()
        self._queues = dict()
        self._rate_limits = dict()
        self._semaphore = asyncio.Semaphore(capacity)

    async def push(self, crawl_item):
        '''
        Schedule a crawl item for downloading.

        Suspends if the rate limiter is already filled to capacity.
        '''
        await self._semaphore.acquire()
        token = self._get_token_for_url(crawl_item.url)
        if token not in self._queues:
            self._queues[token] = deque()
            self._add_expiry(Expiry(time(), token))
        self._queues[token].append(crawl_item)

    def remove_limit(self, domain):
        ''' Remove a rate limit. '''
        token = self._get_token_for_domain(domain)
        del self._rate_limits[token]

    async def remove_job(self, job_id, finish_downloads=True):
        '''
        Remove all pending items for the given job.

        If ``finish_downloads`` is ``True``, this will wait until the downloader
        finishes any downloads it has started for this job. Otherwise, download
        tasks are canceled, too.
        '''

        # Copy all existing queues to new queues but drop items matching the
        # given job_id. This is faster than modifying queues in-place.
        new_queues = dict()
        removed_items = list()

        for token, old_deque in self._queues.items():
            new_deque = deque()

            for item in old_deque:
                if item.job_id == job_id:
                    removed_items.append(item)
                else:
                    new_deque.append(item)

            new_queues[token] = new_deque

        self._queues = new_queues

        # Ask the download to remove this job.
        await self._downloader.remove_job(job_id, finish_downloads)

        # Return the removed items so the crawl job can place them back into
        # the frontier.
        return removed_items

    async def run(self):
        '''
        Schedule items for download.

        Maintains the invariant that if a token exists in the ``_expires`` heap,
        then a queue exists for that token.
        '''

        logger.info('Rate limiter is running.')

        try:
            while True:
                # Get the next token and then get the next item for that token.
                expiry = await self._get_next_expiry()
                token = expiry.token
                queue = self._queues[token]

                if len(queue) == 0:
                    # If nothing left in this queue, delete it and get another
                    # token instead.
                    del self._queues[token]
                    continue

                crawl_item = queue.popleft()
                logger.debug('Popped %s', crawl_item.url)
                await self._downloader.push(crawl_item)
                self._semaphore.release()
                crawl_item.completed.add_done_callback(self._reschedule)
        except asyncio.CancelledError:
            # Cancellation is okay.
            raise
        finally:
            logger.info('Rate limiter has stopped.')

    def set_limit(self, domain, interval):
        ''' Set a rate limit. '''
        token = self._get_token_for_domain(domain)
        self._rate_limits[token] = interval

    def _add_expiry(self, expiry):
        ''' Add the specified expiry to the heap. '''
        heappush(self._expires, expiry)
        self._expiry_added.set()

    async def _get_next_expiry(self):
        '''
        Pop an expiry off the heap.

        If no tokens on heap, suspend until a token is available.
        '''

        # Peek at the next expiration.
        if len(self._expires) == 0:
            await self._expiry_added.wait()
            self._expiry_added.clear()

        while True:
            now = time()
            expires = self._expires[0].time

            if expires <= now:
                # The next expiry is in the past, so we can pop it right now.
                break
            else:
                # The next expiry is in the future, so wait for it but also can
                # be interrupted if somebody adds a new expiry to the heap.
                try:
                    await asyncio.wait_for(
                        self._expiry_added.wait(),
                        timeout=expires - now
                    )
                    self._expiry_added.clear()
                except asyncio.TimeoutError:
                    # The next item on the heap is ready to pop.
                    break

        expiry = heappop(self._expires)
        return expiry

    def _get_token_for_domain(self, domain):
        ''' Get a token for a domain. '''
        hash_ = hashlib.blake2b(domain.encode('ascii'), digest_size=16)
        token = hash_.digest()
        return token

    def _get_token_for_url(self, url):
        ''' Return the token for the domain in ``url``. '''
        parsed = urllib.parse.urlparse(url)
        token = self._get_token_for_domain(parsed.hostname)
        return token

    def _reschedule(self, crawl_item_future):
        ''' When an item finishes, re-schedule its token. '''
        crawl_item = crawl_item_future.result()
        token = self._get_token_for_url(crawl_item.url)
        limit = self._rate_limits.get(token, self._default_limit)
        self._add_expiry(Expiry(time() + limit, token))
