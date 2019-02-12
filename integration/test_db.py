from datetime import datetime, timezone
from operator import itemgetter

import pytest
from rethinkdb import RethinkDB

from starbelly.db import ScheduleDb
from starbelly.job import RunState


r = RethinkDB()
r.set_loop_type('trio')


@pytest.fixture
async def db_pool(nursery):
    db_pool = r.ConnectionPool(db='test', nursery=nursery)
    yield db_pool
    await db_pool.close()


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
async def schedule_table(db_pool):
    async with db_pool.connection() as conn:
        await r.table_create('schedule').run(conn)
        await r.table('schedule').index_create('schedule_name').run(conn)
        await r.table('schedule').index_wait('schedule_name').run(conn)
    yield r.table('schedule')
    async with db_pool.connection() as conn:
        await r.table_drop('schedule').run(conn)


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



