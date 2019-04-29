from datetime import datetime, timezone
import logging
from unittest.mock import Mock

import pytest
import trio
from trio_websocket import ConnectionClosed, open_websocket

from . import AsyncMock, fail_after
from starbelly.job import RunState
from starbelly.policy import Policy
from starbelly.rate_limiter import GLOBAL_RATE_LIMIT_TOKEN
from starbelly.schedule import Schedule
from starbelly.server import InvalidRequestException, Server
from starbelly.server.subscription import (
    subscribe_crawl_sync,
    subscribe_job_status,
    subscribe_resource_monitor,
    subscribe_task_monitor,
    unsubscribe,
)
from starbelly.starbelly_pb2 import (
    CaptchaSolverAntigateCharacters,
    JobRunState as PbRunState,
    Request,
    RequestSubscribeJobStatus,
    RequestSubscribeJobSync,
    RequestSubscribeResourceMonitor,
    RequestSubscribeTaskMonitor,
    RequestUnsubscribe,
    Response,
    ServerMessage,
)


logger = logging.getLogger(__name__)
HOST = '127.0.0.1'


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
def server_db():
    return Mock()


@pytest.fixture
def stats_tracker():
    return Mock()


@pytest.fixture
def subscription_db():
    return Mock()


@pytest.fixture
async def server(nursery, server_db, subscription_db, crawl_manager,
        rate_limiter, resource_monitor, stats_tracker, scheduler):
    server = Server('127.0.0.1', 0, server_db, subscription_db, crawl_manager,
        rate_limiter, resource_monitor, stats_tracker, scheduler)
    await nursery.start(server.run)
    yield server


@pytest.fixture
async def client(server):
    async with open_websocket(HOST, server.port, '/', use_ssl=False) as ws:
        yield ws


def new_request(request_id):
    ''' Helper to make Request objects. '''
    request = Request()
    request.request_id = request_id
    return request


async def send_test_command(client, command):
    ''' A little helper to reduce some boilerplate. '''
    await client.send_message(command.SerializeToString())
    message = await client.get_message()
    return ServerMessage.FromString(message).response


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


@fail_after(3)
async def test_get_list_captcha(client, server_db):
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
    server_db.get_captcha_solver = AsyncMock(return_value=captcha_doc)
    server_db.list_captcha_solvers = AsyncMock(return_value=(1, [captcha_doc]))

    # Get 1 captcha
    command1 = new_request(1)
    command1.get_captcha_solver.solver_id = b'\xaa' * 16
    response1 = await send_test_command(client, command1)
    assert response1.request_id == 1
    assert response1.solver.solver_id == b'\xaa' * 16
    assert response1.solver.name == 'Test CAPTCHA Solver'
    assert response1.solver.antigate.service_url == 'https://captcha.example'

    # List 1 captcha
    command2 = new_request(2)
    command2.list_captcha_solvers.page.limit = 10
    command2.list_captcha_solvers.page.offset = 0
    response2 = await send_test_command(client, command2)
    assert response2.request_id == 2
    assert response2.list_captcha_solvers.total == 1
    assert len(response2.list_captcha_solvers.solvers) == 1


@fail_after(3)
async def test_set_delete_captcha(client, server_db):
    # Set 1 captcha:
    captcha_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    server_db.delete_captcha_solver = AsyncMock()
    server_db.set_captcha_solver = AsyncMock(return_value=captcha_id)

    # Set one captcha
    command1 = new_request(1)
    solver = command1.set_captcha_solver.solver
    solver.name = 'Test CAPTCHA Solver'
    solver.antigate.service_url = 'https://captcha.example'
    solver.antigate.api_key = 'FAKE-API-KEY'
    solver.antigate.require_phrase = False
    solver.antigate.case_sensitive = True
    solver.antigate.characters = CaptchaSolverAntigateCharacters.Value(
        'ALPHANUMERIC')
    solver.antigate.require_math = False
    solver.antigate.min_length = 5
    solver.antigate.max_length = 5
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert server_db.set_captcha_solver.call_args[0]['name'] == \
        'Test CAPTCHA Solver'

    # Delete one captcha
    command2 = new_request(2)
    command2.delete_captcha_solver.solver_id = b'\xaa' * 16
    response2 = await send_test_command(client, command2)
    assert response2.is_success
    assert server_db.delete_captcha_solver.call_args[0] == captcha_id


