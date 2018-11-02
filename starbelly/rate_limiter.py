from collections import deque
from dataclasses import dataclass, field
import functools
import hashlib
from heapq import heappop, heappush
import logging
import urllib.parse

import trio
from yarl import URL


logger = logging.getLogger(__name__)
GLOBAL_RATE_LIMIT_TOKEN = b'\x00' * 16


@dataclass
@functools.total_ordering
class Expiry:
    '''
    Represents a rate limit token that will expire at a given time.

    Expiries can be compared to each other, e.g. ``expiry1 < expiry2``, or to a
    timestamp, e.g. ``expiry1 < trio.current_time()``.
    '''
    time: float
    token: bytes

    def __eq__(self, other):
        '''
        Implement ``==`` operator.

        Full comparison is provided by the ``functools.total_ordering``
        decorator.

        :type other: class:`Expiry` or float
        '''
        time1 = self.time
        if isinstance(other, Expiry):
            time2 = other.time
        elif isinstance(other, (int, float)):
            time2 = other
        return time1 == time2

    def __lt__(self, other):
        '''
        Implement ``<`` operator.

        Full comparison is provided by the ``functools.total_ordering``
        decorator.

        :type other: class:`Expiry` or float
        '''
        time1 = self.time
        if isinstance(other, Expiry):
            time2 = other.time
        elif isinstance(other, (int, float)):
            time2 = other
        return time1 < time2


class RateLimiter:
    '''
    This class is responsible for enforcing rate limits.

    The rate limiter acts as a bottleneck between the multiple crawl frontiers
    and the downloader, enforcing the configured rate limits.

    A queue is maintained for each domain that has pending requests to it. When
    a rate limit expires for a given domain, the next URL in the corresponding
    domain queue is sent to the downloader. (If the domain queue is empty, the
    queue is deleted.) The rate limiter has a fixed capacity; when the number of
    URLs buffered in the rate limiter exceeds this capacity, subsequent calls to
    :meth:`push` will block until some capacity is available; these calls will
    be served in the order they are made.

    In order to provide some flexibility, rate limits are not strictly tied to
    individual domains. Each URL is mapped to a "rate limit token". URLs with
    the same token will be placed into the same queue. This system will allow
    more flexible rate limiting policies in the future, such as applying a
    single rate limit to a set of domains.
    '''
    def __init__(self, capacity):
        '''
        Constructor.

        :param int capacity: The number of items to buffer in the rate limiter
            before calls to :meth:`push` will block. (Must be ≥0.)
        '''
        if capacity < 0:
            raise ValueError('Capacity must be ≥0.')
        self._expires = list()
        self._expiry_lock = trio.Lock()
        self._expiry_cancel_scope = None
        self._global_limit = None
        self._queues = dict()
        self._rate_limits = dict()
        self._semaphore = trio.Semaphore(capacity)

    def __len__(self):
        '''
        Return number of buffered requests.

        :rtype: int
        '''
        return sum(len(q) for q in self._queues.values())

    def delete_rate_limit(self, token):
        '''
        Remove a rate limit for a given token.

        If ``token`` does not exist, then this has no effect.

        :param bytes token: A rate limit token.
        '''
        logger.debug('Delete rate limit: token=%r', token)
        try:
            del self._rate_limits[token]
        except KeyError:
            pass

    async def get_next_request(self):
        '''
        Get the next download request from this rate limiter.

        Maintains the invariant that if a token exists in the ``_expires`` heap,
        then a queue exists for that token.

        :returns: The next download request.
        :rtype: starbelly.downloader.DownloadRequest
        '''
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

    def get_domain_token(self, domain):
        '''
        Get a token for a domain.

        :param str domain: The domain to generate a token for.
        :returns: The token corresponding to the domain.
        :rtype: bytes
        '''
        hash_ = hashlib.blake2b(domain.encode('ascii'), digest_size=16)
        token = hash_.digest()
        return token

    async def push(self, request):
        '''
        Schedule a request for downloading.

        Suspends if the rate limiter is already filled to capacity.

        :param request: A download request.
        :type request: starbelly.downloader.DownloadRequest
        '''
        logger.debug('Push request: %r', request)
        await self._semaphore.acquire()
        token = self.get_domain_token(request.url.host)
        if token not in self._queues:
            self._queues[token] = deque()
            self._add_expiry(Expiry(trio.current_time(), token))
        self._queues[token].append(request)

    def remove_job(self, job_id):
        '''
        Remove all download requests for the given job.

        :param bytes job_id:
        :returns: The removed requests.
        :rtype: list[starbelly.downloader.DownloadRequest]
        '''
        logger.debug('Remove job: id=%r', job_id)
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
        '''
        Reset the rate limit for the specified URL.

        :param yarl.URL url:
        '''
        logger.debug('Reset URL: %r', url)
        token = self.get_domain_token(url.host)
        limit = self._rate_limits.get(token, self._global_limit)
        self._add_expiry(Expiry(trio.current_time() + limit, token))

    def set_rate_limit(self, token, delay):
        '''
        Set the rate limit for the specified token.

        :param str token: The rate limit token.
        :param float delay: The delay between subsequent requests, in seconds.
        '''
        logger.debug('Set rate limit: token=%r delay=%f', token, delay)
        if token == GLOBAL_RATE_LIMIT_TOKEN:
            self._global_limit = delay
        else:
            self._rate_limits[token] = delay

    def _add_expiry(self, expiry):
        '''
        Add the specified expiry to the heap.

        :param Expiry expiry:
        '''
        heappush(self._expires, expiry)
        if self._expiry_cancel_scope and expiry.time <= trio.current_time():
            self._expiry_cancel_scope.cancel()
            self._expiry_cancel_scope = None

    async def _get_next_expiry(self):
        '''
        Pop an expiry off the heap.

        If no tokens on heap, suspend until a token is available. This function
        uses an internal lock so that only one task can execute it at a time.

        :returns: The next expiry.
        :rtype: Expiry
        '''
        async with self._expiry_lock:
            # If there are no pending expirations, then we wait for somebody to
            # call push() or reset().
            if len(self._expires) == 0:
                with trio.open_cancel_scope() as cancel_scope:
                    self._expiry_cancel_scope = cancel_scope
                    await trio.sleep_forever()

            # Now there are definitely pending expirations. Examine the earliest
            # pending expiration. If it is in the past, then we pop it
            # immediately. If it is in the future, then sleep until its
            # expiration time or until somebody calls reset() or push().
            now = trio.current_time()
            expires = self._expires[0].time
            if expires > now:
                with trio.move_on_after(expires - now) as cancel_scope:
                    self._expiry_cancel_scope = cancel_scope
                    await trio.sleep_forever()

            expiry = heappop(self._expires)
            return expiry
