import math

import trio


class ExponentialBackoff:
    ''' An experimental class: this makes it simple to write loops that poll
    a resource and backoff when the resource is not ready.

    For example, if you are polling the database for some new records, you might
    wait 1 second and then try again. If there are still no records, then you
    wait 2 seconds before trying again, then 4 seconds, then 8, etc.

    This is written as an async iterator, so you can just loop over it and it
    will automatically delay in between loop iterations.
    '''
    def __init__(self, start=1, max_=math.inf):
        '''
        Constructor.

        :param int start: The initial delay between loop iterations.
        :param int max_: The maximum delay.
        '''
        self._backoff = start
        self._initial = True
        self._max = max_

    def __aiter__(self):
        ''' This instance is an async iterator. '''
        return self

    async def __anext__(self):
        ''' Add a delay in between loop iterations. (No delay for the first
        iteration. '''
        if self._initial:
            backoff = 0
            self._initial = False
        else:
            backoff = self._backoff
            await trio.sleep(backoff)
        return backoff

    def increase(self):
        ''' Double the current backoff, but not if it would exceed this
        instance's max value. '''
        if self._backoff <= self._max // 2:
            self._backoff *= 2

    def decrease(self):
        ''' Halve the current backoff, not if would be less than 1. '''
        if self._backoff >= 2:
            self._backoff //= 2
