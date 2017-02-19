import asyncio
from bisect import bisect
from collections import defaultdict
import logging
from time import time

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    '''
    A class that is responsible for tracking rate limits for each domain.

    The rate limiter handles 3 scenarios.

    1. A task needs a domain and a domain is ready: that domain is returned
       immediately from an internal list of ready domains.
    2. A task needs a domain but the domain isn't ready: the task waits for a
       rate limit to expire. Tasks are served in the same order that they are
       called.
    3. A rate limit expires but no task is waiting for it: the domain is added
       an internal list of ready domains which is later used to serve scenario
       #1.
    '''

    def __init__(self, default_interval=0.1):
        ''' Constructor. '''
        self._default_interval = default_interval
        self._intervals = dict()
        self._ready_domains = list()
        self._sleepers = set()
        self._seen_domains = set()
        self._waiters = list()

    async def select_domain(self, choices):
        '''
        From a list ``choices`` of domains return the first domain that is
        allowed by the rate limit.
        '''

        # If there any domains we haven't seen before, add those to the ready
        # list.
        for choice in choices:
            if not choice in self._seen_domains:
                self._seen_domains.add(choice)
                self._ready_domains.append(choice)

        # Check if any domains are on the ready list.
        if len(self._ready_domains) > 0:
            # If any domains are ready, return the first match immediately.
            for index, domain in enumerate(self._ready_domains):
                if domain in choices:
                    domain = self._ready_domains.pop(index)
                    logger.debug('Domain {} is ready.'.format(domain))
                    return domain

        # If we get here, then none of the choices is ready, so wait for one
        # to become ready.
        msg = 'No domain in choices={} is ready. Waiting for rate limit expiry.'
        logger.debug(msg.format(choices))
        waiter = DomainRateLimitFuture(choices)
        self._waiters.append(waiter)
        return await waiter

    def set_domain_limit(self, domain, interval):
        ''' Set the rate limit for a given domain. '''
        msg = 'Setting rate limit for {} to {}.'
        logger.debug(msg.format(domain, interval))
        self._intervals[domain] = interval

    def stop(self):
        '''
        Cancel all tasks created by this instance.

        Returns a future that completes when all tasks have finished.
        '''

        logger.info('Rate limiter is stopping.')

        for sleeper in self._sleepers:
            sleeper.cancel()

        tasks = asyncio.gather(*self._sleepers, return_exceptions=True)
        return tasks

    def touch_domain(self, domain):
        '''
        Mark a domain has having been accessed.

        After accessing, the domain will go back into the ready list after its
        rate limit expires.
        '''

        def rate_limit_expired(_):
            ''' This nested function is called when a rate limit expires. '''
            found_waiter = False
            self._sleepers.remove(sleeper)

            # Check if any task is waiting for this domain.
            for index, waiter in enumerate(self._waiters):
                if waiter.is_waiting_for(domain):
                    self._waiters.pop(index)
                    if not waiter.cancelled():
                        msg = 'Rate limit expired for {} and sent to waiter.'
                        logger.debug(msg.format(domain))
                        found_waiter = True
                        waiter.set_result(domain)

            # If nobody is waiting, add this domain to the ready list.
            if not found_waiter:
                msg = 'Rate limit expired for {} and added to ready list.'
                logger.debug(msg.format(domain))
                self._ready_domains.append(domain)

        # Create a task that will sleep until the rate limit expires; when it
        # wakes up, it will mark the domain as being ready.
        rate_limit = self._intervals.get(domain, self._default_interval)
        sleeper = asyncio.ensure_future(asyncio.sleep(rate_limit))
        sleeper.add_done_callback(rate_limit_expired)
        self._sleepers.add(sleeper)


class DomainRateLimitFuture(asyncio.Future):
    ''' A subclass of ``Future`` that holds a list of domains. '''

    def __init__(self, domains):
        '''
        Constructor.

        The future fires when of the ``domains`` is ready, i.e. its rate limit
        has expired.
        '''

        super().__init__()
        self._rate_limit_domains = domains

    def is_waiting_for(self, domain):
        ''' Return true if this waiter is waiting for ``domain``. '''
        return domain in self._rate_limit_domains
