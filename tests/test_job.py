from datetime import datetime, timezone
import logging
import pickle
from unittest.mock import Mock

import pytest
import trio

from . import AsyncMock, asyncio_loop, fail_after
from starbelly.frontier import FrontierExhaustionError
from starbelly.job import (
    PipelineTerminator,
    RunState,
    StatsTracker,
    CrawlManager,
)


logger = logging.getLogger(__name__)


def make_policy_doc():
    created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test Policy',
        'created_at': created_at,
        'updated_at': created_at,
        'authentication': {'enabled': True},
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
            'strip_parameters': ['PHPSESSID'],
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


@fail_after(3)
async def test_start_job(asyncio_loop, nursery):
    # Set up fixtures
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    policy_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    rate_limiter = Mock()
    stats_tracker = StatsTracker()
    robots_txt_manager = Mock()
    manager_db = Mock()
    manager_db.clear_frontier = AsyncMock()
    manager_db.create_job = AsyncMock(job_id)
    manager_db.finish_job = AsyncMock()
    manager_db.get_max_sequence = AsyncMock(100)
    manager_db.get_policy = AsyncMock(make_policy_doc())
    manager_db.run_job = AsyncMock()
    frontier_db = Mock()
    frontier_db.any_in_flight = AsyncMock(False)
    frontier_db.get_frontier_batch = AsyncMock({})
    frontier_db.get_frontier_size = AsyncMock(0)
    frontier_db.run = AsyncMock()
    extractor_db = Mock()
    storage_db = Mock()
    login_db = Mock()
    crawl_manager = CrawlManager(rate_limiter, stats_tracker,
        robots_txt_manager, manager_db, frontier_db, extractor_db, storage_db,
        login_db)

    # Run the crawl manager and start a new job
    await nursery.start(crawl_manager.run)
    await crawl_manager.start_job('Test Job', ['https://seed.example'],
        ['tag1'], policy_id)

    # Wait for the crawler to tell us that the job is running.
    recv_channel = crawl_manager.get_job_state_channel()
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.RUNNING

    resources = crawl_manager.get_resource_usage()
    assert resources['maximum_downloads'] == 20
    assert resources['current_downloads'] == 0
    assert resources['jobs'][0]['id'] == job_id
    assert resources['jobs'][0]['name'] == 'Test Job'
    assert resources['jobs'][0]['current_downloads'] == 0

    # The job has an empty frontier, so it will quit immediately after starting.
    # Wait for the completed job state.
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.COMPLETED

    # Make sure the manager interacted with other objects correctly.
    assert manager_db.clear_frontier.call_args[0] == job_id
    assert manager_db.finish_job.call_args[0] == job_id
    assert manager_db.finish_job.call_args[1] == RunState.COMPLETED
    assert manager_db.get_policy.call_args[0] == policy_id
    assert manager_db.run_job.call_args[0] == job_id
    assert frontier_db.get_frontier_batch.call_args[0] == job_id

    stats = stats_tracker.snapshot()
    assert stats[0]['id'] == job_id
    assert stats[0]['name'] == 'Test Job'
    assert stats[0]['run_state'] == RunState.COMPLETED
    assert stats[0]['seeds'] == ['https://seed.example']
    assert stats[0]['tags'] == ['tag1']


@fail_after(3)
async def test_pause_resume_cancel(asyncio_loop, nursery):
    # Set up fixtures
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    job_doc = {
        'id': job_id,
        'name': 'Test Job',
        'seeds': ['https://seed1.example', 'https://seed2.example'],
        'tags': [],
        'run_state': RunState.PAUSED,
        'old_urls': b'\x80\x03cbuiltins\nset\nq\x00]q\x01C\x10\xad\xb6\x93\x9b'
                    b'\xac\x92\xd8\xfd\xc0\x8dJ\x94^\x8d\xe5~q\x02a\x85q\x03Rq'
                    b'\x04.',
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
            'captcha_solver_id': None,
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

    rate_limiter = Mock()
    stats_tracker = StatsTracker()
    robots_txt_manager = Mock()
    manager_db = Mock()
    manager_db.clear_frontier = AsyncMock()
    manager_db.create_job = AsyncMock(job_id)
    manager_db.finish_job = AsyncMock()
    manager_db.get_max_sequence = AsyncMock(100)
    manager_db.get_policy = AsyncMock(make_policy_doc())
    manager_db.resume_job = AsyncMock(job_doc)
    manager_db.pause_job = AsyncMock()
    manager_db.run_job = AsyncMock()
    frontier_db = Mock()
    frontier_db.any_in_flight = AsyncMock(True)
    frontier_db.get_frontier_batch = AsyncMock({})
    frontier_db.get_frontier_size = AsyncMock(0)
    frontier_db.run = AsyncMock()
    extractor_db = Mock()
    storage_db = Mock()
    login_db = Mock()
    crawl_manager = CrawlManager(rate_limiter, stats_tracker,
        robots_txt_manager, manager_db, frontier_db, extractor_db, storage_db,
        login_db)

    # Run the crawl manager and start a new job
    await nursery.start(crawl_manager.run)
    await crawl_manager.start_job(job_doc['name'], job_doc['seeds'],
        job_doc['tags'], job_doc['policy']['id'])

    # Wait for the crawler to tell us that the job is running.
    recv_channel = crawl_manager.get_job_state_channel()
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.RUNNING

    # Now pause and wait for the paused event.
    await crawl_manager.pause_job(job_id)
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.PAUSED
    assert manager_db.pause_job.call_args[0] == job_id
    # There are two "old URLs": the seed URLs.
    assert len(pickle.loads(manager_db.pause_job.call_args[1])) == 2
    assert stats_tracker.snapshot()[0]['run_state'] == RunState.PAUSED

    # Now resume and wait for the running event.
    await crawl_manager.resume_job(job_id)
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.RUNNING
    assert manager_db.resume_job.call_args[0] == job_id

    # Now cancel and wait for the cancelled event
    await crawl_manager.cancel_job(job_id)
    state_event = await recv_channel.receive()
    assert state_event.run_state == RunState.CANCELLED
    assert manager_db.finish_job.call_args[0] == job_id
    assert manager_db.finish_job.call_args[1] == RunState.CANCELLED
