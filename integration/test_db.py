from datetime import datetime, timezone
import logging
from operator import itemgetter
import pickle

import pytest
from rethinkdb import RethinkDB

from starbelly.db import (
    CrawlFrontierDb,
    CrawlExtractorDb,
    CrawlManagerDb,
    CrawlStorageDb,
    LoginDb,
    ScheduleDb,
    ServerDb,
)
from starbelly.downloader import DownloadResponse
from starbelly.job import RunState


logger = logging.getLogger(__name__)
r = RethinkDB()
r.set_loop_type('trio')


@pytest.fixture
async def db_pool(nursery):
    db_pool = r.ConnectionPool(db='test', nursery=nursery)
    yield db_pool
    await db_pool.close()


@pytest.fixture
async def captcha_solver_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('captcha_solver').run(conn)
    yield r.table('captcha_solver')
    async with db_pool.connection() as conn:
        await r.table_drop('captcha_solver').run(conn)


@pytest.fixture
async def domain_login_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('domain_login', primary_key='domain').run(conn)
    yield r.table('domain_login')
    async with db_pool.connection() as conn:
        await r.table_drop('domain_login').run(conn)


@pytest.fixture
async def frontier_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('frontier').run(conn)
        await r.table('frontier').index_create('cost_index', [r.row['job_id'],
            r.row['in_flight'], r.row['cost']]).run(conn)
        await r.table('frontier').index_wait('cost_index').run(conn)
    yield r.table('frontier')
    async with db_pool.connection() as conn:
        await r.table_drop('frontier').run(conn)


@pytest.fixture
async def job_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('job').run(conn)
        await r.table('job').index_create('started_at').run(conn)
        await r.table('job').index_wait('started_at').run(conn)
        await r.table('job').index_create('schedule',
            [r.row['schedule_id'], r.row['started_at']]).run(conn)
        await r.table('job').index_wait('schedule').run(conn)
    yield r.table('job')
    async with db_pool.connection() as conn:
        await r.table_drop('job').run(conn)


@pytest.fixture
async def policy_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('policy').run(conn)
        await r.table('policy').index_create('name').run(conn)
        await r.table('policy').index_wait('name').run(conn)
    yield r.table('policy')
    async with db_pool.connection() as conn:
        await r.table_drop('policy').run(conn)


@pytest.fixture
async def response_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('response', primary_key='sequence').run(conn)
        await r.table('response').index_create('job_sync',
            [r.row['job_id'], r.row['sequence']]).run(conn)
        await r.table('response').index_wait('job_sync').run(conn)
    yield r.table('response')
    async with db_pool.connection() as conn:
        await r.table_drop('response').run(conn)


@pytest.fixture
async def rate_limit_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('rate_limit', primary_key='token').run(conn)
        await r.table('rate_limit').index_create('name').run(conn)
        await r.table('rate_limit').index_wait('name').run(conn)
    yield r.table('rate_limit')
    async with db_pool.connection() as conn:
        await r.table_drop('rate_limit').run(conn)


@pytest.fixture
async def response_body_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('response_body').run(conn)
    yield r.table('response_body')
    async with db_pool.connection() as conn:
        await r.table_drop('response_body').run(conn)


@pytest.fixture
async def schedule_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('schedule').run(conn)
        await r.table('schedule').index_create('schedule_name').run(conn)
        await r.table('schedule').index_wait('schedule_name').run(conn)
    yield r.table('schedule')
    async with db_pool.connection() as conn:
        await r.table_drop('schedule').run(conn)


class TestCrawlExtractorDb:
    async def test_delete_frontier_items(self, db_pool, frontier_table):
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        async with db_pool.connection() as conn:
            result = await frontier_table.insert({
                'cost': 1.0,
                'job_id': job_id,
                'in_flight': False,
                'url': 'https://extractor.example',
            }).run(conn)
            frontier_id = result['generated_keys'][0]
            count = await frontier_table.count().run(conn)
        assert count == 1
        crawl_extractor_db = CrawlExtractorDb(db_pool)
        result = await crawl_extractor_db.delete_frontier_item(frontier_id)
        async with db_pool.connection() as conn:
            count = await frontier_table.count().run(conn)
        assert count == 0

    async def test_insert_frontier_items(self, db_pool, frontier_table):
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        crawl_extractor_db = CrawlExtractorDb(db_pool)
        result = await crawl_extractor_db.insert_frontier_items([
            {'cost': 1.0, 'job_id': job_id, 'url': 'https://a.example'},
            {'cost': 1.0, 'job_id': job_id, 'url': 'https://b.example'},
            {'cost': 1.0, 'job_id': job_id, 'url': 'https://c.example'},
        ])
        async with db_pool.connection() as conn:
            count = await frontier_table.count().run(conn)
            first = await frontier_table.order_by('url').nth(0).run(conn)
        assert count == 3
        assert first['url'] == 'https://a.example'


