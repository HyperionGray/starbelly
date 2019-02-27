'''
A lot of these tests mock up internal APIs in the robots manager, which isn't
great but is the most expedient way to get this working.
'''
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from rethinkdb import RethinkDB
import trio

from . import asyncio_loop, AsyncMock
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


async def download(request):
    ''' A mock download function that returns a fixed response. '''
    response = DownloadResponse.from_request(request)
    response.content_type = 'text/plain'
    response.body = \
        b'User-agent: *\n' \
        b'Disallow: /foo/\n' \
        b'\n' \
        b'User-agent: TestAgent1\n' \
        b'Disallow: /bar/\n'
    response.status_code = 200
    return response


async def test_fetch_robots(asyncio_loop, nursery):
    ''' The robots.txt manager should fetch a robots.txt file by sending a
    request to its downloader channel. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy1 = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy1, dl)
    assert await rtm.is_allowed('https://www.example/foo/', policy1, dl)
    assert not await rtm.is_allowed('https://www.example/bar/', policy1, dl)

    policy2 = make_policy(usage='OBEY', user_agent='TestAgent2')
    assert await rtm.is_allowed('https://www.example/index.html', policy2, dl)
    assert not await rtm.is_allowed('https://www.example/foo/', policy2, dl)
    assert await rtm.is_allowed('https://www.example/bar/', policy2, dl)

    # The file should only be fetched one time, and then served from cache for
    # subsequent requests.
    assert dl.download.call_count == 1


async def test_fetch_robots_invert(asyncio_loop, nursery):
    ''' Do the opposite of what robots.txt says. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy1 = make_policy(usage='INVERT', user_agent='TestAgent1')
    assert not await rtm.is_allowed('https://www.example/index', policy1, dl)
    assert not await rtm.is_allowed('https://www.example/foo/', policy1, dl)
    assert await rtm.is_allowed('https://www.example/bar/', policy1, dl)

    policy2 = make_policy(usage='INVERT', user_agent='TestAgent2')
    assert not await rtm.is_allowed('https://www.example/index', policy2, dl)
    assert await rtm.is_allowed('https://www.example/foo/', policy2, dl)
    assert not await rtm.is_allowed('https://www.example/bar/', policy2, dl)

    # The file should only be fetched one time, and then served from cache for
    # subsequent requests.
    assert dl.download.call_count == 1


async def test_fetch_robots_ignore(asyncio_loop, nursery):
    ''' Ignore what robots.txt says. Don't even fetch it. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy1 = make_policy(usage='IGNORE', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy1, dl)
    assert await rtm.is_allowed('https://www.example/foo/', policy1, dl)
    assert await rtm.is_allowed('https://www.example/bar/', policy1, dl)

    policy2 = make_policy(usage='IGNORE', user_agent='TestAgent2')
    assert await rtm.is_allowed('https://www.example/index.html', policy2, dl)
    assert await rtm.is_allowed('https://www.example/foo/', policy2, dl)
    assert await rtm.is_allowed('https://www.example/bar/', policy2, dl)

    # The download function should never be called.
    assert not dl.download.called


async def test_fetch_missing_robots(asyncio_loop, nursery):
    ''' If robots file has a 404 error, then it is treated as a permissive
    robots . '''
    async def download404(request):
        ''' A mock download function that returns a fixed response. '''
        assert str(request.url) == 'https://www.example/robots.txt'
        response = DownloadResponse.from_request(request)
        response.content_type = 'text/plain'
        response.status_code = 404
        return response

    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download404)
    rtm = RobotsTxtManager(db_pool)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy, dl)
    assert await rtm.is_allowed('https://www.example/foo/', policy, dl)
    assert await rtm.is_allowed('https://www.example/bar/', policy, dl)


async def test_fetch_concurrent(asyncio_loop, nursery, autojump_clock):
    ''' If two tasks request the same robots.txt at the same time, one blocks
    while the other requests the file over the network.. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()
    policy = make_policy(usage='OBEY', user_agent='TestAgent1')

    async def request1():
        assert await rtm.is_allowed('https://www.example/index', policy, dl)

    async def request2():
        assert not await rtm.is_allowed('https://www.example/bar/', policy, dl)

    async with trio.open_nursery() as inner:
        inner.start_soon(request1)
        inner.start_soon(request2)

    assert dl.download.call_count == 1


async def test_fetch_max_age(asyncio_loop, nursery, autojump_clock):
    ''' Set max age to 0 seconds and then request a robots.txt twice. It should
    be fetched from network twice. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool, max_age=0)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/foo/', policy, dl)
    assert not await rtm.is_allowed('https://www.example/bar/', policy, dl)
    assert dl.download.call_count == 2


async def test_fetch_from_db(asyncio_loop, autojump_clock):
    ''' The robots is not in the memory cache but it is in the database. '''
    robots_doc = {
        'file': b'User-agent: *\n' \
                b'Disallow: /foo/\n' \
                b'\n' \
                b'User-agent: TestAgent1\n' \
                b'Disallow: /bar/\n',
        'updated_at': datetime.now(timezone.utc),
        'url': 'https://www.example/robots.txt',
    }
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool, max_age=0)
    rtm._get_robots_from_db = AsyncMock(return_value=robots_doc)
    rtm._save_robots_to_db = AsyncMock()

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy, dl)
    assert not dl.download.called


async def test_update_db(asyncio_loop, nursery, autojump_clock):
    ''' The robots in the DB has expired, so we fetch a new copy from the
    network and update the DB copy. '''
    robots_doc = {
        'file': b'User-agent: *\n' \
                b'Disallow: /foo/\n' \
                b'\n' \
                b'User-agent: TestAgent1\n' \
                b'Disallow: /bar/\n',
        'updated_at': datetime.now(timezone.utc) - timedelta(hours=1),
        'url': 'https://www.example/robots.txt',
    }
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool, max_age=5)
    rtm._get_robots_from_db = AsyncMock(return_value=robots_doc)
    rtm._save_robots_to_db = AsyncMock()

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy, dl)
    assert dl.download.call_count == 1


async def test_cache_eviction(asyncio_loop, nursery, autojump_clock):
    ''' Set the cache size to 2. '''
    db_pool = Mock()
    dl = Mock()
    dl.download = AsyncMock(side_effect=download)
    rtm = RobotsTxtManager(db_pool, max_cache=2)
    rtm._get_robots_from_db = AsyncMock()
    rtm._save_robots_to_db = AsyncMock()

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://test1.example/foo/', policy, dl)
    assert dl.download.call_count == 1
    assert await rtm.is_allowed('https://test1.example/foo/', policy, dl)
    assert dl.download.call_count == 1
    assert await rtm.is_allowed('https://test2.example/foo/', policy, dl)
    assert dl.download.call_count == 2
    assert await rtm.is_allowed('https://test3.example/foo/', policy, dl)
    assert dl.download.call_count == 3
    assert await rtm.is_allowed('https://test1.example/foo/', policy, dl)
    assert dl.download.call_count == 4
