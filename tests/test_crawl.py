'''
Tests for crawl pipeline components: CrawlJob, PipelineTerminator,
StatsTracker, RunState, and JobStateEvent.
'''
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
import trio

from . import AsyncMock, fail_after
from starbelly.downloader import Downloader
from starbelly.extractor import CrawlExtractor
from starbelly.frontier import CrawlFrontier
from starbelly.job import (
    CrawlJob,
    JobStateEvent,
    PipelineTerminator,
    RunState,
    StatsTracker,
)
from starbelly.policy import Policy
from starbelly.storage import CrawlStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_policy_doc():
    dt = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test Policy',
        'created_at': dt,
        'updated_at': dt,
        'authentication': {'enabled': False},
        'limits': {
            'max_cost': 10,
            'max_duration': None,
            'max_items': 10_000,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [],
        'robots_txt': {'usage': 'IGNORE'},
        'url_normalization': {
            'enabled': True,
            'strip_parameters': [],
        },
        'url_rules': [
            {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
             'pattern': '^https?://({SEED_DOMAINS})/'},
            {'action': 'MULTIPLY', 'amount': 0},
        ],
        'user_agents': [{'name': 'Test User Agent'}],
    }


def make_policy():
    return Policy(make_policy_doc(), '1.0.0', ['https://seed.example'])


def make_crawl_job(policy=None, schedule_id=None):
    '''Create a CrawlJob with mocked sub-components.'''
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    if policy is None:
        policy = make_policy()

    frontier = Mock(spec=CrawlFrontier)
    frontier.run = AsyncMock()
    downloader = Mock(spec=Downloader)
    downloader.run = AsyncMock()
    downloader.count = 0
    storage = Mock(spec=CrawlStorage)
    storage.run = AsyncMock()
    extractor = Mock(spec=CrawlExtractor)
    extractor.run = AsyncMock()
    extractor.old_urls = set()
    terminator = Mock(spec=PipelineTerminator)
    terminator.run = AsyncMock()

    return CrawlJob(
        name='Test Crawl',
        job_id=job_id,
        schedule_id=schedule_id,
        policy=policy,
        frontier=frontier,
        downloader=downloader,
        storage=storage,
        extractor=extractor,
        terminator=terminator,
    )