@fail_after(3)
async def test_get_list_domain_login(client, server_db):
    login_doc = {
        'domain': 'login.example',
        'login_url': 'https://login.example/login.aspx',
        'login_test': None,
        'users': [
            {'username': 'john.doe', 'password': 'fake', 'working': True},
            {'username': 'jane.doe', 'password': 'fake', 'working': True},
        ],
    }

    # Credentials not found
    server_db.get_domain_login = AsyncMock()
    command1 = new_request(1)
    command1.get_domain_login.domain = 'bogus.example'
    response1 = await send_test_command(client, command1)
    assert not response1.is_success

    # Get a domain login
    server_db.get_domain_login = AsyncMock(return_value=login_doc)
    command2 = new_request(2)
    command2.get_domain_login.domain = 'login.example'
    response2 = await send_test_command(client, command2)
    login = response2.domain_login
    assert login.domain == 'login.example'
    assert login.login_url == 'https://login.example/login.aspx'
    assert login.users[0].username == 'john.doe'

    # List domain logins
    server_db.list_domain_logins = AsyncMock(return_value=(1,[login_doc]))
    command3 = new_request(3)
    command3.list_domain_logins.page.limit = 10
    command3.list_domain_logins.page.offset = 0
    response3 = await send_test_command(client, command3)
    logins = response3.list_domain_logins
    assert logins.total == 1
    assert logins.logins[0].domain == 'login.example'
    assert logins.logins[0].login_url == 'https://login.example/login.aspx'
    assert logins.logins[0].users[0].username == 'john.doe'


@fail_after(3)
async def test_set_delete_domain_login(client, server_db):
    server_db.get_domain_login = AsyncMock()
    server_db.delete_domain_login = AsyncMock()
    server_db.set_domain_login = AsyncMock()

    # Create domain login
    command1 = new_request(1)
    login = command1.set_domain_login.login
    login.domain = 'login.example'
    login.login_url = 'https://login.example/login.aspx'
    user = login.users.add()
    user.username = 'john.doe'
    user.password = 'fake'
    user.working = True
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert server_db.set_domain_login.call_args[0] == {
        'domain': 'login.example',
        'login_url': 'https://login.example/login.aspx',
        'login_test': None,
        'users': [
            {'username': 'john.doe', 'password': 'fake', 'working': True},
        ]
    }

    # Delete domain login
    command2 = new_request(2)
    command2.delete_domain_login.domain = 'login.example'
    response2 = await send_test_command(client, command2)
    assert response2.is_success
    assert server_db.delete_domain_login.call_args[0] == 'login.example'


@fail_after(3)
async def test_policy(client, server_db):
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
    server_db.delete_policy = AsyncMock()
    server_db.get_policy = AsyncMock(return_value=policy_doc)
    server_db.list_policies = AsyncMock(return_value=(1, [policy_doc]))
    server_db.set_policy = AsyncMock(return_value=policy_id)

    # Get a policy
    command1 = new_request(1)
    command1.get_policy.policy_id = b'\xaa' * 16
    response1 = await send_test_command(client, command1)
    assert server_db.get_policy.call_args[0] == policy_id
    assert response1.policy.name == 'Test Policy'

    # List policies
    command2 = new_request(2)
    command2.list_policies.page.limit = 10
    command2.list_policies.page.offset = 0
    response2 = await send_test_command(client, command2)
    assert response2.list_policies.total == 1
    assert response2.list_policies.policies[0].name == 'Test Policy'

    # Set policy
    command3 = new_request(3)
    policy2_doc = policy_doc.copy()
    del policy2_doc['id']
    Policy.convert_doc_to_pb(policy2_doc, command3.set_policy.policy)
    response3 = await send_test_command(client, command3)
    assert response3.new_policy.policy_id == b'\xaa' * 16

    # Delete policy
    command4 = new_request(4)
    command4.delete_policy.policy_id = b'\xaa' * 16
    response4 = await send_test_command(client, command4)
    assert response4.is_success
    assert server_db.delete_policy.call_args[0] == policy_id


