import asyncio
from collections import deque, namedtuple
import hashlib
from heapq import heappop, heappush
import logging
from time import time
import urllib.parse

import rethinkdb as r

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

    def __init__(self, db_pool, capacity=1e4):
        ''' Constructor. '''
        self._db_pool = db_pool
        self._expires = list()
        self._expiry_added = asyncio.Event()
        self._global_limit = None
        self._queues = dict()
        self._rate_limits = dict()
        self._semaphore = asyncio.Semaphore(capacity)

    async def get_limits(self, limit, skip):
        ''' Return a list of rate limits ordered by name. '''
        count_query = r.table('rate_limit').count()
        item_query = (
            r.table('rate_limit')
             .order_by(index='name')
             .skip(skip)
             .limit(limit)
        )

        rate_limits = list()

        async with self._db_pool.connection() as conn:
            count = await count_query.run(conn)
            cursor = await item_query.run(conn)
            async for rate_limit in cursor:
                rate_limits.append(rate_limit)
            await cursor.close()

        return count, rate_limits

    async def get_next_request(self):
        '''
        Get the next download request from this rate limiter.

        Maintains the invariant that if a token exists in the ``_expires`` heap,
        then a queue exists for that token.
        '''
        # Get the next token and then get the next item for that token.
        expiry = await self._get_next_expiry()
        token = expiry.token
        queue = self._queues[token]

        if len(queue) == 0:
            # If nothing left in this queue, delete it and get another
            # token instead.
            del self._queues[token]
            request = await self.get_next_request()
        else:
            request = queue.popleft()

        self._semaphore.release()
        logger.debug('Popped %s', request.url)
        return request

    async def initialize(self):
        ''' Load rate limits from database. '''
        async with self._db_pool.connection() as conn:
            cursor = await r.table('rate_limit').run(conn)
            async for rate_limit in cursor:
                if rate_limit['type'] == 'global':
                    self._global_limit = rate_limit['delay']
                elif rate_limit['type'] == 'domain':
                    token = rate_limit['token']
                    self._rate_limits[token] = rate_limit['delay']
                else:
                    raise Exception('Cannot load rate limit (unknown type): '
                        .format(repr(rate_limit)))
            await cursor.close()

        logger.info('Rate limiter is initialized.')

    async def push(self, request):
        '''
        Schedule a request for downloading.

        Suspends if the rate limiter is already filled to capacity.
        '''
        await self._semaphore.acquire()
        token = self._get_token_for_url(request.url)
        if token not in self._queues:
            self._queues[token] = deque()
            self._add_expiry(Expiry(time(), token))
        self._queues[token].append(request)

    async def remove_job(self, job_id):
        ''' Remove all download requests for the given job. '''
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

        # Return the removed items so the crawl job can place them back into
        # the frontier.
        return removed_items

    def reset(self, url):
        ''' Reset the rate limit for the specified URL. '''
        token = self._get_token_for_url(url)
        limit = self._rate_limits.get(token, self._global_limit)
        self._add_expiry(Expiry(time() + limit, token))

    async def set_domain_limit(self, domain, delay):
        '''
        Set a rate limit.

        If delay is None, then remove the rate limit for the specified domain,
        i.e. use the global default for that domain. Set ``delay=0`` for no
        delay.
        '''
        token = self._get_token_for_domain(domain)
        base_query = r.table('rate_limit').get_all(token, index='token')
        if delay is None:
            try:
                del self._rate_limits[token]
            except KeyError:
                pass
            async with self._db_pool.connection() as conn:
                await base_query.delete().run(conn)
        else:
            self._rate_limits[token] = delay
            async with self._db_pool.connection() as conn:
                try:
                    await base_query.nth(0).update({'delay': delay}).run(conn)
                except r.ReqlNonExistenceError:
                    await r.table('rate_limit').insert({
                        'delay': delay,
                        'domain': domain,
                        'name': domain,
                        'token': token,
                        'type': 'domain',
                    }).run(conn)

    async def set_global_limit(self, delay):
        token = b'\x00' * 16
        if delay is None:
            raise Exception('Cannot delete the global rate limit.')
        self._global_limit = delay
        query = (
            r.table('rate_limit')
             .get_all(token, index='token')
             .nth(0)
             .update({'delay': delay})
        )
        async with self._db_pool.connection() as conn:
            await query.run(conn)

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