class TestCrawlFrontierDb:
    async def test_any_in_flight(self, db_pool, frontier_table):
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        async with db_pool.connection() as conn:
            await frontier_table.insert({
                'cost': 1.0,
                'job_id': job_id,
                'url': 'https://frontier.example',
                'in_flight': False,
            }).run(conn)
        crawl_frontier_db = CrawlFrontierDb(db_pool)
        assert not await crawl_frontier_db.any_in_flight(job_id)
        async with db_pool.connection() as conn:
            await frontier_table.update({'in_flight': True}).run(conn)
        assert await crawl_frontier_db.any_in_flight(job_id)

    async def test_get_frontier_batch(self, db_pool, frontier_table):
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        async with db_pool.connection() as conn:
            # The frontier has 4 items, 1 of which is already in-flight and
            # should not be included in any frontier batches.
            await frontier_table.insert([{
                'cost': 3.0,
                'job_id': job_id,
                'url': 'https://frontier.example/3',
                'in_flight': False,
            },{
                'cost': 2.0,
                'job_id': job_id,
                'url': 'https://frontier.example/2',
                'in_flight': False,
            },{
                'cost': 1.0,
                'job_id': job_id,
                'url': 'https://frontier.example/1',
                'in_flight': False,
            },{
                'cost': 2.5,
                'job_id': job_id,
                'url': 'https://frontier.example/4',
                'in_flight': True,
            }]).run(conn)
        crawl_frontier_db = CrawlFrontierDb(db_pool)
        # The batch size is 2 and we have 3 documents, so we should get two
        # batches.
        batch1 = await crawl_frontier_db.get_frontier_batch(job_id, 2)
        async with db_pool.connection() as conn:
            in_flight_count = await frontier_table.filter({'in_flight': True}
                ).count().run(conn)
        assert in_flight_count == 3
        assert len(batch1) == 2
        assert batch1[0]['url'] == 'https://frontier.example/1'
        assert batch1[1]['url'] == 'https://frontier.example/2'

        batch2 = await crawl_frontier_db.get_frontier_batch(job_id, 2)
        async with db_pool.connection() as conn:
            in_flight_count = await frontier_table.filter({'in_flight': True}
                ).count().run(conn)
        assert in_flight_count == 4
        assert len(batch2) == 1
        assert batch2[0]['url'] == 'https://frontier.example/3'

    async def test_get_frontier_size(self, db_pool, frontier_table):
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        async with db_pool.connection() as conn:
            await frontier_table.insert([{
                'cost': 1.0,
                'job_id': job_id,
                'url': 'https://frontier.example/1',
                'in_flight': False,
            },{
                'cost': 1.0,
                'job_id': job_id,
                'url': 'https://frontier.example/2',
                'in_flight': True,
            }]).run(conn)
        crawl_frontier_db = CrawlFrontierDb(db_pool)
        assert await crawl_frontier_db.get_frontier_size(job_id) == 2


