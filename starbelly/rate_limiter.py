import asyncio
from bisect import bisect
from collections import defaultdict
import logging
from time import time


logger = logging.getLogger(__name__)


class DomainRateLimiter:
    '''
    A class that is responsible for tracking rate limits for each domain.
    '''

    def __init__(self, default_interval=5):
        ''' Constructor. '''
        self._all_domains = set()
        self._domain_touched = asyncio.Future()
        self._intervals = defaultdict(lambda: default_interval)
        self._ready_domains = set()
        self._wait_domains = list()
        self._wait_times = list()

    async def select_domain(self, choices):
        '''
        From a set ``choices`` of domains that we have pending crawl items to
        download, select one of the domains that is allowed by the rate limit.
        '''
        # Add any domains that we don't already know about.
        new_domains = choices - self._all_domains
        self._all_domains.update(new_domains)
        self._ready_domains.update(new_domains)

        while True:
            # Peel off all domains that have become ready.
            now = time()
            while len(self._wait_times) > 0 and now >= self._wait_times[0]:
                self._wait_times.pop(0)
                self._ready_domains.add(self._wait_domains.pop(0))

            logger.debug('Domains choices: {}'.format(choices))
            logger.debug('Domains ready: {}'.format(self._ready_domains))
            logger.debug('Current time: {}'.format(time()))
            logger.debug('Domains pending: {}'.format(
                list(zip(self._wait_domains, self._wait_times))
            ))

            # Use a ready domain if possible.
            #
            # TODO: there should be a more orderly way to pick from several
            # ready domains, e.g. the one that was least recently used, in order
            # to ensure all domains are treated equally.
            try:
                domain = (self._ready_domains & choices).pop()
                self._ready_domains.remove(domain)
                logger.debug('Selected domain {}'.format(domain))
                return domain
            except KeyError as e:
                pass

            # Wait until the next domain becomes ready.
            logger.debug('No domains available! Waiting for a rate limit to expire...')
            if len(self._wait_times) == 0:
                await self._domain_touched
            else:
                delay = self._wait_times[0] - now
                sleeper = asyncio.ensure_future(asyncio.sleep(delay))
                await asyncio.wait(
                    [sleeper, self._domain_touched],
                    return_when=asyncio.FIRST_COMPLETED
                )
                if not sleeper.done():
                    sleeper.cancel()

    def set_domain_limit(self, domain, interval):
        ''' Set the rate limit for a given domain. '''
        self._intervals[domain] = interval
        self._all_domains.add(domain)
        self._ready_domains.add(domain)

    def touch_domain(self, domain):
        '''
        Mark a domain has having been accessed, so it will not be selected
        again until its rate limit expires.
        '''
        interval = self._intervals[domain]

        if interval == 0:
            self._ready_domains.add(domain)
        else:
            next_time = time() + self._intervals[domain]
            index = bisect(self._wait_times, next_time)
            self._wait_times.insert(index, next_time)
            self._wait_domains.insert(index, domain)

        if not self._domain_touched.done():
            self._domain_touched.set_result(None)

        self._domain_touched = asyncio.Future()
        logger.debug('Touched domain {}'.format(domain))