def make_stats_doc(job_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', **overrides):
    '''Create a stats document for StatsTracker.'''
    doc = {
        'id': job_id,
        'name': 'Test Job',
        'run_state': RunState.RUNNING,
        'seeds': ['https://seed.example'],
        'tags': ['tag1'],
        'started_at': datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        'completed_at': None,
        'item_count': 0,
        'http_success_count': 0,
        'http_error_count': 0,
        'exception_count': 0,
        'http_status_counts': {},
    }
    doc.update(overrides)
    return doc


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------

def test_run_state_values():
    assert RunState.PENDING == 'pending'
    assert RunState.PAUSED == 'paused'
    assert RunState.RUNNING == 'running'
    assert RunState.CANCELLED == 'cancelled'
    assert RunState.COMPLETED == 'completed'


# ---------------------------------------------------------------------------
# JobStateEvent
# ---------------------------------------------------------------------------

def test_job_state_event_fields():
    now = datetime.now(timezone.utc)
    event = JobStateEvent(
        job_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        schedule_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        run_state=RunState.RUNNING,
        event_time=now,
    )
    assert event.job_id == 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    assert event.schedule_id == 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    assert event.run_state == RunState.RUNNING
    assert event.event_time == now


def test_job_state_event_none_schedule():
    event = JobStateEvent(
        job_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        schedule_id=None,
        run_state=RunState.PENDING,
        event_time=datetime.now(timezone.utc),
    )
    assert event.schedule_id is None


# ---------------------------------------------------------------------------
# StatsTracker
# ---------------------------------------------------------------------------

def test_stats_tracker_add_and_snapshot():
    tracker = StatsTracker(timedelta(seconds=60))
    doc = make_stats_doc()
    tracker.add_job(doc)
    snapshot = tracker.snapshot()
    assert len(snapshot) == 1
    assert snapshot[0]['id'] == doc['id']
    assert snapshot[0]['name'] == 'Test Job'
    assert snapshot[0]['run_state'] == RunState.RUNNING
    assert snapshot[0]['seeds'] == ['https://seed.example']
    assert snapshot[0]['tags'] == ['tag1']


def test_stats_tracker_snapshot_copies():
    '''Snapshot should return copies, not references to internal data.'''
    tracker = StatsTracker(timedelta(seconds=60))
    doc = make_stats_doc()
    tracker.add_job(doc)
    snapshot = tracker.snapshot()
    snapshot[0]['seeds'].append('https://extra.example')
    snapshot[0]['tags'].append('extra')
    snapshot[0]['http_status_counts'][404] = 5
    fresh = tracker.snapshot()
    assert fresh[0]['seeds'] == ['https://seed.example']
    assert fresh[0]['tags'] == ['tag1']
    assert fresh[0]['http_status_counts'] == {}


def test_stats_tracker_delete_job():
    tracker = StatsTracker(timedelta(seconds=60))
    doc = make_stats_doc()
    tracker.add_job(doc)
    assert len(tracker.snapshot()) == 1
    tracker.delete_job(doc['id'])
    assert len(tracker.snapshot()) == 0


def test_stats_tracker_complete_job():
    tracker = StatsTracker(timedelta(seconds=60))
    doc = make_stats_doc()
    tracker.add_job(doc)
    now = datetime.now(timezone.utc)
    tracker.complete_job(doc['id'], now)
    snapshot = tracker.snapshot()
    assert snapshot[0]['completed_at'] == now


def test_stats_tracker_set_run_state():
    tracker = StatsTracker(timedelta(seconds=60))
    doc = make_stats_doc()
    tracker.add_job(doc)
    tracker.set_run_state(doc['id'], RunState.PAUSED)
    snapshot = tracker.snapshot()
    assert snapshot[0]['run_state'] == RunState.PAUSED


def test_stats_tracker_prunes_old_completed_jobs():
    '''Completed jobs older than the recent window should be pruned.'''
    tracker = StatsTracker(timedelta(seconds=60))
    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    doc = make_stats_doc()
    tracker.add_job(doc)
    tracker.complete_job(doc['id'], old_time)
    snapshot = tracker.snapshot()
    assert len(snapshot) == 0


def test_stats_tracker_keeps_recent_completed_jobs():
    '''Completed jobs within the recent window should be kept.'''
    tracker = StatsTracker(timedelta(seconds=60))
    recent_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    doc = make_stats_doc()
    tracker.add_job(doc)
    tracker.complete_job(doc['id'], recent_time)
    snapshot = tracker.snapshot()
    assert len(snapshot) == 1


def test_stats_tracker_multiple_jobs():
    tracker = StatsTracker(timedelta(seconds=60))
    doc1 = make_stats_doc(job_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
                          name='Job A')
    doc2 = make_stats_doc(job_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
                          name='Job B')
    tracker.add_job(doc1)
    tracker.add_job(doc2)
    snapshot = tracker.snapshot()
    assert len(snapshot) == 2
    names = {s['name'] for s in snapshot}
    assert names == {'Job A', 'Job B'}


# ---------------------------------------------------------------------------
# PipelineTerminator
# ---------------------------------------------------------------------------

async def test_pipeline_terminator_reads_all(nursery):
    '''PipelineTerminator should drain all items from a channel.'''
    send, recv = trio.open_memory_channel(10)
    terminator = PipelineTerminator(recv)
    nursery.start_soon(terminator.run)
    for i in range(5):
        await send.send(i)
    await send.aclose()
    # Give the terminator time to drain
    await trio.testing.wait_all_tasks_blocked()


async def test_pipeline_terminator_empty_channel(nursery):
    '''PipelineTerminator should handle an immediately closed channel.'''
    send, recv = trio.open_memory_channel(0)
    terminator = PipelineTerminator(recv)
    await send.aclose()
    # run() should return without error when channel is closed immediately
    await terminator.run()


# ---------------------------------------------------------------------------
# CrawlJob
# ---------------------------------------------------------------------------

def test_crawl_job_properties():
    job = make_crawl_job(schedule_id='cccccccc-cccc-cccc-cccc-cccccccccccc')
    assert job.id == 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    assert job.name == 'Test Crawl'
    assert job.schedule_id == 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    assert job.current_downloads == 0


def test_crawl_job_repr():
    job = make_crawl_job()
    r = repr(job)
    assert 'aaaaaaaa' in r
    assert 'Test Crawl' in r


def test_crawl_job_old_urls():
    job = make_crawl_job()
    assert job.old_urls == set()


def test_crawl_job_none_schedule():
    job = make_crawl_job(schedule_id=None)
    assert job.schedule_id is None


@fail_after(3)
async def test_crawl_job_stop(nursery):
    '''A running CrawlJob can be stopped via stop().'''
    job = make_crawl_job()
    nursery.start_soon(job.run)
    await trio.testing.wait_all_tasks_blocked()
    await job.stop()


@fail_after(3)
async def test_crawl_job_stop_before_start():
    '''Calling stop() before run() raises an exception.'''
    job = make_crawl_job()
    with pytest.raises(Exception, match='Cannot cancel job'):
        await job.stop()