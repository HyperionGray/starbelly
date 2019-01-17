'''
A lot of these tests mock up internal APIs in the robots manager, which isn't
great but is the most expedient way to get this working.
'''
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from rethinkdb import RethinkDB
import trio

from . import asyncio_loop
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


async def async_none(*args, **kwargs):
    ''' This helper is used as a side effect in mocked out methods. '''
    await trio.sleep(0)
    return None


async def async_robots(*args, **kwargs):
    ''' This helper is used as a side effect in mocked out methods. '''
    await trio.sleep(0)
    return {
        'file': b'User-agent: *\n' \
                b'Disallow: /foo/\n' \
                b'\n' \
                b'User-agent: TestAgent1\n' \
                b'Disallow: /bar/\n',
        'updated_at': datetime.now(timezone.utc),
        'url': 'https://www.example/robots.txt',
    }


async def test_fetch_robots(asyncio_loop, nursery):
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
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

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


async def test_fetch_robots_invert(asyncio_loop, nursery):
    ''' Do the opposite of what robots.txt says. '''
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
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy1 = make_policy(usage='INVERT', user_agent='TestAgent1')
    assert not await rtm.is_allowed('https://www.example/index.html', policy1)
    assert not await rtm.is_allowed('https://www.example/foo/', policy1)
    assert await rtm.is_allowed('https://www.example/bar/', policy1)

    policy2 = make_policy(usage='INVERT', user_agent='TestAgent2')
    assert not await rtm.is_allowed('https://www.example/index.html', policy2)
    assert await rtm.is_allowed('https://www.example/foo/', policy2)
    assert not await rtm.is_allowed('https://www.example/bar/', policy2)

    # The file should only be fetched one time, and then served from cache for
    # subsequent requests.
    assert serve_count == 1


async def test_fetch_robots_ignore(asyncio_loop, nursery):
    ''' Ignore what robots.txt says. Don't even fetch it. '''
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy1 = make_policy(usage='IGNORE', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy1)
    assert await rtm.is_allowed('https://www.example/foo/', policy1)
    assert await rtm.is_allowed('https://www.example/bar/', policy1)

    policy2 = make_policy(usage='IGNORE', user_agent='TestAgent2')
    assert await rtm.is_allowed('https://www.example/index.html', policy2)
    assert await rtm.is_allowed('https://www.example/foo/', policy2)
    assert await rtm.is_allowed('https://www.example/bar/', policy2)


async def test_fetch_missing_robots(asyncio_loop, nursery):
    ''' If robots file has a 404 error, then it is treated as a permissive
    robots . '''
    async def serve_robots():
        request = await request_recv.receive()
        assert str(request.url) == 'https://www.example/robots.txt'
        response = DownloadResponse.from_request(request)
        response.content_type: 'text/plain'
        response.status_code = 404
        await response_send.send(response)

    nursery.start_soon(serve_robots)
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy)
    assert await rtm.is_allowed('https://www.example/foo/', policy)
    assert await rtm.is_allowed('https://www.example/bar/', policy)


async def test_fetch_concurrent(asyncio_loop, nursery, autojump_clock):
    ''' If two tasks request the same robots.txt at the same time, one blocks
    while the other requests the file over the network.. '''
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
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none
    policy = make_policy(usage='OBEY', user_agent='TestAgent1')

    async def request1():
        assert await rtm.is_allowed('https://www.example/index.html', policy)

    async def request2():
        assert not await rtm.is_allowed('https://www.example/bar/', policy)

    async with trio.open_nursery() as inner:
        inner.start_soon(request1)
        inner.start_soon(request2)

    assert serve_count == 1


async def test_fetch_max_age(asyncio_loop, nursery, autojump_clock):
    ''' Set max age to 0 seconds and then request a robots.txt twice. It should
    be fetched from network twice. '''
    async def serve_robots():
        nonlocal serve_count
        while True:
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
    rtm = RobotsTxtManager(None, request_send, response_recv, max_age=0)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/foo/', policy)
    assert not await rtm.is_allowed('https://www.example/bar/', policy)
    assert serve_count == 2


async def test_fetch_from_db(asyncio_loop, autojump_clock):
    ''' The robots is not in the memory cache but it is in the database. '''
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    rtm = RobotsTxtManager(None, request_send, response_recv)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_robots
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy)


async def test_update_db(asyncio_loop, nursery, autojump_clock):
    ''' The robots in the DB has expired, so we fetch a new copy from the
    network and update the DB copy. '''
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
    rtm = RobotsTxtManager(None, request_send, response_recv, max_age=0)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_robots
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://www.example/index.html', policy)
    assert serve_count == 1


async def test_cache_eviction(asyncio_loop, nursery, autojump_clock):
    ''' Set the cache size to 2. '''
    async def serve_robots():
        nonlocal serve_count
        while True:
            request = await request_recv.receive()
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
    rtm = RobotsTxtManager(None, request_send, response_recv, max_cache=1)
    rtm._get_robots_from_db = Mock()
    rtm._get_robots_from_db.side_effect = async_none
    rtm._save_robots_to_db = Mock()
    rtm._save_robots_to_db.side_effect = async_none

    policy = make_policy(usage='OBEY', user_agent='TestAgent1')
    assert await rtm.is_allowed('https://test1.example/foo/', policy)
    assert serve_count == 1
    assert await rtm.is_allowed('https://test1.example/foo/', policy)
    assert serve_count == 1
    assert await rtm.is_allowed('https://test2.example/foo/', policy)
    assert serve_count == 2
    assert await rtm.is_allowed('https://test3.example/foo/', policy)
    assert serve_count == 3
    assert await rtm.is_allowed('https://test1.example/foo/', policy)
    assert serve_count == 4
