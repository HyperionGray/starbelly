import asyncio
from collections import deque, namedtuple
import hashlib
from heapq import heappop, heappush
import logging
from time import time
import urllib.parse

from . import raise_future_exception


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
        self._queues = dict()
        self._rate_limits = dict()
        self._semaphore = asyncio.Semaphore(capacity)
        self._task = None
        self._token_added = asyncio.Event()

    async def push(self, crawl_item):
        '''
        Schedule a crawl item for downloading.

        Suspends if the rate limiter is already filled to capacity.
        '''
        await self._semaphore.acquire()
        token = self._get_token_for_url(crawl_item.url)
        if token not in self._queues:
            self._queues[token] = deque()
            heappush(self._expires, (Expiry(time(), token)))
            self._token_added.set()
        self._queues[token].append(crawl_item)

    def remove_limit(self, domain):
        ''' Remove a rate limit. '''
        token = self._get_token_for_domain(domain)
        del self._rate_limits[token]

    def set_limit(self, domain, interval):
        ''' Set a rate limit. '''
        token = self._get_token_for_domain(domain)
        self._rate_limits[token] = interval

    def start(self):
        ''' Start the rate limiter task. '''
        logger.info('Rate limiter is starting...')
        self._task = asyncio.ensure_future(self._run())
        raise_future_exception(self._task)

    async def stop(self):
        ''' Stop the rate limiter task. '''
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        logger.info('Rate limiter has stopped.')

    async def _get_next_expiry(self):
        '''
        Pop an expiry off the heap.

        If no tokens on heap, suspend until a token is available.
        '''
        # Peek at the next expiration.
        if len(self._expires) == 0:
            await self._token_added.wait()
            self._token_added.clear()

        now = time()
        expires = self._expires[0].time

        # If the next expiry is in the future, then wait for expiration but
        # interrupt if a new token is added to the heap.
        if expires > now:
            try:
                await asyncio.wait_for(
                    self._token_added.wait(),
                    timeout=expires - now
                )
                self._token_added.clear()
            except asyncio.TimeoutError:
                pass

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

    async def _run(self):
        '''
        Schedule items for download.

        Maintains the invariant that for every token in the heap, there is a
        corresponding queue.
        '''

        logger.info('Rate limiter is running.')

        while True:
            # Get the next token and then get the next item for that token.
            expiry = await self._get_next_expiry()
            token = expiry.token
            queue = self._queues[token]

            if len(queue) == 0:
                # If nothing left in this queue, delete it and get another token
                # instead.
                del self._queues[token]
                continue

            crawl_item = queue.popleft()
            logger.debug('Popped %s', crawl_item.url)
            await self._downloader.push(crawl_item)
            self._semaphore.release()

            # Schedule next expiration.
            limit = self._rate_limits.get(token, self._default_limit)
            expires = time() + limit
            heappush(self._expires, (Expiry(expires, token)))
