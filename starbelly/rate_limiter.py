from binascii import hexlify
from collections import deque
from dataclasses import dataclass
import functools
import hashlib
from heapq import heappop, heappush
import logging

import trio


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

    def __repr__(self):
        ''' This repr is easier to read than the default. '''
        return 'Expiry(time={:0.3f}, token={})'.format(self.time,
            hexlify(self.token).decode('ascii'))


def get_domain_token(domain):
    '''
    Get a token for a domain.

    :param str domain: The domain to generate a token for.
    :returns: The token corresponding to the domain.
    :rtype: bytes
    '''
    hash_ = hashlib.blake2b(domain.encode('ascii'), digest_size=16)
    token = hash_.digest()
    return token


class RateLimiter:
    '''
    This class is responsible for enforcing rate limits.

    The rate limiter acts as a bottleneck between the multiple crawl frontiers
    and the downloader, enforcing the configured rate limits. Each crawl job
    sends download requests to the rate limiter ordered by priority of download,
    then the rate limiter forwards those items to the appropriate downloader
    when the appropriate amount of time has elapsed. This ensure that rate
    limits are correctly enforced even if multiple crawl jobs are accessing the
    same domain.

    In order to provide some flexibility, rate limits are not strictly tied to
    individual domains. Each URL is mapped to a "rate limit token". URLs with
    the same token will share the same rate limit. This system will allow more
    flexible rate limiting policies in the future, such as applying a single
    rate limit to a set of domains.

    Internally, a queue is maintained for each rate limit token that has pending
    requests to it. When a rate limit expires for a given token, the next URL in
    the corresponding queue is sent to the downloader. The rate limiter has a
    fixed capacity. This prevents the rate limiter's memory usage from growing
    without bounds and applies backpressure to the crawl jobs that are
    submitting download requests to the rate limiter.
    '''
    def __init__(self, capacity):
        '''
        Constructor.

        :param int capacity: The maximum number of items to buffer inside of the
            rate limiter.
        '''
        self._expires = list()
        self._expiry_cancel_scope = None
        self._global_limit = None
        self._queues = dict()
        self._rate_limits = dict()
        self._capacity = capacity
        self._semaphore = trio.Semaphore(capacity)
        self._request_send, self._request_recv = trio.open_memory_channel(0)
        self._reset_send, self._reset_recv = trio.open_memory_channel(0)
        self._job_channels = dict()

    @property
    def item_count(self):
        ''' The number of requests queueud inside the rate limiter. '''
        return self._capacity - self._semaphore.value

    @property
    def job_count(self):
        ''' The number of jobs tracked by the rate limiter. '''
        return len(self._job_channels)

    def add_job(self, job_id):
        '''
        Add a job to the rate limiter. Returns a send channel that requests for
        this job will be sent to.

        :param str job_id: A job ID.
        '''
        job_send, job_recv = trio.open_memory_channel(0)
        self._job_channels[job_id] = job_send
        return job_recv

    def get_request_channel(self):
        '''
        Get a channel that can send requests to the rate limiter.

        :rtype: trio.SendChannel
        '''
        return self._request_send.clone()

    def get_reset_channel(self):
        '''
        Get a channel that can send resets to the rate limiter.

        :rtype: trio.ReceiveChannel
        '''
        return self._reset_send.clone()

    async def remove_job(self, job_id):
        '''
        Remove all download requests for the given job.

        :param str job_id:
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
        channel = self._job_channels.pop(job_id)
        await channel.aclose()

    async def run(self):
        ''' Run the rate limiter. '''
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self._read_requests_task)
            nursery.start_soon(self._write_requests_task)
            nursery.start_soon(self._read_resets_task)

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

    def set_rate_limit(self, token, delay):
        '''
        Set the rate limit for the specified token.

        :param str token: The rate limit token.
        :param float delay: The delay between subsequent requests, in seconds.
        '''
        logger.debug('Set rate limit: token=%r delay=%f',
            hexlify(token).decode('ascii'), delay)
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
        if self._expiry_cancel_scope:
            self._expiry_cancel_scope.cancel()
            self._expiry_cancel_scope = None

    async def _get_next_expiry(self):
        '''
        Pop an expiry off the heap.

        If no tokens on heap, suspend until a token is available.

        :returns: The next expiry.
        :rtype: Expiry
        '''
        while True:
            if not self._expires:
                # If there are no pending expirations, then we wait for a new
                # token or a reset of an existing token.
                with trio.CancelScope() as cancel_scope:
                    self._expiry_cancel_scope = cancel_scope
                    await trio.sleep_forever()
                continue

            # Now there are definitely pending expirations. Examine the earliest
            # pending expiration. If it is in the past, then we pop it
            # immediately. If it is in the future, then sleep until its
            # expiration time or until somebody adds or resets a token.
            now = trio.current_time()
            expires = self._expires[0].time
            if expires <= now:
                expiry = heappop(self._expires)
                return expiry
            with trio.move_on_after(expires - now) as cancel_scope:
                self._expiry_cancel_scope = cancel_scope
                await trio.sleep_forever()
            continue

    async def _read_requests_task(self):
        '''
        This task reads incoming requests, e.g. from the crawl frontier, and
        places them into the rate limiting queue.

        :returns: This task runs until cancelled.
        '''
        async for request in self._request_recv:
            await self._semaphore.acquire()
            logger.debug('Received request: %s', request.url)
            token = get_domain_token(request.url.host)
            if token not in self._queues:
                self._queues[token] = deque()
                self._add_expiry(Expiry(trio.current_time(), token))
            self._queues[token].append(request)

    async def _read_resets_task(self):
        '''
        This task listens for incoming resets that indicate that a request has
        finished downloading and its corresponding rate limit should start.

        :returns: This task runs until cancelled.
        '''
        async for url in self._reset_recv:
            logger.debug('Reset URL: %s', url)
            token = get_domain_token(url.host)
            limit = self._rate_limits.get(token, self._global_limit)
            self._add_expiry(Expiry(trio.current_time() + limit, token))

    async def _write_requests_task(self):
        '''
        When a request is ready to be downloaded, i.e. the required rate limit
        time has elapsed, this task forwards the request to the appropriate
        downloader.

        :returns: This task runs until cancelled.
        '''
        while True:
            expiry = await self._get_next_expiry()
            logger.debug('Popped expiry: %r', expiry)
            token = expiry.token
            queue = self._queues[token]

            if not queue:
                # If nothing left in this queue, delete it and get another
                # token instead.
                del self._queues[token]
                continue
            else:
                request = queue.popleft()

            channel = self._job_channels[request.job_id]
            await channel.send(request)
            self._semaphore.release()
            logger.debug('Sent request:  %s', request.url)