@fail_after(3)
async def test_list_rate_limits(client, server_db):
    token = b'\xaa' * 16
    rate_limit = {
        'name': 'domain:rate-limit.example',
        'token': token,
        'delay': 1.5,
    }
    server_db.list_rate_limits = AsyncMock(return_value=(1, [rate_limit]))

    command1 = new_request(1)
    command1.list_rate_limits.page.limit = 10
    command1.list_rate_limits.page.offset = 0
    response1 = await send_test_command(client, command1)
    rate_limits = response1.list_rate_limits
    assert rate_limits.total == 1
    assert rate_limits.rate_limits[0].name == 'domain:rate-limit.example'
    assert rate_limits.rate_limits[0].token == token
    assert rate_limits.rate_limits[0].delay == 1.5
    assert rate_limits.rate_limits[0].domain == 'rate-limit.example'


@fail_after(3)
async def test_set_rate_limit(client, rate_limiter, server_db):
    server_db.set_rate_limit = AsyncMock()
    token = b'\xc5\xd3\xc5\xda\xdby\xab\xf4\x19~\x8f\xde\xc3\xcd\xfer'

    # Set a rate limit on a domain
    command1 = new_request(1)
    command1.set_rate_limit.domain = 'rate-limit.example'
    command1.set_rate_limit.delay = 1.5
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert server_db.set_rate_limit.call_args[0] == 'domain:rate-limit.example'
    assert server_db.set_rate_limit.call_args[1] == token
    assert server_db.set_rate_limit.call_args[2] == 1.5
    assert rate_limiter.set_rate_limit.called

    # Delete a rate limit on a domain
    command2 = new_request(2)
    command2.set_rate_limit.domain = 'rate-limit.example'
    response2 = await send_test_command(client, command2)
    assert response2.is_success
    assert server_db.set_rate_limit.call_args[0] == 'domain:rate-limit.example'
    assert server_db.set_rate_limit.call_args[1] == token
    assert server_db.set_rate_limit.call_args[2] == None
    assert rate_limiter.delete_rate_limit.called

    # Set the global rate limit
    command3 = new_request(3)
    command3.set_rate_limit.delay = 1.5
    response3 = await send_test_command(client, command3)
    assert response3.is_success
    assert server_db.set_rate_limit.call_args[0] == 'Global Rate Limit'
    assert server_db.set_rate_limit.call_args[1] == GLOBAL_RATE_LIMIT_TOKEN
    assert server_db.set_rate_limit.call_args[2] == 1.5
    assert rate_limiter.set_rate_limit.called


