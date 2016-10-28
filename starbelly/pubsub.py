class PubSub:
    def __init__(self):
        self._callbacks = set()

    def cancel(self, callback):
        self._callbacks.remove(callback)

    def listen(self, callback):
        self._callbacks.add(callback)

    def publish(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)
