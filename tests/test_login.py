from base64 import b64decode
from datetime import datetime, timezone
from functools import partial

from aiohttp import CookieJar
import trio
from yarl import URL

from . import asyncio_loop
from starbelly.captcha import CaptchaSolver
from starbelly.downloader import Downloader, DownloadResponse
from starbelly.login import get_login_form, solve_captcha_asyncio
from starbelly.policy import Policy


async def test_login_form_extraction(asyncio_loop, mocker):
    ''' Test fetching login page, form extraction, and login image. The CAPTCHA
    solver is mocked out.

    Note that the asyncio_loop fixture isn't used directly, but it creates a
    global asyncio loop that this test requires. '''
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
            'service_url': 'https://captcha.example/',
            'api_key': None,
            'require_phrase': False,
            'case_sensitive': True,
            'characters': True,
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
    policy = Policy(policy_doc, '1.0.0', ['https://www.example'])
    cookie_jar = CookieJar()
    form_response_body = b'<html><head><title><test></title></head><body>' \
        b'<form action="/login" method="POST">' \
        b'<input type="text" name="username">' \
        b'<input type="password" name="password">' \
        b'<img src="https://www.example/get_captcha" alt="CAPTCHA">' \
        b'<input type="text" name="captcha">' \
        b'<input type="submit" value="Log In"></body></html>'
    form_response = DownloadResponse(
        cost=0.0,
        url='https://www.example',
        canonical_url='https://www.example',
        content_type='text/html',
        body=form_response_body,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status_code=200,
        headers={'Server': 'Fake Server 1.0', 'Content-type': 'text/html'},
        should_save=True
    )
    img_response_body = b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
        'AAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==')
    img_response = DownloadResponse(
        cost=0.0,
        url='https://www.example/captcha',
        canonical_url='https://www.example/captcha',
        content_type='text/html',
        body=img_response_body,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        status_code=200,
        headers={'Server': 'Fake Server 1.0', 'Content-type': 'image/png'},
        should_save=True
    )
    async def download_img():
        return img_response
    async def solve():
        return 'ABCD1234'
    downloader = Downloader(None, None, trio.Semaphore(1))
    downloader.download = mocker.Mock()
    downloader.download.side_effect = [download_img()]
    solve_mock = mocker.patch('starbelly.login.solve_captcha_asyncio')
    solve_mock.side_effect = [solve()]

    # Now test the login extractor.
    with trio.fail_after(3):
        action, method, data = await get_login_form(policy, downloader,
            cookie_jar, form_response, 'testuser', 'testpass')

    solve_mock.assert_called()
    assert action == URL('https://www.example/login')
    assert method == 'POST'
    assert data['username'] == 'testuser'
    assert data['password'] == 'testpass'
    assert data['captcha'] == 'ABCD1234'


async def test_solve_login_captcha(asyncio_loop, mocker, nursery):
    ''' This test focuses on the private function _solve_captcha_asyncio. '''
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
        await stream.aclose()

    serve_tcp = partial(trio.serve_tcp, handler, port=0, host='127.0.0.1')
    http_server = await nursery.start(serve_tcp)
    addr, port = http_server[0].socket.getsockname()
    img_data = b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
        'AAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==')
    solver = CaptchaSolver({
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'type': 'example',
        'created_at': datetime(2019, 1, 26, 15, 30, 0, tzinfo=timezone.utc),
        'updated_at': datetime(2019, 1, 26, 15, 35, 0, tzinfo=timezone.utc),
        'name': 'Captcha #1',
        'service_url': 'http://{}:{}/'.format(addr, port),
        'api_key': 'ABCDEFGH',
        'require_phrase': False,
        'case_sensitive': True,
        'characters': 'ALPHANUMERIC',
        'require_math': False,
    })
    # Patch out asyncio sleep so that the test completes quickly.
    async def sleep():
        return
    sleep_mock = mocker.patch('asyncio.sleep')
    sleep_mock.side_effect = [sleep()]
    solution = await solve_captcha_asyncio(solver, img_data)
    assert solution == 'ABCD1234'

