from datetime import datetime
from unittest.mock import Mock

import pytest
from rethinkdb import RethinkDB
import trio
import trio_asyncio

from starbelly.downloader import DownloadResponse
from starbelly.policy import Policy
from starbelly.robots import RobotsTxt, RobotsTxtManager


def make_policy(usage, user_agent):
    ''' Make a sample policy. '''
    dt = datetime(2018,12,31,13,47,00)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': dt,
        'updated_at': dt,
        'authentication': {
            'enabled': False,
        },
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'save': True},
        ],
        'proxy_rules': [],
        'robots_txt': {
            'usage': usage,
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': [],
        },
        'url_rules': [
            {'action': 'MULTIPLY', 'amount': 0},
        ],
        'user_agents': [
            {'name': user_agent}
        ]
    }
    return Policy(doc, '1.0.0', ['https://seeds.example'])


@pytest.fixture
async def db_pool(nursery):
    r = RethinkDB()
    r.set_loop_type('trio')
    db_pool = r.ConnectionPool(db='test', nursery=nursery)
    async with db_pool.connection() as conn:
        await r.table_create('robots_txt').run(conn)
        await r.table('robots_txt').index_create('url').run(conn)
        await r.table('robots_txt').index_wait('url')
    yield db_pool
    async with db_pool.connection() as conn:
        await r.table_drop('robots_txt').run(conn)
    await db_pool.close()


@pytest.fixture
async def asyncio_loop():
    async with trio_asyncio.open_loop() as loop:
        yield


async def test_fetch_robots(asyncio_loop, db_pool, nursery):
    ''' The robots.txt manager should fetch a robots.txt file by sending a
    request to its downloader channel. '''
    async def serve_robots():
        nonlocal serve_count
        request = await request_recv.receive()
        assert str(request.url) == 'https://www.example/robots.txt'
        response = DownloadResponse.from_request(request)
        response.content_type: 'text/plain'
        response.body = \
            b'User-agent: *\n' \
            b'Disallow: /foo/\n' \
            b'\n' \
            b'User-agent: TestAgent1\n' \
            b'Disallow: /bar/\n'
        response.status_code = 200
        await response_send.send(response)
        serve_count += 1

    serve_count = 0
    nursery.start_soon(serve_robots)
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    rtm = RobotsTxtManager(db_pool, request_send, response_recv)

    policy1 = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy1)
    assert await rtm.is_allowed('https://www.example/foo/', policy1)
    assert not await rtm.is_allowed('https://www.example/bar/', policy1)

    policy2 = make_policy(usage='OBEY', user_agent='TestAgent2')
    assert await rtm.is_allowed('https://www.example/index.html', policy2)
    assert not await rtm.is_allowed('https://www.example/foo/', policy2)
    assert await rtm.is_allowed('https://www.example/bar/', policy2)

    # The file should only be fetched one time, and then served from cache for
    # subsequent requests.
    assert serve_count == 1
