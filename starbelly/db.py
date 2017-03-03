import asyncio
import logging


logger = logging.getLogger(__name__)


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
        self._db_connect = db_connect
        self._queue = asyncio.Queue(maxsize=max_idle)

    async def acquire(self):
        '''
        Get a connection from the pool or create a new connection if necessary.

        Any connection that you acquire from this method, you must later release
        with the ``release(...)`` method.
        '''

        try:
            conn = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            conn = await self._db_connect()

        return conn

    def connection(self):
        ''' Return a context manager that yields a connection. '''
        return _AsyncRethinkContextManager(self)

    async def close(self):
        ''' Close all connections and remove them from the pool. '''

        logger.info('Closing all remaining database connections...')
        conns = list()

        while not self._queue.empty():
            conns.append(self._queue.get_nowait())

        for conn in conns:
            await conn.close()
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