@fail_after(3)
async def test_schedule(client, scheduler, server_db):
    schedule_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    schedule_id_bytes = b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa' \
                        b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa'
    dt = datetime(2019, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    schedule_doc = {
        'id': schedule_id,
        'schedule_name': 'Test Schedule',
        'enabled': True,
        'created_at': dt,
        'updated_at': dt,
        'time_unit': 'DAYS',
        'num_units': 7,
        'timing': 'REGULAR_INTERVAL',
        'job_name': 'Test Job #{COUNT}',
        'job_count': 1,
        'seeds': ['https://schedule.example'],
        'tags': ['schedule1', 'schedule2'],
        'policy_id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    }
    server_db.delete_schedule = AsyncMock()
    server_db.get_schedule = AsyncMock(return_value=schedule_doc)
    server_db.list_schedules = AsyncMock(return_value=(1, [schedule_doc]))
    server_db.list_schedule_jobs = AsyncMock(return_value=list())
    server_db.set_schedule = AsyncMock(return_value=schedule_id)

    # Get a schedule
    command1 = new_request(1)
    command1.get_schedule.schedule_id = b'\xaa' * 16
    response1 = await send_test_command(client, command1)
    assert server_db.get_schedule.call_args[0] == schedule_id
    assert response1.schedule.schedule_name == 'Test Schedule'

    # List schedules
    command2 = new_request(2)
    command2.list_schedules.page.limit = 10
    command2.list_schedules.page.offset = 0
    response2 = await send_test_command(client, command2)
    list_ = response2.list_schedules
    assert list_.total == 1
    assert list_.schedules[0].schedule_name == 'Test Schedule'

    # Set schedule
    command3 = new_request(3)
    schedule3_doc = schedule_doc.copy()
    schedule3_doc['id'] = None
    Schedule.from_doc(schedule3_doc).to_pb(command3.set_schedule.schedule)
    response3 = await send_test_command(client, command3)
    assert response3.new_schedule.schedule_id == schedule_id_bytes
    assert server_db.set_schedule.called
    assert scheduler.add_schedule.called

    # Delete policy
    command4 = new_request(4)
    command4.delete_schedule.schedule_id = b'\xaa' * 16
    response4 = await send_test_command(client, command4)
    assert response4.is_success
    assert server_db.delete_schedule.call_args[0] == schedule_id
    assert scheduler.remove_schedule.called


@fail_after(3)
async def test_subscription():
    # Note that this test doesn't use a websocket connection, it runs the
    # server handlers directly so that we can mock out the subscription manager.
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    subscription_manager = Mock()
    subscription_manager.subscribe_crawl_sync.return_value = 1
    subscription_manager.subscribe_job_status.return_value = 2
    subscription_manager.subscribe_resource_monitor.return_value = 3
    subscription_manager.subscribe_task_monitor.return_value = 4
    stats_tracker = Mock()
    resource_monitor = Mock()

    # Subscribe to job sync
    command1 = RequestSubscribeJobSync()
    command1.job_id = b'\xaa' * 16
    response1 = Response()
    crawl_manager = Mock()
    await subscribe_crawl_sync(command1, crawl_manager, response1,
        subscription_manager)
    assert response1.new_subscription.subscription_id == 1

    # Subscribe to job status
    command2 = RequestSubscribeJobStatus()
    command2.min_interval = 1
    response2 = Response()
    await subscribe_job_status(command2, response2, subscription_manager,
        stats_tracker)
    assert response2.new_subscription.subscription_id == 2

    # Subscribe to resource monitor
    command3 = RequestSubscribeResourceMonitor()
    command3.history = 10
    response3 = Response()
    await subscribe_resource_monitor(command3, response3, resource_monitor,
        subscription_manager)
    assert response3.new_subscription.subscription_id == 3

    # Subscribe to task monitor
    command4 = RequestSubscribeTaskMonitor()
    command4.period = 2.0
    response4 = Response()
    await subscribe_task_monitor(command4, response4, subscription_manager)
    assert response4.new_subscription.subscription_id == 4

    # Unsubscrive to task monitor
    command5 = RequestUnsubscribe()
    command5.subscription_id = 5
    await unsubscribe(command5, subscription_manager)
    assert subscription_manager.cancel_subscription.called


@fail_after(3)
async def test_delete_job(client, server_db):
    server_db.delete_job = AsyncMock()
    command1 = new_request(1)
    command1.delete_job.job_id = b'\xaa' * 16
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert server_db.delete_job.call_args[0] == \
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@fail_after(3)
async def test_get_job(client, server_db):
    dt = datetime(2018, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    job = {
        'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'name': 'Test Job',
        'seeds': ['https://seed1.example', 'https://seed2.example'],
        'tags': [],
        'run_state': RunState.RUNNING,
        'started_at': dt,
        'completed_at': None,
        'duration': None,
        'item_count': 0,
        'http_success_count': 0,
        'http_error_count': 0,
        'exception_count': 0,
        'http_status_counts': {},
        'schedule_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'policy': {
            'name': 'Test Policy',
            'created_at': dt,
            'updated_at': dt,
            'authentication': {
                'enabled': False,
            },
            'captcha_solver_id': None,
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
    }
    server_db.get_job = AsyncMock(return_value=job)
    command1 = new_request(1)
    command1.get_job.job_id = b'\xaa' * 16
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert response1.job.job_id == b'\xaa' * 16
    assert response1.job.name == 'Test Job'
    assert response1.job.policy.name == 'Test Policy'


@fail_after(3)
async def test_list_jobs(client, server_db):
    dt = datetime(2018, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    job = {
        'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'name': 'Test Job',
        'seeds': ['https://seed1.example', 'https://seed2.example'],
        'tags': [],
        'run_state': RunState.RUNNING,
        'started_at': dt,
        'completed_at': None,
        'duration': None,
        'item_count': 0,
        'http_success_count': 0,
        'http_error_count': 0,
        'exception_count': 0,
        'http_status_counts': {},
        'schedule_id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    }
    server_db.list_jobs = AsyncMock(return_value=(1,[job]))
    command1 = new_request(1)
    command1.list_jobs.page.limit = 10
    command1.list_jobs.page.offset = 0
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert response1.list_jobs.total == 1
    job = response1.list_jobs.jobs[0]
    assert job.job_id == b'\xaa' * 16
    assert job.name == 'Test Job'


@fail_after(3)
async def test_set_jobs(client, crawl_manager, server_db):
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    crawl_manager.start_job = AsyncMock(return_value=job_id)
    crawl_manager.cancel_job = AsyncMock()
    crawl_manager.pause_job = AsyncMock()
    crawl_manager.resume_job = AsyncMock()

    # Start a new job
    command1 = new_request(1)
    command1.set_job.name = 'New Job'
    command1.set_job.policy_id = b'\xbb' * 16
    command1.set_job.seeds.append('https://seed.example')
    command1.set_job.tags.extend(['tag1', 'tag2'])
    response1 = await send_test_command(client, command1)
    assert response1.is_success
    assert crawl_manager.start_job.call_args[0] == 'New Job'
    assert crawl_manager.start_job.call_args[1] == ['https://seed.example']
    assert crawl_manager.start_job.call_args[2] == ['tag1', 'tag2']
    assert crawl_manager.start_job.call_args[3] == \
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'

    # Cancel a job
    command2 = new_request(2)
    command2.set_job.job_id = b'\xaa' * 16
    command2.set_job.run_state = PbRunState.Value('CANCELLED')
    response2 = await send_test_command(client, command2)
    assert response2.is_success
    assert crawl_manager.cancel_job.call_args[0] == \
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

    # Pause a job
    command3 = new_request(3)
    command3.set_job.job_id = b'\xaa' * 16
    command3.set_job.run_state = PbRunState.Value('PAUSED')
    response3 = await send_test_command(client, command3)
    assert response3.is_success
    assert crawl_manager.pause_job.call_args[0] == \
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

    # Resume a job
    command4 = new_request(4)
    command4.set_job.job_id = b'\xaa' * 16
    command4.set_job.run_state = PbRunState.Value('RUNNING')
    response4 = await send_test_command(client, command4)
    assert response4.is_success
    assert crawl_manager.resume_job.call_args[0] == \
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

    # Invalid run state:
    command5 = new_request(5)
    command5.set_job.job_id = b'\xaa' * 16
    command5.set_job.run_state = PbRunState.Value('PENDING')
    response5 = await send_test_command(client, command5)
    assert not response5.is_success
