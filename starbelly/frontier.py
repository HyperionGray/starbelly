from dataclasses import dataclass
import logging

from rethinkdb import RethinkDB
from yarl import URL

from .backoff import ExponentialBackoff
from .downloader import DownloadRequest


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
    def __init__(self, job_id, db, send_channel, login_manager, policy, stats):
        '''
        Constructor

        :param str job_id: The ID of the job corresponding to this frontier.
        :param starbelly.db.CrawlFrontierDb db: A database layer.
        :param trio.SendChannel send_channel: This channel is used to send
            ``FrontierItem`` that need to be downloaded, e.g. to send to the
            rate limiter.
        :param starbelly.login.LoginManager login_manager: Used when the
            frontier sees an unauthenticated domain and needs to log in.
        :param starbelly.policy.Policy: The policy to use.
        :param dict stats: A dictionary of crawl statistics.
        '''
        self._job_id = job_id
        self._db = db
        self._send_channel = send_channel
        self._login_manager = login_manager
        self._policy = policy
        self._authenticated_domains = set()
        self._stats = stats

    def __repr__(self):
        ''' Include job ID in the repr. '''
        return '<CrawlFrontier job_id={}>'.format(self._job_id[:8])

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
                if self._policy.authentication.is_enabled():
                    domain = URL(item.url).host
                    if domain not in self._authenticated_domains:
                        await self._login_manager.login(domain)
                        self._authenticated_domains.add(domain)
                logger.debug('%r Sending: %r', self, item)
                request = DownloadRequest.from_frontier_item(item)
                await self._send_channel.send(request)

    async def _initialize(self):
        ''' Initialize frontier database documents. '''

        size = await self._db.get_frontier_size(self._job_id)
        logger.info('%r Initialization complete (size=%d)', self, size)
        self._stats['frontier_size'] = size

    async def _get_batch(self, size=10):
        '''
        Get a batch of items from the frontier table, ordered by ascending cost.
        If no items available, poll the database until items become available.

        :param int size:
        :returns: A batch of frontier items.
        :rtype: list[FrontierItem]
        '''
        backoff = ExponentialBackoff(min_=1, max_=16)
        async for _ in backoff:
            docs = await self._db.get_frontier_batch(self._job_id, size)
            if docs:
                self._stats['frontier_size'] -= len(docs)
                break
            else:
                if await self._db.any_in_flight():
                    backoff.increase()
                else:
                    raise FrontierExhaustionError()

        return [FrontierItem.from_doc(doc) for doc in docs]
