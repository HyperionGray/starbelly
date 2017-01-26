class PubSub:
    ''' A really simple, in-memory publish-subscribe system. '''

    def __init__(self):
        ''' Constructor. '''
        self._callbacks = set()

    def cancel(self, callback):
        ''' Remove a subscription. '''
        self._callbacks.remove(callback)

    def listen(self, callback):
        ''' Subscribe to events. '''
        self._callbacks.add(callback)

    def publish(self, *args, **kwargs):
        ''' Send an event to all subscribers. '''
        for callback in self._callbacks:
            callback(*args, **kwargs)
