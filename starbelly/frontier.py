from dataclasses import dataclass
import logging

from rethinkdb import RethinkDB
from yarl import URL

from .downloader import DownloadRequest
from .login import get_login_form


r = RethinkDB()
logger = logging.getLogger(__name__)


class FrontierExhaustionError(Exception):
    ''' Indicates that the frontier has no items remaining (in-flight or
    otherwise. '''


@dataclass
class FrontierItem:
    ''' Represents a resource that should be crawled. '''
    frontier_id: bytes
    job_id: bytes
    url: str
    cost: float

    @classmethod
    def from_doc(cls, doc):
        '''
        Create a frontier item from a database document.

        :param dict doc: A database document.
        '''
        return cls(doc['id'], doc['job_id'], doc['url'], doc['cost'])


class CrawlFrontier:
    ''' Contains the logic for managing a crawl frontier, i.e. the URLs that
    have already been crawled and the URLs that are remaining to be crawled. '''
    def __init__(self, job_id, db_pool, send_channel, login_manager,
            robots_txt_manager, policy):
        '''
        Constructor

        :param str job_id: The ID of the job corresponding to this frontier.
        :param db_pool: A RethinkDB connection pool.
        :param trio.SendChannel send_channel: This channel is used to send
            ``FrontierItem`` that need to be downloaded, e.g. to send to the
            rate limiter.
        :param starbelly.login.LoginManager login_manager: Used when the
            frontier sees an unauthenticated domain and needs to log in.
        :param starbelly.robots.RobotsTxtManager: A robots.txt manager.
        :param starbelly.policy.Policy: The policy to use.
        '''
        self._job_id = job_id
        self._db_pool = db_pool
        self._send_channel = send_channel
        self._receive_channel = receive_channel
        self._login_manager = login_manager
        self._robots_txt_manager = robots_txt_manager
        self._policy = policy
        self._authenticated_domains = set()
        self._size = 0
        self._pending = 0

    def __repr__(self):
        ''' Include job ID in the repr. '''
        return '<CrawlFrontier job_id={}>'.format(self._job_id)[:8]

    @property
    def size(self):
        '''
        Return total number of items in the frontier, including those in
        database.

        :rtype: int
        '''
        return self._frontier_size

    async def run(self):
        '''
        This task takes items off the frontier and sends them to the rate
        limiter.

        :returns: This function runs until cancelled.
        '''
        await self._initialize()

        while True:
            frontier_items = await self._get_batch()
            for item in frontier_items:
                robots_ok = await self._robots_txt_manager.is_allowed(
                    item['url'])
                if not robots_ok:
                    self._pending -= 1
                    continue
                if self._auth_policy.is_enabled():
                    domain = urlparse(item['url']).hostname
                    if domain not in self._authenticated_domains:
                        await self._login_manager.login(domain)
                        self._authenticated_domains.add(domain)
                logger.debug('%r Sending: %r', self, item)
                request = DownloadRequest.from_frontier_item(item)
                await self._send_channel.send(request)

    async def _any_in_flight(self):
        '''
        Check whether there are any frontier items that are "in-flight", i.e.
        somewhere in the crawling pipeline.

        :rtype bool:
        '''
        in_flight_query = (
            r.table('frontier')
             .order_by(index='cost_index')
             .between((self.id, True, r.minval),
                      (self.id, True, r.maxval))
             .count()
        )

        async with self._db_pool.connection() as conn:
            in_flight_count = await in_flight_query.run(conn)

        return in_flight_count > 0

    async def _initialize(self):
        ''' Initialize frontier database documents. '''
        size_query =  r.table('frontier').between(
            (self._job_id, r.minval),
            (self._job_id, r.maxval),
            index='cost_index'
        ).count()

        async with self._db_pool.connection() as conn:
            logger.info('%r Initializing frontier...', self)
            self._size = await size_query.run(conn)
            logger.info('%r Initialization complete.', self)

    async def _get_batch(self, size=10):
        '''
        Get a batch of items from the frontier table, ordered by ascending cost.
        If no items available, poll the database until items become available.

        :param int size:
        '''
        next_url_query = (
            r.table('frontier')
             .order_by(index='cost_index')
             .between((self.id, False, r.minval),
                      (self.id, False, r.maxval))
             .limit(size)
             .update({'in_flight': True}, return_changes=True)
        )

        while True:
            async with self._db_pool.connection() as conn:
                try:
                    result = await next_url_query.run(conn)
                    docs = [r['new_val'] for r in result['changes']]
                    self._size -= len(docs)
                    self._pending += 1
                    break
                except r.ReqlNonExistenceError:
                    if await self._any_in_flight():
                        await trio.sleep(1)
                    else:
                        raise FrontierExhaustionError()

        return [FrontierItem.from_doc(doc) for doc in docs]
