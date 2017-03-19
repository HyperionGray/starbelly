import asyncio
import logging

import rethinkdb as r
from rethinkdb.errors import ReqlCursorEmpty


logger = logging.getLogger(__name__)


class AsyncCursorIterator:
    '''
    An async iterator for a RethinkDB cursor.

    This will eventually be part of RethinkDB API (see
    https://github.com/rethinkdb/rethinkdb/pull/6291) but for now I have rolled
    my own.
    '''

    def __init__(self, cursor):
        ''' Constructor. '''
        self._cursor = cursor

    def __aiter__(self):
        ''' Return self, an async iterator. '''
        return self

    async def __anext__(self):
        ''' Get next item from cursor. '''
        try:
            while True:
                return await asyncio.shield(self._cursor.next())
        except ReqlCursorEmpty:
            raise StopAsyncIteration
        except asyncio.CancelledError:
            # Cancellation is okay.
            raise
        finally:
            pass
            #TODO close() isn't a coroutine in this version of the driver. In
            # the future, it should be possible to do this:
            # await self._cursor.close()
            # But for now, calling this synchronously leads to an error.


class AsyncRethinkPool:
    '''
    An asyncio-compatible pool of RethinkDB connections.

    There is no maximum number of connections, because certain types of queries
    (such as changefeeds) will keep a connection open for a long time. We don't
    want a bunch of changefeeds to prevent the application from doing any
    transactional work.

    You can obtain a connection with the ``acquire()`` coroutine. When a task
    acquires a connection from the pool, it must later ``release(...)`` the
    connection when it is done so that another task may re-use the connection.
    To simplify acquiring and releasing, this class provides an asyncronous
    context manager, so connections can be easily managed as follows:

        pool = RethinkDbPool()
        ...
        async with pool.connection() as conn:
            ...

    This form will make sure that the connection is always released back to the
    pool.
    '''
    def __init__(self, db_connect, max_idle=20):
        '''
        Constructor.

        ``db_connect`` is a factory coroutine that takes no arguments and
        returns a new connection.

        ``max_idle`` is the number of connections to keep open in the queue. If
        a connection is released and there are already ``max_idle`` connections
        open, then the released connection will be closed.
        '''
        self._closed = False
        self._db_connect = db_connect
        self._queue = asyncio.Queue(maxsize=max_idle)
        self._sequence = 0

    async def acquire(self):
        '''
        Get a connection from the pool or create a new connection if necessary.

        Any connection that you acquire from this method, you must later release
        with the ``release(...)`` method.
        '''

        if self._closed:
            raise Exception('DB pool is closed!')

        try:
            conn = self._queue.get_nowait()
            while not conn.is_open():
                # Connections in the pool may timeout, so look for one that is
                # still connected.
                conn = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            try:
                conn = await self._db_connect()
            except r.ReqlDriverError as rde:
                # Rethink wraps up CancelledError in ReqlDriverError, but
                # cancelling is okay, so we unwrap and re-raise it.
                if isinstance(rde.__context__, asyncio.CancelledError):
                    raise rde.__context__ from None
                else:
                    raise

        return conn

    def connection(self):
        ''' Return a context manager that manages a connection. '''
        return _AsyncRethinkContextManager(self)

    async def close(self):
        ''' Close all connections and remove them from the pool. '''

        logger.info('Closing all remaining database connections...')
        conns = list()

        while not self._queue.empty():
            conns.append(self._queue.get_nowait())

        for conn in conns:
            if conn.is_open():
                await conn.close()

        self._closed = True
        logger.info('All database connections have been closed.')

    async def release(self, conn):
        '''
        Release a connection back into the pool.

        If the pool is already full (e.g. size equals ``max_idle``), then the
        connection will be closed.
        '''

        try:
            self._queue.put_nowait(conn)
        except asyncio.QueueFull:
            await conn.close()


class _AsyncRethinkContextManager:
    ''' An async context manager for RethinkDbPool. '''

    def __init__(self, pool):
        ''' Constructor. '''
        self._conn = None
        self._pool = pool

    async def __aenter__(self):
        ''' Acquire a connection. '''
        self._conn = await self._pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        ''' Release a connection. '''
        await self._pool.release(self._conn)
