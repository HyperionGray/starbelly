from datetime import datetime, timezone
import logging
from unittest.mock import Mock

import pytest
import trio
from trio_websocket import ConnectionClosed, open_websocket

from . import AsyncMock, fail_after
from starbelly.policy import Policy as PythonPolicy
from starbelly.server import InvalidRequestException, Server
from starbelly.server.captcha import (
    delete_captcha_solver,
    get_captcha_solver,
    list_captcha_solvers,
    set_captcha_solver,
)
from starbelly.server.login import (
    delete_domain_login,
    get_domain_login,
    list_domain_logins,
    set_domain_login,
)
from starbelly.server.policy import (
    delete_policy,
    get_policy,
    list_policies,
    set_policy,
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
async def test_get_list_captcha():
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
async def test_set_delete_captcha():
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


@fail_after(3)
async def test_get_list_domain_login():
    login_doc = {
        'domain': 'login.example',
        'login_url': 'https://login.example/login.aspx',
        'login_test': None,
        'users': [
            {'username': 'john.doe', 'password': 'fake', 'working': True},
            {'username': 'jane.doe', 'password': 'fake', 'working': True},
        ],
    }

    # A domain is required
    command1 = RequestGetDomainLogin()
    response1 = Response()
    server_db = Mock()
    with pytest.raises(InvalidRequestException):
        await get_domain_login(command1, response1, server_db)

    # Credentials not found
    command2 = RequestGetDomainLogin()
    command2.domain = 'bogus.example'
    response2 = Response()
    server_db.get_domain_login = AsyncMock()
    with pytest.raises(InvalidRequestException):
        await get_domain_login(command2, response2, server_db)

    # Get a domain login
    command3 = RequestGetDomainLogin()
    command3.domain = 'login.example'
    response3 = Response()
    server_db.get_domain_login = AsyncMock(return_value=login_doc)
    await get_domain_login(command3, response3, server_db)
    assert response3.domain_login.domain == 'login.example'
    assert response3.domain_login.login_url == 'https://login.example/login.aspx'
    assert response3.domain_login.users[0].username == 'john.doe'

    # List domain logins
    command4 = RequestListDomainLogins()
    command4.page.limit = 10
    command4.page.offset = 0
    response4 = Response()
    server_db.list_domain_logins = AsyncMock(return_value=(1,[login_doc]))
    login = await list_domain_logins(command4, response4, server_db)
    assert response4.list_domain_logins.total == 1
    assert response4.list_domain_logins.logins[0].domain == 'login.example'
    assert response4.list_domain_logins.logins[0].login_url == 'https://login.example/login.aspx'
    assert response4.list_domain_logins.logins[0].users[0].username == 'john.doe'


@fail_after(3)
async def test_set_delete_domain_login():
    server_db = Mock()
    server_db.get_domain_login = AsyncMock()
    server_db.delete_domain_login = AsyncMock()
    server_db.set_domain_login = AsyncMock()

    # Domain is required
    command1 = RequestSetDomainLogin()
    with pytest.raises(InvalidRequestException):
        await set_domain_login(command1, server_db)

    # Login URL is required
    command2 = RequestSetDomainLogin()
    command2.login.domain = 'login.example'
    with pytest.raises(InvalidRequestException):
        await set_domain_login(command2, server_db)

    # Create domain login
    command3 = RequestSetDomainLogin()
    command3.login.domain = 'login.example'
    command3.login.login_url = 'https://login.example/login.aspx'
    user = command3.login.users.add()
    user.username = 'john.doe'
    user.password = 'fake'
    user.working = True
    await set_domain_login(command3, server_db)
    assert server_db.set_domain_login.call_args[0] == {
        'domain': 'login.example',
        'login_url': 'https://login.example/login.aspx',
        'login_test': None,
        'users': [
            {'username': 'john.doe', 'password': 'fake', 'working': True},
        ]
    }

    # Delete domain login requires domain
    command4 = RequestDeleteDomainLogin()
    with pytest.raises(InvalidRequestException):
        await delete_domain_login(command4, server_db)

    # Delete domain login
    command5 = RequestDeleteDomainLogin()
    command5.domain = 'login.example'
    await delete_domain_login(command5, server_db)
    assert server_db.delete_domain_login.call_args[0] == 'login.example'


@fail_after(3)
async def test_get_list_set_policy():
    policy_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    created_at = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    policy_doc = {
        'id': policy_id,
        'name': 'Test Policy',
        'created_at': created_at,
        'updated_at': created_at,
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
        ],
    }
    server_db = Mock()
    server_db.get_policy = AsyncMock(return_value=policy_doc)
    server_db.list_policies = AsyncMock(return_value=(1, [policy_doc]))
    server_db.set_policy = AsyncMock(return_value=policy_id)

    # Policy ID is required
    command1 = RequestGetPolicy()
    response1 = Response()
    with pytest.raises(InvalidRequestException):
        await get_policy(command1, response1, server_db)

    # Get a policy
    command2 = RequestGetPolicy()
    command2.policy_id = b'\xaa' * 16
    response2 = Response()
    await get_policy(command2, response2, server_db)
    assert server_db.get_policy.call_args[0] == policy_id
    assert response2.policy.name == 'Test Policy'

    # List domain logins
    command3 = RequestListDomainLogins()
    command3.page.limit = 10
    command3.page.offset = 0
    response3 = Response()
    login = await list_policies(command3, response3, server_db)
    assert response3.list_policies.total == 1
    assert response3.list_policies.policies[0].name == 'Test Policy'

    # Set policy
    command4 = RequestSetPolicy()
    policy2_doc = policy_doc.copy()
    del policy2_doc['id']
    PythonPolicy.convert_doc_to_pb(policy2_doc, command4.policy)
    response4 = Response()
    await set_policy(command4, response4, server_db)
    assert response4.new_policy.policy_id == b'\xaa' * 16


@fail_after(3)
async def test_delete_policy():
    policy_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    server_db = Mock()
    server_db.delete_policy = AsyncMock()
    server_db.set_policy = AsyncMock(return_value=policy_id)

    # Delete policy requires policy id
    command1 = RequestDeletePolicy()
    with pytest.raises(InvalidRequestException):
        await delete_policy(command1, server_db)

    # Delete policy
    command2 = RequestDeletePolicy()
    command2.policy_id = b'\xaa' * 16
    await delete_policy(command2, server_db)
    assert server_db.delete_policy.call_args[0] == policy_id
