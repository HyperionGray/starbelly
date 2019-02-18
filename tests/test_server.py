from datetime import datetime, timezone
import logging
from unittest.mock import Mock

import pytest
import trio
from trio_websocket import ConnectionClosed, open_websocket

from . import AsyncMock, fail_after
from starbelly.server import InvalidRequestException, Server
from starbelly.server.captcha import (
    delete_captcha_solver,
    get_captcha_solver,
    list_captcha_solvers,
    set_captcha_solver,
)
from starbelly.starbelly_pb2 import *


logger = logging.getLogger(__name__)
HOST = '127.0.0.1'


@pytest.fixture
async def client(server):
    async with open_websocket(HOST, server.port, '/', use_ssl=False) as ws:
        yield ws


@pytest.fixture
def crawl_manager():
    return Mock()


@pytest.fixture
def rate_limiter():
    return Mock()


@pytest.fixture
def resource_monitor():
    return Mock()


@pytest.fixture
def scheduler():
    return Mock()


@pytest.fixture
async def server(nursery, server_db, crawl_manager, rate_limiter,
        resource_monitor, scheduler):
    server = Server('127.0.0.1', 0, server_db, crawl_manager, rate_limiter,
        resource_monitor, scheduler)
    await nursery.start(server.run)
    yield server


@pytest.fixture
def server_db():
    return Mock()


@fail_after(3)
async def test_invalid_message(client):
    ''' A non-protobuf message should close the connection. '''
    await client.send_message(b'foo')
    with pytest.raises(ConnectionClosed):
        await client.get_message()


@fail_after(3)
async def test_profile(client):
    request = Request()
    request.request_id = 1
    request.performance_profile.duration = 0.1
    request.performance_profile.sort_by = 'calls'
    request.performance_profile.top_n = 5
    await client.send_message(request.SerializeToString())
    message_bytes = await client.get_message()
    message = ServerMessage.FromString(message_bytes)
    assert message.response.request_id == 1
    profile = message.response.performance_profile
    assert profile.total_calls > 1
    assert profile.total_time > 0.1
    assert len(profile.functions) == 5
    logger.info('%r', profile)


@fail_after(3)
async def test_get_list_captcha(client):
    dt = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    captcha_doc = {
        'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'name': 'Test CAPTCHA Solver',
        'type': 'antigate',
        'created_at': dt,
        'updated_at': dt,
        'service_url': 'https://captcha.example',
        'api_key': 'FAKE-API-KEY',
        'require_phrase': False,
        'case_sensitive': False,
        'characters': 'ALPHANUMERIC',
        'require_math': False,
        'min_length': 5,
        'max_length': 5,
    }

    # Cannot get captcha without ID
    command1 = RequestGetCaptchaSolver()
    response1 = Response()
    server_db = Mock()
    server_db.get_captcha_solver = AsyncMock(return_value=captcha_doc)
    server_db.list_captcha_solvers = AsyncMock(return_value=(1, [captcha_doc]))
    with pytest.raises(InvalidRequestException):
        await get_captcha_solver(command1, response1, server_db)

    command1 = RequestGetCaptchaSolver()
    response1 = Response()
    server_db = Mock()
    server_db.get_captcha_solver = AsyncMock(return_value=captcha_doc)
    server_db.list_captcha_solvers = AsyncMock(return_value=(1, [captcha_doc]))
    with pytest.raises(InvalidRequestException):
        await get_captcha_solver(command1, response1, server_db)

    # Get 1 captcha
    command2 = RequestGetCaptchaSolver()
    command2.solver_id = b'\xaa' * 16
    response2 = Response()
    await get_captcha_solver(command2, response2, server_db)
    assert response2.solver.solver_id == b'\xaa' * 16
    assert response2.solver.name == 'Test CAPTCHA Solver'
    assert response2.solver.antigate.service_url == 'https://captcha.example'

    # List 1 captcha
    command3 = RequestListCaptchaSolvers()
    command3.page.limit = 10
    command3.page.offset = 0
    response3 = Response()
    await list_captcha_solvers(command3, response3, server_db)
    assert response3.list_captcha_solvers.total == 1
    assert len(response3.list_captcha_solvers.solvers) == 1


@fail_after(3)
async def test_set_delete_captcha(client):
    # Set 1 captcha:
    captcha_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    dt = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    command1 = RequestSetCaptchaSolver()
    command1.solver.name = 'Test CAPTCHA Solver'
    command1.solver.antigate.service_url = 'https://captcha.example'
    command1.solver.antigate.api_key = 'FAKE-API-KEY'
    command1.solver.antigate.require_phrase = False
    command1.solver.antigate.case_sensitive = True
    command1.solver.antigate.characters = \
        CaptchaSolverAntigateCharacters.Value('ALPHANUMERIC')
    command1.solver.antigate.require_math = False
    command1.solver.antigate.min_length = 5
    command1.solver.antigate.max_length = 5

    response1 = Response()
    server_db = Mock()
    server_db.delete_captcha_solver = AsyncMock()
    server_db.set_captcha_solver = AsyncMock(return_value=captcha_id)
    await set_captcha_solver(command1, response1, server_db)
    assert server_db.set_captcha_solver.call_args[0]['name'] == \
        'Test CAPTCHA Solver'

    # Cannot delete captcha without ID:
    command2 = RequestDeleteCaptchaSolver()
    with pytest.raises(InvalidRequestException):
        await delete_captcha_solver(command2, server_db)

    # Delete one captcha
    command3 = RequestDeleteCaptchaSolver()
    command3.solver_id = b'\xaa' * 16
    await delete_captcha_solver(command3, server_db)
    assert server_db.delete_captcha_solver.call_args[0] == captcha_id
