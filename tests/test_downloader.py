from datetime import datetime
from functools import partial
from unittest.mock import Mock

import aiohttp
import pytest
import trio
from yarl import URL

from . import asyncio_loop, AsyncMock
from starbelly.downloader import (
    Downloader,
    DownloadRequest,
    DownloadResponse,
)
from starbelly.policy import Policy


def make_request(url, method='GET', policy=None, form_data=None):
    ''' Make a request object for the given URL. '''
    job_id = '123e4567-e89b-12d3-a456-426655440001'
    return DownloadRequest(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        job_id=job_id,
        method=method,
        url=url,
        form_data=form_data,
        cost=1.0
    )


def make_stats():
    ''' Make an empty stats dictionary. '''
    return {
        'item_count': 0,
        'http_success_count': 0,
        'http_error_count': 0,
        'exception_count': 0,
        'http_status_counts': {},
    }


def make_policy(proxy=None):
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
            'max_duration': 3600,
            'max_items': 10_000,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': proxy or [],
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


def test_request():
    request = make_request('http://downloader.example/path1/path2?k2=v2&k1=v1')
    assert request.job_id == '123e4567-e89b-12d3-a456-426655440001'
    assert request.url.host == 'downloader.example'
    assert request.canonical_url == 'http://downloader.example/path1/' \
        'path2?k1=v1&k2=v2'


def test_response():
    request = make_request('http://downloader.example/path1/path2?k2=v2&k1=v1')
    resp = DownloadResponse.from_request(request)
    resp.start()
    assert resp.duration is None
    http_response = Mock(object())
    http_response.status = 200
    http_response.content_type = 'text/html'
    http_response.headers = {'User-agent': 'foo'}
    body = b'<html><head><title>test</title></head><body>test</body></html>'
    resp.set_response(http_response, body)
    assert resp.duration > 0
    assert resp.status_code == 200
    assert resp.content_type == 'text/html'
    assert resp.headers['User-agent'] == 'foo'
    assert resp.body.startswith(b'<html>')


def test_response_exception():
    request = make_request('http://downloader.example/path1/path2?k2=v2&k1=v1')
    resp = DownloadResponse.from_request(request)
    resp.start()
    assert resp.duration is None
    resp.set_exception('Sample exception')
    assert resp.duration > 0
    assert resp.exception == 'Sample exception'


async def test_http_get(nursery, asyncio_loop):
    # Create a server:
    async def handler(stream):
        request = await stream.receive_some(4096)
        assert request.startswith(b'GET /foo?user=john HTTP/1.1\r\n')
        assert request.endswith(b'\r\n\r\n')
        await stream.send_all(
                b'HTTP/1.1 200 OK\r\n'
                b'Content-type: text/html\r\n'
                b'\r\n'
                b'<html><head><title>Unit Test</title></head>\r\n'
                b'<body><h1>This is a unit test</h1></body></html>\r\n'
                b'\r\n'
            )
        await stream.aclose()
    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    http_server = await nursery.start(serve_tcp)
    addr, port = http_server[0].socket.getsockname()

    # Run the test:
    job_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    policy = make_policy()
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    semaphore = trio.Semaphore(1)
    rate_limiter_reset = Mock()
    rate_limiter_reset.send = AsyncMock()
    stats = make_stats()
    dl = Downloader(job_id, policy, response_send, request_recv, semaphore,
        rate_limiter_reset, stats)
    nursery.start_soon(dl.run)
    request = make_request('http://{}:{}/foo'.format(addr, port),
        form_data={'user': 'john'})
    await request_send.send(request)
    response = await response_recv.receive()
    nursery.cancel_scope.cancel()
    assert response.status_code == 200
    assert response.content_type == 'text/html'
    assert response.body.startswith(b'<html>')
    assert stats['item_count'] == 1
    assert stats['http_success_count'] == 1
    assert stats['http_status_counts'][200] == 1


