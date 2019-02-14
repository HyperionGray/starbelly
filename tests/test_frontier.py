from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import trio

from . import AsyncMock
from starbelly.frontier import (
    CrawlFrontier,
    FrontierItem,
    FrontierExhaustionError,
)
from starbelly.policy import Policy


def make_policy():
    created_at = datetime(2018,12,31,13,47,00)
    policy_doc = {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': created_at,
        'authentication': {
            'enabled': True,
        },
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
            'strip_parameters': ['b'],
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
    return Policy(policy_doc, '1.0.0', ['https://frontier.example'])


async def test_frontier_exhaustion(nursery):
    # Set up test fixtures
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    db.any_in_flight = AsyncMock()
    db.get_frontier_batch = AsyncMock(return_value=list())
    db.get_frontier_size = AsyncMock(return_value=5)
    send_channel, recv_channel = trio.open_memory_channel(0)
    login_manager = Mock()
    login_manager.login = AsyncMock()
    policy = make_policy()
    stats = dict()
    frontier = CrawlFrontier(job_id, db, send_channel, login_manager, policy,
        stats)

    # This test has an empty frontier, so it should raise an exhaustion error
    # in its run() method.
    with pytest.raises(FrontierExhaustionError):
        await frontier.run()


async def test_frontier_batches(autojump_clock, nursery):
    # Set up test fixtures
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    db.any_in_flight = AsyncMock()
    batch1 = [{
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'cost': 1.0,
        'job_id': job_id,
        'url': 'https://frontier.example/1',
        'in_flight': False,
    },{
        'id': 'cccccccc-cccc-cccc-cccc-cccccccccccc',
        'cost': 2.0,
        'job_id': job_id,
        'url': 'https://frontier.example/2',
        'in_flight': False,
    }]
    batch2 = [{
        'id': 'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'cost': 3.0,
        'job_id': job_id,
        'url': 'https://frontier.example/3',
        'in_flight': False,
    }]
    db.get_frontier_batch = AsyncMock(return_values=(batch1, batch2, []))
    db.get_frontier_size = AsyncMock(return_value=5)
    send_channel, recv_channel = trio.open_memory_channel(0)
    login_manager = Mock()
    login_manager.login = AsyncMock()
    policy = make_policy()
    stats = dict()
    frontier = CrawlFrontier(job_id, db, send_channel, login_manager, policy,
        stats)
    assert repr(frontier) == '<CrawlFrontier job_id=aaaaaaaa>'
    nursery.start_soon(frontier.run)

    # Wait for the first item from the frontier. It should trigger the login
    # manager to log in to this domain, and also check the robots.txt to see if
    # the item is allowed.
    item1 = await recv_channel.receive()
    assert login_manager.login.call_count == 1
    assert login_manager.login.call_args[0] == 'frontier.example'
    assert str(item1.url) == 'https://frontier.example/1'
    assert item1.cost == 1.0
    assert item1.job_id == job_id
    assert item1.frontier_id == 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
