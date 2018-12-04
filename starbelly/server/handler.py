from functools import wraps


handlers = dict()

# TODO EXPAND THIS TO HANDLE DI
# foo.__code__.co_varnames

def handler(func):
    _handlers[func.__name__] = handler