@pytest.mark.skip('This test does not work; it just hangs...')
async def test_http_post(nursery):
    # Create a server:
    async def handler(stream):
        request = b''
        while True:
            request = await stream.receive_some(4096)
            if request.endswith(b'\r\n\r\n'):
                break
        assert request.startswith(b'POST /foo HTTP/1.1\r\n')
        await stream.send_all(
                b'HTTP/1.1 200 OK\r\n'
                b'Content-type: text/html\r\n'
                b'\r\n'
                b'<html><head><title>Unit Test</title></head>\r\n'
                b'<body><h1>This is a unit test</h1></body></html>\r\n'
                b'\r\n'
            )
        await stream.aclose()
    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    http_server = await nursery.start(serve_tcp)
    addr, port = http_server[0].socket.getsockname()

    # Run the test:
    job_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    policy = make_policy()
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    semaphore = trio.Semaphore(1)
    rate_limiter_reset = Mock()
    rate_limiter_reset.send = AsyncMock()
    stats = make_stats()
    dl = Downloader(job_id, policy, response_send, request_recv, semaphore,
        rate_limiter_reset, stats)
    nursery.start_soon(dl.run)
    request = make_request('http://{}:{}/foo'.format(addr, port), method='POST',
        form_data={'user': 'john'})
    await request_send.send(request)
    response = await response_recv.receive()
    nursery.cancel_scope.cancel()
    assert response.status_code == 200
    assert response.content_type == 'text/html'
    assert response.body.startswith(b'<html>')
    assert stats['item_count'] == 1
    assert stats['http_success_count'] == 1
    assert stats['http_status_counts'][200] == 1


async def test_http_proxy_get(asyncio_loop, nursery):
    # Create a server:
    async def handler(stream):
        request = await stream.receive_some(4096)
        assert request.startswith(b'GET http://test.example/foo HTTP/1.1')
        assert request.endswith(b'\r\n\r\n')
        await stream.send_all(
                b'HTTP/1.1 200 OK\n'
                b'Content-type: text/html\n'
                b'\n'
                b'<html><head><title>Unit Test</title></head>\n'
                b'<body><h1>This is a unit test</h1></body></html>\n'
            )
        await stream.aclose()
    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    http_proxy = await nursery.start(serve_tcp)
    addr, port = http_proxy[0].socket.getsockname()

    # Run the test:
    job_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    policy = make_policy(proxy=[{
        'proxy_url': 'http://{}:{}'.format(addr, port),
    }])
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    semaphore = trio.Semaphore(1)
    rate_limiter_reset = Mock()
    rate_limiter_reset.send = AsyncMock()
    stats = make_stats()
    dl = Downloader(job_id, policy, response_send, request_recv, semaphore,
        rate_limiter_reset, stats)
    nursery.start_soon(dl.run)
    request = make_request('http://test.example/foo', policy=policy)
    await request_send.send(request)
    response = await response_recv.receive()
    nursery.cancel_scope.cancel()
    assert response.status_code == 200
    assert response.content_type == 'text/html'
    assert response.body.startswith(b'<html>')
    assert stats['item_count'] == 1
    assert stats['http_success_count'] == 1
    assert stats['http_status_counts'][200] == 1


async def test_socks_proxy_get(asyncio_loop, nursery):
    # Create a server:
    async def handler(stream):
        # Negotiate SOCKS authentication (no auth)
        request = await stream.receive_some(4096)
        assert request.startswith(b'\x05')
        await stream.send_all(b'\x05\x00')
        # Negotiate SOCKS command.
        request = await stream.receive_some(4096)
        assert request == b'\x05\x01\x00\x01\x7f\x00\x00\x01\x00\x50'
        await stream.send_all(b'\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x50')
        # Get HTTP request and send response.
        request = await stream.receive_some(4096)
        assert request.startswith(b'GET /foo HTTP/1.1')
        assert request.endswith(b'\r\n\r\n')
        await stream.send_all(
                b'HTTP/1.1 200 OK\r\n'
                b'Content-type: text/html\r\n'
                b'\r\n'
                b'<html><head><title>Unit Test</title></head>\r\n'
                b'<body><h1>This is a unit test</h1></body></html>\r\n'
                b'\r\n'
            )
        await stream.aclose()
    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    socks_proxy = await nursery.start(serve_tcp)
    addr, port = socks_proxy[0].socket.getsockname()

    # Run the test:
    job_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    policy = make_policy(proxy=[{
        'proxy_url': 'socks5://{}:{}'.format(addr, port),
    }])
    request_send, request_recv = trio.open_memory_channel(0)
    response_send, response_recv = trio.open_memory_channel(0)
    semaphore = trio.Semaphore(1)
    rate_limiter_reset = Mock()
    rate_limiter_reset.send = AsyncMock()
    stats = make_stats()
    dl = Downloader(job_id, policy, response_send, request_recv, semaphore,
        rate_limiter_reset, stats)
    nursery.start_soon(dl.run)
    request = make_request('http://127.0.0.1/foo', policy=policy)
    await request_send.send(request)
    response = await response_recv.receive()
    nursery.cancel_scope.cancel()
    assert response.status_code == 200
    assert response.content_type == 'text/html'
    assert response.body.startswith(b'<html>')
    assert stats['item_count'] == 1
    assert stats['http_success_count'] == 1
    assert stats['http_status_counts'][200] == 1
