from datetime import datetime, timezone
from itertools import count
from unittest.mock import Mock

from yarl import URL
import trio

from . import AsyncMock
from starbelly.downloader import DownloadResponse
from starbelly.policy import Policy
from starbelly.storage import CrawlStorage


def make_policy():
    ''' Make a sample policy. '''
    dt = datetime(2018,12,31,13,47,00)
    doc = {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test',
        'created_at': dt,
        'updated_at': dt,
        'authentication': {
            'enabled': False,
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
    return Policy(doc, '1.0.0', ['https://seeds.example'])


async def test_storage(nursery):
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa'
    db = Mock()
    db.save_response = AsyncMock()
    db.update_job_stats = AsyncMock()
    test_send, storage_receive = trio.open_memory_channel(0)
    storage_send, test_receive = trio.open_memory_channel(0)
    policy = make_policy()
    sequence = count(start=100)
    storage = CrawlStorage(job_id, db, storage_send, storage_receive, policy,
        sequence)
    assert repr(storage) == '<CrawlStorage job_id=aaaaaaaa>'
    nursery.start_soon(storage.run)
    started_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completed_at = datetime(2019, 1, 1, 12, 0, 3, tzinfo=timezone.utc)
    response = DownloadResponse(
        frontier_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        cost=1.0,
        url='https://storage.example/',
        canonical_url='https://storage.example/',
        content_type='text/plain',
        body=b'Hello, world!',
        started_at=started_at,
        completed_at=completed_at,
        exception=None,
        status_code=200,
        headers={'Server': 'FooServe 1.0'}
    )
    response.duration = 3.0
    await test_send.send(response)
    response2 = await test_receive.receive()
    assert response is response2
    assert db.save_response.call_count == 1
    save_response_args = db.save_response.call_args
    assert save_response_args[0] == {
        'sequence': 100,
        'job_id': job_id,
        'body_id': b'\x9b\xbb\xb7A\x0f\xa6FJ\x1aj!i\x19\x17\x94U',
        'url': 'https://storage.example/',
        'canonical_url': 'https://storage.example/',
        'content_type': 'text/plain',
        'cost': 1.0,
        'duration': 3.0,
        'headers': ['SERVER', 'FooServe 1.0'],
        'is_success': True,
        'status_code': 200,
        'started_at': started_at,
        'completed_at': completed_at,
    }
    # Note that the gzip'ed body is non deterministic, so we only check body ID
    # and is_compressed fields.
    assert save_response_args[1]['id'] == \
        b'\x9b\xbb\xb7A\x0f\xa6FJ\x1aj!i\x19\x17\x94U'
    assert save_response_args[1]['is_compressed']
    assert db.update_job_stats.call_count == 1
