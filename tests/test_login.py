from base64 import b64decode
from datetime import datetime, timezone
from functools import partial
from unittest.mock import Mock

from aiohttp import CookieJar
import trio
from yarl import URL

from . import asyncio_loop, AsyncMock
from starbelly.captcha import CaptchaSolver
from starbelly.downloader import Downloader, DownloadResponse
from starbelly.login import LoginManager
from starbelly.policy import Policy


def make_policy(captcha_port=80):
    policy_doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': datetime(2019, 1, 28, 14, 26, 0, tzinfo=timezone.utc),
        'updated_at': datetime(2019, 1, 28, 14, 26, 0, tzinfo=timezone.utc),
        'authentication': {
            'enabled': False,
        },
        'captcha_solver': {
            'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f8',
            'name': 'Example CAPTCHA',
            'service_url': 'http://127.0.0.1:{}'.format(captcha_port),
            'api_key': None,
            'require_phrase': False,
            'case_sensitive': True,
            'characters': 'ALPHANUMERIC',
            'require_math': False,
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
    return Policy(policy_doc, '1.0.0', ['https://login.example'])


async def test_login_form():
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    login = {
        'domain': 'login.example',
        'login_url': 'https://login.example/index',
        'users': [{'username': 'john', 'password': 'fake'}]
    }
    db.get_login = AsyncMock(return_value=login)
    policy = make_policy()
    downloader = Mock()
    html1 = \
    b'''<html>
        <head><title>Login Test</title></head>
        <body>
            <form action="/login" method="POST">
            <input type="text" name="username">
            <input type="password" name="password">
            <input type="submit" value="Log In">
        </body>
        </html>'''
    response1 = DownloadResponse(
        frontier_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        cost=1.0,
        url='https://login.example',
        canonical_url='https://login.example',
        content_type='text/html',
        body=html1,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    response2 = DownloadResponse(
        frontier_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        cost=1.0,
        url='https://login.example',
        canonical_url='https://login.example',
        content_type='text/html',
        body=None,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    downloader.download = AsyncMock(return_values=(response1, response2))
    login_manager = LoginManager(job_id, db, policy, downloader)
    await login_manager.login('login.example')
    assert downloader.download.call_count == 2
    request = downloader.download.call_args[0]
    assert request.method == 'POST'
    assert str(request.url) == 'https://login.example/login'
    assert request.form_data['username'] == 'john'
    assert request.form_data['password'] == 'fake'


async def test_login_with_captcha(asyncio_loop, mocker, nursery):
    # Create a CAPTCHA server
    conn_count = 0
    async def handler(stream):
        nonlocal conn_count
        if conn_count == 0:
            request = await stream.receive_some(4096)
            assert request.startswith(b'POST /createTask HTTP/1.1\r\n')
            await stream.send_all(
                b'HTTP/1.1 200 OK\r\n'
                b'Content-type: application/json\r\n'
                b'\r\n'
                b'{"errorId": 0, "taskId": 28278116}\r\n'
                b'\r\n'
            )
        else:
            request = await stream.receive_some(4096)
            assert request.startswith(b'POST /getTaskResult HTTP/1.1\r\n')
            await stream.send_all(
                b'HTTP/1.1 200 OK\r\n'
                b'Content-type: application/json\r\n'
                b'\r\n'
                b'{"errorId": 0, "taskId": 28278116, "status": "ready",\r\n'
                b' "solution": {"text": "ABCD1234"}}\r\n'
                b'\r\n'
            )
        conn_count += 1
    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    http_server = await nursery.start(serve_tcp)
    addr, port = http_server[0].socket.getsockname()

    # Patch out asyncio sleep so that the test completes quickly.
    sleep_mock = mocker.patch('asyncio.sleep', new=AsyncMock())

    # Create test fixtures
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    login = {
        'domain': 'login.example',
        'login_url': 'https://login.example/index',
        'users': [{'username': 'john', 'password': 'fake'}]
    }
    db.get_login = AsyncMock(return_value=login)
    policy = make_policy(port)
    downloader = Mock()
    html1 = \
    b'''<html>
        <head><title>Login Test</title></head>
        <body>
            <form action="/login" method="POST">
            <input type="text" name="username">
            <input type="password" name="password">
            <img src="/get-captcha" alt="CAPTCHA">
            <input type="text" name="captcha">
            <input type="submit" value="Log In">
        </body>
        </html>'''
    response1 = DownloadResponse(
        frontier_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        cost=1.0,
        url='https://login.example/index',
        canonical_url='https://login.example/index',
        content_type='text/html',
        body=html1,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 1, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    img_data = b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
        'AAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==')
    response2 = DownloadResponse(
        frontier_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        cost=1.0,
        url='https://login.example/get-captcha',
        canonical_url='https://login.example/get-captcha',
        content_type='image/png',
        body=img_data,
        started_at=datetime(2019, 2, 1, 10, 2, 4, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 5, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    response3 = DownloadResponse(
        frontier_id='cccccccc-cccc-cccc-cccc-cccccccccccc',
        cost=1.0,
        url='https://login.example/login',
        canonical_url='https://login.example/login',
        content_type='text/plain',
        body=b'200 OK',
        started_at=datetime(2019, 2, 1, 10, 2, 2, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 3, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    downloader.download = AsyncMock(return_values=(response1, response2,
        response3))

    # Run the test
    login_manager = LoginManager(job_id, db, policy, downloader)
    await login_manager.login('login.example')
    assert downloader.download.call_count == 3
    request = downloader.download.call_args[0]
    assert request.method == 'POST'
    assert str(request.url) == 'https://login.example/login'
    assert request.form_data['username'] == 'john'
    assert request.form_data['password'] == 'fake'
    assert request.form_data['captcha'] == 'ABCD1234'
