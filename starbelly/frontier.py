from dataclasses import dataclass
import logging

from rethinkdb import RethinkDB
from yarl import URL

from .downloader import DownloadRequest
from .login import get_login_form


r = RethinkDB()
logger = logging.getLogger(__name__)


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
    def __init__(self, job_id, db_pool, send_channel, downloader,
            robots_txt_manager, policy, pickled_state=None):
        '''
        Constructor

        :param bytes job_id: The ID of the job corresponding to this frontier.
        :param db_pool: A RethinkDB connection pool.
        :param trio.SendChannel send_channel: This channel is used to send
            ``FrontierItem`` that need to be downloaded, e.g. to send to the
            rate limiter.
        :param starbelly.downloader.Downloader downloader: The downloader used
            for logging in.
        :param starbelly.robots.RobotsTxtManager: A robots.txt manager.
        :param starbelly.policy.Policy: The policy to use.
        :param bytes pickled_state: If not None, initialize the "seen" URLs to
            those contained in this pickled data.
        '''
        self._job_id = job_id
        self._db_pool = db_pool
        self._send_channel = send_channel
        self._receive_channel = receive_channel
        self._downloader = downloader
        self._robots_txt_manager = robots_txt_manager
        self._policy = policy
        if pickled_state:
            self._frontier_seen = pickle.loads(pickled_state)
        else:
            self._frontier_seen = set()

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
                        await self._try_login(domain)
                        self._authenticated_domains.add(domain)
                logger.debug('%r Sending: %r', self, item)
                request = DownloadRequest.from_frontier_item(item)
                await self._send_channel.send(request)

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
                    await trio.sleep(1)

        return [FrontierItem.from_doc(doc) for doc in docs]

    async def _try_login(self, domain):
        ''' Attempt a login for the given domain. '''
        async with self._db_pool.connection() as conn:
            login = await r.table('domain_login').get(domain).run(conn)

        if login is None:
            return

        user = random.choice(login['users'])
        masked_pass = user['password'][:2] + '******'
        logger.info('%r Attempting login: domain=%s with user=%s password=%s',
            self, domain, user['username'], masked_pass)
        request = DownloadRequest(frontier_id=self.id, job_id=self._job_id,
            method='GET', url=login['login_url'], form_data=None, cost=1.0)
        response = await self._downloader.download(request)
        if not response.is_success:
            logger.error('%r Login aborted: cannot fetch %s', self,
                response.url)
            return
        try:
            action, method, data = await get_login_form(self._cookie_jar,
                response, user['username'], user['password'])
        except Exception as e:
            logger.exception('%r Cannot parse login form: %s', self, e)
            return
        logger.info('%r Login action=%s method=%s data=%r', self, action, method,
            data)
        request = DownloadRequest(frontier_id=self.id, job_id=self._job_id,
            method=method, url=action, form_data=data, cost=1.0)
        response = await self._downloader.download(request)
        if not response.is_success():
            logger.error('%r Login failed action=%s (see downloader log for'
                ' details)', self, action)