class TestCrawlManagerDb:
    async def test_clear_frontier(self, db_pool, frontier_table):
        job1_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        job2_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        async with db_pool.connection() as conn:
            # There are 2 items in the frontier for job 1 and 1 item for job 2.
            await frontier_table.insert([{
                'cost': 1.0,
                'job_id': job1_id,
                'in_flight': False,
                'url': 'https://job1.example/alpha',
            },{
                'cost': 1.0,
                'job_id': job1_id,
                'in_flight': True,
                'url': 'https://job1.example/bravo',
            },{
                'cost': 1.0,
                'job_id': job2_id,
                'in_flight': False,
                'url': 'https://job2.example/alpha',
            }]).run(conn)
        crawl_manager_db = CrawlManagerDb(db_pool)
        await crawl_manager_db.clear_frontier(job1_id)
        async with db_pool.connection() as conn:
            # The job 1 items should be gone. Only 1 item remains, and it is for
            # job 2.
            size = await frontier_table.count().run(conn)
            item = await frontier_table.nth(0).run(conn)
        assert size == 1
        assert item['url'] == 'https://job2.example/alpha'

    async def test_create_job(self, db_pool, job_table, frontier_table):
        ''' This tests job creation, finish, and getting schedule ID. '''
        started_at = datetime(2018, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        completed_at = datetime(2018, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        job_doc = {
            'name': 'Test Job',
            'seeds': ['https://seed1.example', 'https://seed2.example'],
            'tags': [],
            'run_state': RunState.PENDING,
            'started_at': started_at,
            'completed_at': None,
            'duration': None,
            'item_count': 0,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {},
            'schedule_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }
        crawl_manager_db = CrawlManagerDb(db_pool)
        job_id = await crawl_manager_db.create_job(job_doc)
        async with db_pool.connection() as conn:
            job_count = await job_table.count().run(conn)
            frontier_count = await frontier_table.count().run(conn)
            job = await job_table.get(job_id).run(conn)
        assert job_count == 1
        assert frontier_count == 2
        assert job['name'] == 'Test Job'
        await crawl_manager_db.finish_job(job_id, RunState.CANCELLED,
            completed_at)
        async with db_pool.connection() as conn:
            job = await job_table.get(job_id).run(conn)
        assert job['run_state'] == RunState.CANCELLED
        assert job['completed_at'] == completed_at
        assert job['duration'] == 3600
        schedule_id = await crawl_manager_db.get_job_schedule_id(job_id)
        assert schedule_id == 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

    async def test_get_max_sequence(self, db_pool, response_table):
        crawl_manager_db = CrawlManagerDb(db_pool)
        max_sequence = await crawl_manager_db.get_max_sequence()
        job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        started_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        completed_at = datetime(2019, 1, 1, 12, 0, 1, tzinfo=timezone.utc)
        assert max_sequence == 0
        async with db_pool.connection() as conn:
            await response_table.insert([{
                'sequence': 100,
                'job_id': job_id,
                'url': 'http://sequence.example/1',
                'url_can': 'http://sequence.example/1',
                'started_at': started_at,
                'completed_at': completed_at,
                'duration': 1.0,
                'cost': 1.0,
                'content_type': 'text/plain',
                'status_code': 200,
                'is_success': True,
                'body_id': None,
            },{
                'sequence': 101,
                'job_id': job_id,
                'url': 'http://sequence.example/1',
                'url_can': 'http://sequence.example/1',
                'started_at': started_at,
                'completed_at': completed_at,
                'duration': 1.0,
                'cost': 1.0,
                'content_type': 'text/plain',
                'status_code': 200,
                'is_success': True,
                'body_id': None,
            }]).run(conn)
        max_sequence = await crawl_manager_db.get_max_sequence()
        assert max_sequence == 101

    async def test_get_policy(self, db_pool, captcha_solver_table,
            policy_table):
        captcha_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        catpcha_doc = {
            'id': captcha_id,
            'name': 'CAPTCHA Service',
            'service_url': 'https://captcha.example',
            'api_key': 'FAKE-API-KEY',
            'require_phrase': False,
            'case_sensitive': True,
            'characters': 'ALPHANUMERIC',
            'require_math': False,
            'min_length': 5,
            'max_length': 5,
        }
        policy_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        policy_doc = {
            'id': policy_id,
            'name': 'Test Policy',
            'created_at': created_at,
            'updated_at': created_at,
            'authentication': {
                'enabled': False,
            },
            'captcha_solver_id': captcha_id,
            'limits': {
                'max_cost': 10,
                'max_duration': 3600,
                'max_items': 10_000,
            },
            'mime_type_rules': [
                {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
                {'save': False},
            ],
            'proxy_rules': [],
            'robots_txt': {
                'usage': 'IGNORE',
            },
            'url_normalization': {
                'enabled': True,
                'strip_parameters': [],
            },
            'url_rules': [
                {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
                 'pattern': '^https?://({SEED_DOMAINS})/'},
                {'action': 'MULTIPLY', 'amount': 0},
            ],
            'user_agents': [
                {'name': 'Test User Agent'}
            ]
        }
        async with db_pool.connection() as conn:
            await captcha_solver_table.insert(catpcha_doc).run(conn)
            await policy_table.insert(policy_doc).run(conn)
        crawl_manager_db = CrawlManagerDb(db_pool)
        policy = await crawl_manager_db.get_policy(policy_id)
        assert policy['name'] == 'Test Policy'
        assert 'captcha_solver_id' not in policy
        assert policy['captcha_solver']['service_url'] == \
            'https://captcha.example'

    async def test_pause_resume_job(self, db_pool, captcha_solver_table,
            job_table):
        captcha_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
        catpcha_doc = {
            'id': captcha_id,
            'name': 'CAPTCHA Service',
            'service_url': 'https://captcha.example',
            'api_key': 'FAKE-API-KEY',
            'require_phrase': False,
            'case_sensitive': True,
            'characters': 'ALPHANUMERIC',
            'require_math': False,
            'min_length': 5,
            'max_length': 5,
        }
        created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job_doc = {
            'name': 'Test Job',
            'seeds': ['https://seed1.example', 'https://seed2.example'],
            'tags': [],
            'run_state': RunState.RUNNING,
            'started_at': created_at,
            'completed_at': None,
            'duration': None,
            'item_count': 0,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {},
            'schedule_id': 'cccccccc-cccc-cccc-cccc-cccccccccccc',
            'policy': {
                'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
                'name': 'Test Policy',
                'created_at': created_at,
                'updated_at': created_at,
                'authentication': {
                    'enabled': False,
                },
                'captcha_solver_id': captcha_id,
                'limits': {
                    'max_cost': 10,
                    'max_duration': 3600,
                    'max_items': 10_000,
                },
                'mime_type_rules': [
                    {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
                    {'save': False},
                ],
                'proxy_rules': [],
                'robots_txt': {
                    'usage': 'IGNORE',
                },
                'url_normalization': {
                    'enabled': True,
                    'strip_parameters': [],
                },
                'url_rules': [
                    {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
                     'pattern': '^https?://({SEED_DOMAINS})/'},
                    {'action': 'MULTIPLY', 'amount': 0},
                ],
                'user_agents': [
                    {'name': 'Test User Agent'}
                ],
            },
        }
        async with db_pool.connection() as conn:
            await captcha_solver_table.insert(catpcha_doc).run(conn)
            result = await job_table.insert(job_doc).run(conn)
            job_id = result['generated_keys'][0]
        crawl_manager_db = CrawlManagerDb(db_pool)
        # Old URLs is really a set of hashes, not URLs, but the difference
        # doesn't matter right here:
        old_urls = pickle.dumps({'https://old.example/1',
            'https://old.example/2'})
        await crawl_manager_db.pause_job(job_id, old_urls)
        async with db_pool.connection() as conn:
            job = await job_table.get(job_id).run(conn)
        assert job['run_state'] == RunState.PAUSED
        job = await crawl_manager_db.resume_job(job_id)
        assert job['run_state'] == RunState.RUNNING
        assert job['policy']['captcha_solver']['service_url'] == \
            'https://captcha.example'

    async def test_run_job(self, db_pool, job_table):
        started_at = datetime(2018, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job_doc = {
            'name': 'Test Job',
            'seeds': ['https://seed1.example', 'https://seed2.example'],
            'tags': [],
            'run_state': RunState.PENDING,
            'started_at': started_at,
            'completed_at': None,
            'duration': None,
            'item_count': 0,
            'http_success_count': 0,
            'http_error_count': 0,
            'exception_count': 0,
            'http_status_counts': {},
            'schedule_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        }
        async with db_pool.connection() as conn:
            result = await job_table.insert(job_doc).run(conn)
            job_id = result['generated_keys'][0]
        crawl_manager_db = CrawlManagerDb(db_pool)
        await crawl_manager_db.run_job(job_id)
        async with db_pool.connection() as conn:
            job = await job_table.get(job_id).run(conn)
        assert job['run_state'] == RunState.RUNNING


class TestCrawlStorageDb:
    async def test_save_response(self, db_pool, response_table,
            response_body_table):
        started_at = datetime(2019, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        completed_at = datetime(2019, 2, 1, 12, 0, 3, tzinfo=timezone.utc)
        body_id = '\x01' * 16
        response_doc = {
            'sequence': 1,
            'job_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'url': 'http://response.example',
            'url_can': 'http://response.example',
            'started_at': started_at,
            'completed_at': completed_at,
            'duration': 3.0,
            'cost': 1.0,
            'content_type': 'text/plain',
            'status_code': 200,
            'is_success': True,
            'body_id': body_id,
        }
        response_body_doc = {
            'id': body_id,
            'body': 'Hello world!',
            'is_compressed': False,
        }
        crawl_storage_db = CrawlStorageDb(db_pool)
        await crawl_storage_db.save_response(response_doc, response_body_doc)
        async with db_pool.connection() as conn:
            response_count = await response_table.count().run(conn)
            body_count = await response_body_table.count().run(conn)
        assert response_count == 1
        assert body_count == 1
        # This second document has the same body, so we should end up with two
        # responses but only 1 body.
        response2_doc = {
            'sequence': 2,
            'job_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            'url': 'http://response2.example',
            'url_can': 'http://response2.example',
            'started_at': started_at,
            'completed_at': completed_at,
            'duration': 3.0,
            'cost': 1.0,
            'content_type': 'text/plain',
            'status_code': 200,
            'is_success': True,
            'body_id': body_id,
        }
        await crawl_storage_db.save_response(response2_doc, response_body_doc)
        async with db_pool.connection() as conn:
            response_count = await response_table.count().run(conn)
            body_count = await response_body_table.count().run(conn)
        assert response_count == 2
        assert body_count == 1

    async def test_update_job_stats(self, db_pool, job_table):
        started_at = datetime(2019, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        completed_at = datetime(2019, 2, 1, 12, 0, 3, tzinfo=timezone.utc)
        async with db_pool.connection() as conn:
            result = await job_table.insert({
                'name': 'Test Job',
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'run_state': RunState.RUNNING,
                'started_at': started_at,
                'completed_at': None,
                'duration': 60.0,
                'item_count': 100,
                'http_success_count': 90,
                'http_error_count': 9,
                'exception_count': 1,
                'http_status_counts': {'200': 90, '404': 9},
            }).run(conn)
            job_id = result['generated_keys'][0]
        crawl_storage_db = CrawlStorageDb(db_pool)
        response = DownloadResponse(
            frontier_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
            cost=1.0,
            url='https://storage.example/',
            canonical_url='https://storage.example/',
            content_type='text/plain',
            body=None,
            started_at=started_at,
            completed_at=completed_at,
            exception=None,
            status_code=404,
            headers={'Server': 'Foo'}
        )
        await crawl_storage_db.update_job_stats(job_id, response)
        async with db_pool.connection() as conn:
            job_doc = await job_table.get(job_id).run(conn)
        assert job_doc['item_count'] == 101
        assert job_doc['http_error_count'] == 10


class TestLoginDb:
    async def test_get_login(self, db_pool, domain_login_table):
        async with db_pool.connection() as conn:
            await domain_login_table.insert({
                'domain': 'login.example',
                'login_url': 'https://login.example/login.html',
                'users': [
                    {'username': 'john', 'password': 'fake1'},
                    {'username': 'jane', 'password': 'fake2'},
                ],
            }).run(conn)
        login_db = LoginDb(db_pool)
        login = await login_db.get_login('login.example')
        assert login['domain'] == 'login.example'
        assert len(login['users']) == 2
        assert login['users'][0] == {'username': 'john', 'password': 'fake1'}


class TestScheduleDb:
    async def test_get_schedule_docs(self, db_pool, job_table, schedule_table):
        # Create data fixtures. One schedule has two jobs (we should pick the
        # most recent) and the other schedule has no jobs (we should get None).
        async with db_pool.connection() as conn:
            created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = await schedule_table.insert({
                'schedule_name': 'Schedule 1',
                'enabled': True,
                'created_at': created_at,
                'updated_at': created_at,
                'time_unit': 'HOURS',
                'num_units': 3,
                'timing': 'REGULAR_INTERVAL',
                'job_name': 'Test Job 1',
                'job_count': 1,
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'policy_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            }).run(conn)
            schedule1_id = result['generated_keys'][0]
            result = await schedule_table.insert({
                'schedule_name': 'Schedule 2',
                'enabled': True,
                'created_at': created_at,
                'updated_at': created_at,
                'time_unit': 'HOURS',
                'num_units': 3,
                'timing': 'REGULAR_INTERVAL',
                'job_name': 'Test Job 2',
                'job_count': 1,
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'policy_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            }).run(conn)
            await job_table.insert({
                'name': 'Test Job 1',
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'run_state': RunState.COMPLETED,
                'started_at': datetime(2019, 1, 1, 12, 0, 0,
                    tzinfo=timezone.utc),
                'completed_at': datetime(2019, 1, 1, 13, 0, 0,
                    tzinfo=timezone.utc),
                'duration': 60.0,
                'item_count': 100,
                'http_success_count': 90,
                'http_error_count': 9,
                'exception_count': 1,
                'http_status_counts': {'200': 90, '404': 9},
                'schedule_id': schedule1_id,
            }).run(conn)
            await job_table.insert({
                'name': 'Test Job 2',
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'run_state': RunState.COMPLETED,
                'started_at': datetime(2019, 2, 1, 12, 0, 0,
                    tzinfo=timezone.utc),
                'completed_at': datetime(2019, 2, 1, 12, 0, 0,
                    tzinfo=timezone.utc),
                'duration': 60.0,
                'item_count': 100,
                'http_success_count': 90,
                'http_error_count': 9,
                'exception_count': 1,
                'http_status_counts': {'200': 90, '404': 9},
                'schedule_id': schedule1_id,
            }).run(conn)

        # Run the test.
        schedule_db = ScheduleDb(db_pool)
        schedule_docs = list()
        async for schedule_doc in schedule_db.get_schedule_docs():
            schedule_docs.append(schedule_doc)
        schedule_docs.sort(key=itemgetter('schedule_name'))
        assert schedule_docs[0]['schedule_name'] == 'Schedule 1'
        assert schedule_docs[0]['latest_job']['name'] == 'Test Job 2'
        assert schedule_docs[1]['schedule_name'] == 'Schedule 2'
        assert schedule_docs[1]['latest_job'] is None

    async def test_update_job_count(self, db_pool, schedule_table):
        async with db_pool.connection() as conn:
            created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = await schedule_table.insert({
                'schedule_name': 'Schedule 1',
                'enabled': True,
                'created_at': created_at,
                'updated_at': created_at,
                'time_unit': 'HOURS',
                'num_units': 3,
                'timing': 'REGULAR_INTERVAL',
                'job_name': 'Test Job 1',
                'job_count': 1,
                'seeds': ['https://seed.example'],
                'tags': ['tag1', 'tag2'],
                'policy_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
            }).run(conn)
            schedule_id = result['generated_keys'][0]
        schedule_db = ScheduleDb(db_pool)
        await schedule_db.update_job_count(schedule_id, 2)
        async with db_pool.connection() as conn:
            query = schedule_table.get(schedule_id).pluck('job_count')
            result = await query.run(conn)
        assert result['job_count'] == 2


class TestServerDb():
    def _make_captcha_doc(self):
        return {
            'service_url': 'https://captcha.example',
            'api_key': 'FAKE-API-KEY',
            'require_phrase': False,
            'case_sensitive': False,
            'characters': 'ALPHANUMERIC',
            'require_math': False,
            'min_length': 5,
            'max_length': 5,
        }

    async def test_delete_captcha_solver(self, db_pool, captcha_solver_table,
            policy_table):
        ''' Create two captchas and try to delete them. One can be deleted
        without issue, but the other is referenced by a policy and cannot be
        deleted. '''
        captcha_doc = self._make_captcha_doc()
        async with db_pool.connection() as conn:
            result = await captcha_solver_table.insert([captcha_doc,
                captcha_doc]).run(conn)
            captcha1_id, captcha2_id = result['generated_keys']
            policy_doc = self._make_policy_doc(captcha2_id)
            await policy_table.insert(policy_doc).run(conn)
        server_db = ServerDb(db_pool)

        # Delete 1 captcha:
        await server_db.delete_captcha_solver(captcha1_id)
        async with db_pool.connection() as conn:
            count = await captcha_solver_table.count().run(conn)
        assert count == 1

        # Cannot delete the other captcha:
        with pytest.raises(ValueError):
            await server_db.delete_captcha_solver(captcha2_id)

    async def test_get_captcha_solver(self, db_pool, captcha_solver_table):
        captcha_doc = self._make_captcha_doc()
        async with db_pool.connection() as conn:
            result = await captcha_solver_table.insert(captcha_doc).run(conn)
            captcha_id = result['generated_keys'][0]
        server_db = ServerDb(db_pool)
        doc = await server_db.get_captcha_solver(captcha_id)
        assert doc['service_url'] == 'https://captcha.example'

    async def test_list_captcha_solvers(self, db_pool, captcha_solver_table):
        ''' Create 7 docs. Get pages of 5 items each. '''
        captcha_docs = [self._make_captcha_doc() for _ in range(7)]
        async with db_pool.connection() as conn:
            result = await captcha_solver_table.insert(captcha_docs).run(conn)

        # Get first page:
        server_db = ServerDb(db_pool)
        count, docs = await server_db.list_captcha_solvers(limit=5, offset=0)
        assert count == 7
        assert len(docs) == 5
        assert docs[0]['service_url'] == 'https://captcha.example'

        # Get second page:
        count, docs = await server_db.list_captcha_solvers(limit=5, offset=5)
        assert count == 7
        assert len(docs) == 2
        assert docs[0]['service_url'] == 'https://captcha.example'

    async def test_set_captcha_solver(self, db_pool, captcha_solver_table):
        captcha_doc = self._make_captcha_doc()
        async with db_pool.connection() as conn:
            result = await captcha_solver_table.insert(captcha_doc).run(conn)
            captcha_id = result['generated_keys'][0]

        # Insert one doc
        now = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        server_db = ServerDb(db_pool)
        captcha_id = await server_db.set_captcha_solver(captcha_doc, now)
        assert captcha_id is not None

        # Update one doc
        captcha_doc['id'] = captcha_id
        captcha_id = await server_db.set_captcha_solver(captcha_doc, now)
        assert captcha_id is None

    def _make_domain_login(self):
        return {
            'domain': 'login.example',
            'login_url': 'https://login.example/login.aspx',
            'login_test': None,
            'users': [
                {'username': 'john.doe', 'password': 'fake', 'working': True},
                {'username': 'jane.doe', 'password': 'fake', 'working': True},
            ],
        }

    async def test_delete_domain_login(self, db_pool, domain_login_table):
        domain_login = self._make_domain_login()
        async with db_pool.connection() as conn:
            result = await domain_login_table.insert(domain_login).run(conn)
        server_db = ServerDb(db_pool)
        await server_db.delete_domain_login('login.example')
        async with db_pool.connection() as conn:
            count = await domain_login_table.count().run(conn)
        assert count == 0

    async def test_get_domain_login(self, db_pool, domain_login_table):
        domain_login = self._make_domain_login()
        async with db_pool.connection() as conn:
            result = await domain_login_table.insert(domain_login).run(conn)
        server_db = ServerDb(db_pool)
        doc = await server_db.get_domain_login('login.example')
        assert doc['login_url'] == 'https://login.example/login.aspx'
        assert doc['users'][0]['username'] == 'john.doe'

    async def test_list_domain_logins(self, db_pool, domain_login_table):
        ''' Create 7 docs. Get pages of 5 items each. '''
        # This table's primary key is domain, so we'll change the domain for
        # each login to make it unique.
        domain_logins = list()
        for i in range(7):
            dl = self._make_domain_login()
            dl['domain'] = 'login{}.example'.format(i)
            dl['login_url'] = 'https://login{}.example/login.aspx'.format(i)
            domain_logins.append(dl)
        async with db_pool.connection() as conn:
            result = await domain_login_table.insert(domain_logins).run(conn)

        # Get first page:
        server_db = ServerDb(db_pool)
        count, docs = await server_db.list_domain_logins(limit=5, offset=0)
        assert count == 7
        assert len(docs) == 5
        assert docs[0]['login_url'] == 'https://login0.example/login.aspx'

        # Get second page:
        count, docs = await server_db.list_domain_logins(limit=5, offset=5)
        assert count == 7
        assert len(docs) == 2
        assert docs[0]['login_url'] == 'https://login5.example/login.aspx'

    async def test_set_domain_login(self, db_pool, domain_login_table):
        # Insert domain login:
        domain_login = self._make_domain_login()
        server_db = ServerDb(db_pool)
        await server_db.set_domain_login(domain_login)
        async with db_pool.connection() as conn:
            result = await domain_login_table.get('login.example').run(conn)
        assert result['login_url'] == 'https://login.example/login.aspx'
        assert len(result['users']) == 2

        # Update domain login:
        domain_login['login_url'] = 'https://login.example/login.php'
        await server_db.set_domain_login(domain_login)
        async with db_pool.connection() as conn:
            result = await domain_login_table.get('login.example').run(conn)
        assert result['login_url'] == 'https://login.example/login.php'
        assert len(result['users']) == 2

    def _make_policy_doc(self, captcha_id=None):
        created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        return {
            'name': 'Test Policy',
            'created_at': created_at,
            'updated_at': created_at,
            'authentication': {
                'enabled': False,
            },
            'captcha_solver_id': captcha_id,
            'limits': {
                'max_cost': 10,
                'max_duration': 3600,
                'max_items': 10_000,
            },
            'mime_type_rules': [
                {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
                {'save': False},
            ],
            'proxy_rules': [],
            'robots_txt': {
                'usage': 'IGNORE',
            },
            'url_normalization': {
                'enabled': True,
                'strip_parameters': [],
            },
            'url_rules': [
                {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
                 'pattern': '^https?://({SEED_DOMAINS})/'},
                {'action': 'MULTIPLY', 'amount': 0},
            ],
            'user_agents': [
                {'name': 'Test User Agent'}
            ],
        }

    async def test_delete_policy(self, db_pool, policy_table):
        policy = self._make_policy_doc()
        async with db_pool.connection() as conn:
            result = await policy_table.insert(policy).run(conn)
            policy_id = result['generated_keys'][0]
        server_db = ServerDb(db_pool)
        await server_db.delete_policy(policy_id)
        async with db_pool.connection() as conn:
            count = await policy_table.count().run(conn)
        assert count == 0

    async def test_get_policy(self, db_pool, policy_table):
        policy = self._make_policy_doc()
        async with db_pool.connection() as conn:
            result = await policy_table.insert(policy).run(conn)
            policy_id = result['generated_keys'][0]
        server_db = ServerDb(db_pool)
        doc = await server_db.get_policy(policy_id)
        assert doc['name'] == 'Test Policy'

    async def test_list_policies(self, db_pool, policy_table):
        ''' Create 7 docs. Get pages of 5 items each. '''
        # This table's primary key is domain, so we'll change the domain for
        # each login to make it unique.
        policies = [self._make_policy_doc() for _ in range(7)]
        async with db_pool.connection() as conn:
            result = await policy_table.insert(policies).run(conn)

        # Get first page:
        server_db = ServerDb(db_pool)
        count, docs = await server_db.list_policies(limit=5, offset=0)
        assert count == 7
        assert len(docs) == 5
        assert docs[0]['name'] == 'Test Policy'

        # Get second page:
        count, docs = await server_db.list_policies(limit=5, offset=5)
        assert count == 7
        assert len(docs) == 2
        assert docs[0]['name'] == 'Test Policy'

    async def test_set_policy(self, db_pool, policy_table):
        # Insert policy:
        policy_doc = self._make_policy_doc()
        server_db = ServerDb(db_pool)
        now = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        policy_id = await server_db.set_policy(policy_doc, now)
        assert policy_id is not None
        async with db_pool.connection() as conn:
            policy2_doc = await policy_table.get(policy_id).run(conn)
        assert policy2_doc['name'] == 'Test Policy'
        assert policy2_doc['created_at'] == now
        assert policy2_doc['updated_at'] == now

        # Update policy:
        policy2_doc['name'] = 'Test Policy 2'
        now2 = datetime(2019, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        policy2_id = await server_db.set_policy(policy2_doc, now2)
        assert policy2_id is None
        async with db_pool.connection() as conn:
            result = await policy_table.get(policy_id).run(conn)
        assert result['name'] == 'Test Policy 2'
        assert result['created_at'] == now
        assert result['updated_at'] == now2

    async def test_list_rate_limits(self, db_pool, rate_limit_table):
        token = '\xaa' * 16
        async with db_pool.connection() as conn:
            await rate_limit_table.insert({
                'name': 'domain:rate-limit.example',
                'token': token,
                'delay': 1.5,
            }).run(conn)
        server_db = ServerDb(db_pool)
        count, rate_limits = await server_db.list_rate_limits(10, 0)
        assert count == 1
        assert rate_limits[0]['name'] == 'domain:rate-limit.example'
        assert rate_limits[0]['token'] == token
        assert rate_limits[0]['delay'] == 1.5

    async def test_set_rate_limit(self, db_pool, rate_limit_table):
        token = '\xaa' * 16
        server_db = ServerDb(db_pool)
        await server_db.set_rate_limit('domain:rate-limit.example', token, 1.5)
        async with db_pool.connection() as conn:
            rate_limit = await rate_limit_table.get(token).run(conn)
        assert rate_limit['name'] == 'domain:rate-limit.example'
        assert rate_limit['token'] == token
        assert rate_limit['delay'] == 1.5

    def _make_schedule_doc(self):
        dt = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        return {
            'schedule_name': 'Test Schedule',
            'enabled': True,
            'created_at': dt,
            'updated_at': dt,
            'time_unit': 'DAYS',
            'num_units': 7,
            'timing': 'REGULAR_INTERVAL',
            'job_name': 'Test Job #{JOB_COUNT}',
            'job_count': 1,
            'seeds': ['https://schedule.example'],
            'tags': ['schedule1', 'schedule2'],
            'policy_id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        }

    async def test_delete_schedule(self, db_pool, schedule_table):
        schedule = self._make_schedule_doc()
        async with db_pool.connection() as conn:
            result = await schedule_table.insert(schedule).run(conn)
            schedule_id = result['generated_keys'][0]
        server_db = ServerDb(db_pool)
        await server_db.delete_schedule(schedule_id)
        async with db_pool.connection() as conn:
            count = await schedule_table.count().run(conn)
        assert count == 0

    async def test_get_schedule(self, db_pool, schedule_table):
        schedule = self._make_schedule_doc()
        async with db_pool.connection() as conn:
            result = await schedule_table.insert(schedule).run(conn)
            schedule_id = result['generated_keys'][0]
        server_db = ServerDb(db_pool)
        doc = await server_db.get_schedule(schedule_id)
        assert doc['schedule_name'] == 'Test Schedule'

    async def test_list_schedules(self, db_pool, schedule_table):
        ''' Create 7 docs. Get pages of 5 items each. '''
        # This table's primary key is domain, so we'll change the domain for
        # each login to make it unique.
        schedules = [self._make_schedule_doc() for _ in range(7)]
        async with db_pool.connection() as conn:
            result = await schedule_table.insert(schedules).run(conn)

        # Get first page:
        server_db = ServerDb(db_pool)
        count, docs = await server_db.list_schedules(limit=5, offset=0)
        assert count == 7
        assert len(docs) == 5
        assert docs[0]['schedule_name'] == 'Test Schedule'

        # Get second page:
        count, docs = await server_db.list_schedules(limit=5, offset=5)
        assert count == 7
        assert len(docs) == 2
        assert docs[0]['schedule_name'] == 'Test Schedule'

    async def test_set_schedule(self, db_pool, job_table, schedule_table):
        # Insert policy:
        schedule_doc = self._make_schedule_doc()
        server_db = ServerDb(db_pool)
        now = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = await server_db.set_schedule(schedule_doc, now)
        assert 'latest_job' in result
        assert result['schedule_name'] == 'Test Schedule'
        assert result['created_at'] == now
        assert result['updated_at'] == now

        # Update policy:
        schedule2_doc = result.copy()
        schedule2_doc['schedule_name'] = 'Test Schedule 2'
        now2 = datetime(2019, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        result2 = await server_db.set_schedule(schedule2_doc, now2)
        assert 'latest_job' in result2
        assert result2['schedule_name'] == 'Test Schedule 2'
        assert result2['created_at'] == now
        assert result2['updated_at'] == now2
