from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import protobuf.shared_pb2
import pytest

from starbelly.captcha import CaptchaSolver
from starbelly.policy import (
    Policy,
    PolicyAuthentication,
    PolicyLimits,
    PolicyMimeTypeRules,
    PolicyProxyRules,
    PolicyRobotsTxt,
    PolicyValidationError,
    PolicyUrlNormalization,
    PolicyUrlRules,
    PolicyUserAgents,
)


ACTION_ENUM = protobuf.shared_pb2.PolicyUrlRule.Action
MATCH_ENUM = protobuf.shared_pb2.PatternMatch
USAGE_ENUM = protobuf.shared_pb2.PolicyRobotsTxt.Usage


def test_convert_policy_doc_to_pb():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': updated_at,
        'authentication': {'enabled': True},
        'limits': {
            'max_cost': 10,
            'max_duration': 3600,
            'max_items': 10_000,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234',
             'pattern': r'\.onion',
             'match': 'MATCHES'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    pb = protobuf.shared_pb2.Policy()
    Policy.convert_doc_to_pb(doc, pb)
    assert pb.policy_id == b'\x01\xb6\x0e\xeb*\xc9OA\x9b\x0cG\xdc\xbc\xf67\xf7'
    assert pb.name == 'Test'
    assert pb.created_at == created_at.isoformat()
    assert pb.updated_at == updated_at.isoformat()

    # Authentication
    assert pb.authentication.enabled

    # Limits
    assert pb.limits.max_cost == 10

    # MIME type rules
    assert len(pb.mime_type_rules) == 2
    assert pb.mime_type_rules[0].match == MATCH_ENUM.Value('MATCHES')
    assert pb.mime_type_rules[0].pattern, '^text/'
    assert     pb.mime_type_rules[0].save
    assert not pb.mime_type_rules[1].save

    # Proxy rules
    assert len(pb.proxy_rules) == 1
    assert pb.proxy_rules[0].proxy_url == 'socks5://localhost:1234'

    # Robots.txt
    assert pb.robots_txt.usage == USAGE_ENUM.Value('IGNORE')

    # URL normalization
    assert pb.url_normalization.enabled
    assert pb.url_normalization.strip_parameters == ['PHPSESSID']

    # URL rules
    assert len(pb.url_rules) == 2
    assert pb.url_rules[0].action == ACTION_ENUM.Value('ADD')
    assert pb.url_rules[0].amount == 1
    assert pb.url_rules[0].match == MATCH_ENUM.Value('MATCHES')
    assert pb.url_rules[0].pattern == '^https?://({SEED_DOMAINS})/'
    assert pb.url_rules[1].action == ACTION_ENUM.Value('MULTIPLY')
    assert pb.url_rules[1].amount == 0

    # User agents
    assert len(pb.user_agents) == 1
    assert pb.user_agents[0].name == 'Test User Agent'

def test_convert_policy_doc_to_pb_captcha():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': updated_at,
        'captcha_solver_id': 'e27223d3-85ef-4e89-8fc8-dbcf8df0ce97',
        'authentication': {'enabled': True},
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    pb = protobuf.shared_pb2.Policy()
    Policy.convert_doc_to_pb(doc, pb)
    assert pb.captcha_solver_id == \
        b'\xe2\x72\x23\xd3\x85\xef\x4e\x89\x8f\xc8\xdb\xcf\x8d\xf0\xce\x97'


def test_convert_policy_pb_to_doc():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    pb = protobuf.shared_pb2.Policy()
    pb.policy_id = \
        b'\x01\xb6\x0e\xeb*\xc9OA\x9b\x0cG\xdc\xbc\xf67\xf7'
    pb.name = 'Test'
    pb.created_at = created_at.isoformat()
    pb.updated_at = updated_at.isoformat()

    # Authentication
    pb.authentication.enabled = True

    # Limits
    pb.limits.max_cost = 10
    pb.limits.max_duration = 3600
    pb.limits.max_items = 10_000

    # MIME type rules
    mime1 = pb.mime_type_rules.add()
    mime1.match = MATCH_ENUM.Value('MATCHES')
    mime1.pattern = '^text/'
    mime1.save = True
    mime2 = pb.mime_type_rules.add()
    mime2.save = False

    # Proxy rules
    proxy1 = pb.proxy_rules.add()
    proxy1.proxy_url = 'socks5://localhost:1234'
    proxy1.pattern = r'\.onion'
    proxy1.match = MATCH_ENUM.Value('MATCHES')

    # Robots.txt
    pb.robots_txt.usage = USAGE_ENUM.Value('IGNORE')

    # URL normalization
    pb.url_normalization.enabled = True
    pb.url_normalization.strip_parameters.append('PHPSESSID')

    # URL rules
    url1 = pb.url_rules.add()
    url1.action = ACTION_ENUM.Value('ADD')
    url1.amount = 1
    url1.match = MATCH_ENUM.Value('MATCHES')
    url1.pattern = '^https?://({SEED_DOMAINS})/'
    url2 = pb.url_rules.add()
    url2.action = ACTION_ENUM.Value('MULTIPLY')
    url2.amount = 0

    # User agents
    agent1 = pb.user_agents.add()
    agent1.name = 'Test User Agent'

    doc = Policy.convert_pb_to_doc(pb)
    assert doc['id'] == '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7'
    assert doc['name'] == 'Test'
    assert doc['created_at'] == created_at
    assert doc['updated_at'] == updated_at

    # Authentication
    assert doc['authentication']['enabled']

    # Limits
    assert doc['limits']['max_cost'] == 10

    # MIME type rules
    assert len(doc['mime_type_rules']) == 2
    mime1 = doc['mime_type_rules'][0]
    mime2 = doc['mime_type_rules'][1]
    assert mime1['match'] == 'MATCHES'
    assert mime1['pattern'] == '^text/'
    assert     mime1['save']
    assert not mime2['save']

    # Proxy rules
    assert len(doc['proxy_rules']) == 1
    proxy1 = doc['proxy_rules'][0]
    assert proxy1['proxy_url'] == 'socks5://localhost:1234'

    # Robots.txt
    assert doc['robots_txt']['usage'] == 'IGNORE'

    # URL normalization
    assert doc['url_normalization']['enabled']
    assert doc['url_normalization']['strip_parameters'] == ['PHPSESSID']

    # URL rules
    assert len(doc['url_rules']) == 2
    url1 = doc['url_rules'][0]
    url2 = doc['url_rules'][1]
    assert url1['action'] == 'ADD'
    assert url1['amount'] == 1
    assert url1['match'] == 'MATCHES'
    assert url1['pattern'] == '^https?://({SEED_DOMAINS})/'
    assert url2['action'] == 'MULTIPLY'
    assert url2['amount'] == 0

    # User agents
    assert len(doc['user_agents']) == 1
    agent1 = doc['user_agents'][0]
    assert agent1['name'] == 'Test User Agent'


def test_convert_policy_pb_to_doc_captcha():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    pb = protobuf.shared_pb2.Policy()
    pb.policy_id = \
        b'\x01\xb6\x0e\xeb*\xc9OA\x9b\x0cG\xdc\xbc\xf67\xf7'
    pb.name = 'Test'
    pb.created_at = created_at.isoformat()
    pb.updated_at = updated_at.isoformat()
    pb.captcha_solver_id = \
        b'\xe2\x72\x23\xd3\x85\xef\x4e\x89\x8f\xc8\xdb\xcf\x8d\xf0\xce\x97'

    doc = Policy.convert_pb_to_doc(pb)
    assert doc['captcha_solver_id'] == 'e27223d3-85ef-4e89-8fc8-dbcf8df0ce97'


def test_policy_authentication():
    auth1 = PolicyAuthentication({'enabled': True})
    auth2 = PolicyAuthentication({'enabled': False})
    assert     auth1.is_enabled()
    assert not auth2.is_enabled()


def test_policy_limit_cost():
    limits = PolicyLimits({"max_cost": 10.5})
    assert not limits.exceeds_max_cost(10.0)
    assert not limits.exceeds_max_cost(10.5)
    assert     limits.exceeds_max_cost(11.0)

    # This should be false because we didn't set a limit on it.
    assert not limits.met_item_limit(100)


def test_policy_limit_duration():
    limits = PolicyLimits({"max_duration": 60.0})
    limits.max_duration == 60.0

    # These should be false because we didn't set limits on them.
    assert not limits.exceeds_max_cost(100)
    assert not limits.met_item_limit(100)


def test_policy_limit_items():
    limits = PolicyLimits({"max_items": 60})
    assert not limits.met_item_limit(59)
    assert     limits.met_item_limit(60)
    assert     limits.met_item_limit(61)

    # This should be false because we didn't set a limit on it.
    assert not limits.exceeds_max_cost(100)


def test_policy_limit_invalid():
    with pytest.raises(PolicyValidationError):
        PolicyLimits({"max_items": -10})
    with pytest.raises(PolicyValidationError):
        PolicyLimits({"max_duration": -10})


def test_policy_mime_rules_text_only():
    mime_type_rules = PolicyMimeTypeRules([
        {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
        {'save': False},
    ])
    assert     mime_type_rules.should_save('text/plain')
    assert not mime_type_rules.should_save('application/pdf')
    assert not mime_type_rules.should_save('image/png')

    # Same rules but with the match & save inverted.
    mime_type_rules = PolicyMimeTypeRules([
        {'pattern': '^text/', 'match': 'DOES_NOT_MATCH', 'save': False},
        {'save': True},
    ])
    assert     mime_type_rules.should_save('text/plain')
    assert not mime_type_rules.should_save('application/pdf')
    assert not mime_type_rules.should_save('image/png')


def test_policy_mime_rules_no_images():
    mime_type_rules = PolicyMimeTypeRules([
        {'pattern': '^image/', 'match': 'MATCHES', 'save': False},
        {'save': True},
    ])
    assert     mime_type_rules.should_save('text/plain')
    assert     mime_type_rules.should_save('application/pdf')
    assert not mime_type_rules.should_save('image/png')


def test_policy_mime_rules_text_and_images():
    mime_type_rules = PolicyMimeTypeRules([
        {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
        {'pattern': '^image/', 'match': 'MATCHES', 'save': True},
        {'save': False},
    ])
    assert     mime_type_rules.should_save('text/plain')
    assert not mime_type_rules.should_save('application/pdf')
    assert     mime_type_rules.should_save('image/png')


def test_policy_mime_rules_no_rules():
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([])


def test_policy_mime_rules_missing_pattern_or_match():
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/', 'save': True},
            {'save': False},
        ])
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'match': 'MATCHES', 'save': True},
            {'save': False},
        ])

def test_policy_mime_rules_invalid_regex():
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/(', 'match': 'MATCHES', 'save': True},
            {'save': False},
        ])

def test_policy_mime_rules_invalid_terminal():
    # Save is required in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
            {},
        ])
    # Pattern is not allowed in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
            {'pattern': '^image/', 'save': True},
        ])
    # Match is not allowed in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
            {'match': 'MATCHES', 'save': True},
        ])


def test_policy_mime_rules_missing_save():
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/(', 'match': 'MATCHES'},
            {'save': False},
        ])
    with pytest.raises(PolicyValidationError):
        PolicyMimeTypeRules([
            {'pattern': '^text/(', 'match': 'MATCHES', 'save': True},
            {},
        ])


def test_policy_proxy_never_proxy():
    ''' Never use a proxy. '''
    proxy_rules = PolicyProxyRules([
        {},
    ])
    proxy = proxy_rules.get_proxy_url('https://foo.com/index.html')
    assert proxy == (None, None)


def test_policy_proxy_invalid_terminal():
    ''' Last rule may not contain match or pattern. '''
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'match': 'MATCHES'},
        ])
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'pattern': '[a-z]+'},
        ])


def test_policy_proxy_always_proxy():
    ''' Always use a proxy. '''
    proxy_rules = PolicyProxyRules([
        {'proxy_url': 'socks5://squid:3128'},
    ])
    proxy = proxy_rules.get_proxy_url('https://foo.com/index.html')
    assert proxy == ('socks5', 'socks5://squid:3128')


def test_policy_proxy_conditional_proxy():
    ''' Use a proxy for certain hosts. '''
    proxy_rules = PolicyProxyRules([
        {'match': 'MATCHES',
         'pattern': r'\.onion',
         'proxy_url': 'socks5://tor:9050'},
        {}
    ])
    proxy1 = proxy_rules.get_proxy_url('https://foo.onion/index.html')
    proxy2 = proxy_rules.get_proxy_url('https://foo.com/index.html')
    assert proxy1 == ('socks5', 'socks5://tor:9050')
    assert proxy2 == (None, None)


def test_policy_proxy_invalid_non_terminal():
    # Proxy URL is required in non-terminal rule.
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'match': 'MATCHES',
             'pattern': r'\.onion'},
            {}
        ])
    # Match is required in non-terminal rule.
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'pattern': r'\.onion',
             'proxy_url': 'socks5://tor:9050'},
            {}
        ])
    # Pattern is required in non-terminal rule.
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'match': 'MATCHES',
             'proxy_url': 'socks5://tor:9050'},
            {}
        ])
    # Pattern must be a valid regex.
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'match': 'MATCHES',
             'pattern': r'[',
             'proxy_url': 'socks5://tor:9050'},
            {}
        ])

def test_policy_proxy_invalid_url_scheme():
    with pytest.raises(PolicyValidationError):
        proxy_rules = PolicyProxyRules([
            {'proxy_url': 'ftp://domain.example'},
        ])


def test_policy_robots_invalid_usage():
    with pytest.raises(PolicyValidationError):
        robots = PolicyRobotsTxt(doc={})


def test_policy_url_normalization_normalize():
    ''' Normalize a URL. '''
    url_normalization = PolicyUrlNormalization({
        'enabled': True,
        'strip_parameters': list(),
    })
    url = url_normalization.normalize(
        'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4')
    assert url == 'http://a.com/?PHPSESSID=4&bar=3&foo=1&foo=2'


def test_policy_url_normalization_no_normalize():
    ''' Do not normalize a URL. '''
    url_normalization = PolicyUrlNormalization({
        'enabled': False,
    })
    url = url_normalization.normalize(
            'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4')
    assert url == 'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4'


def test_policy_url_normalization_strip():
    ''' Strip a parameter from a URL. '''
    url_normalization = PolicyUrlNormalization({
        'enabled': True,
        'strip_parameters': ['PHPSESSID'],
    })
    url = url_normalization.normalize(
            'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4')
    assert url == 'http://a.com/?bar=3&foo=1&foo=2'


def test_policy_url_rules_crawl_depth():
    # This URL policy increases cost by 1, i.e. tracks crawl depth.
    url_rules = PolicyUrlRules(
        [{'action': 'ADD', 'amount': 1}],
        seeds=['https://foo.com/']
    )
    assert url_rules.get_cost(10, 'https://foo.com/index.html') == 11


def test_policy_url_rules_regex():
    url_rules = PolicyUrlRules([
        {
            'match': 'MATCHES',
            'pattern': '^https://foo.com/',
            'action': 'ADD',
            'amount': 1,
        },
        {
            'action': 'MULTIPLY',
            'amount': -1,
        },
    ], seeds=['https://foo.com'])
    assert url_rules.get_cost(10, 'https://foo.com/index.html') == 11
    assert url_rules.get_cost(10, 'https://bar.net/index.html') == -10


def test_policy_url_rules_stay_in_domain():
    # I used DOES_NOT_MATCH here just to test it out, but this policy
    # could also be written with MATCH and reverse the MULTIPLY -1 & ADD +1.
    url_rules = PolicyUrlRules([
        {
            'match': 'DOES_NOT_MATCH',
            'pattern': '^https?://({SEED_DOMAINS})/',
            'action': 'MULTIPLY',
            'amount': -1,
        },
        {
            'action': 'ADD',
            'amount': 1.5,
        },
    ], seeds=['https://foo.com/index.html', 'https://bar.net/index.php'])
    assert url_rules.get_cost(10, 'http://foo.com/about.html') == 11.5
    assert url_rules.get_cost(10, 'https://bar.net/about.php') == 11.5
    assert url_rules.get_cost(10, 'http://baz.org/?q=about') == -10


def test_policy_url_rules_no_rules():
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([], seeds=['https://foo.com'])


def test_policy_url_rules_invalid_non_terminal():
    # Match is required in non-terminal:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            {'pattern': r'^https:', 'action': 'ADD', 'amount': 1},
            {'action': 'ADD', 'amount': 2},
        ], seeds=['https://foo.com'])
    # Pattern is required in non-terminal:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            {'match': 'MATCHES', 'action': 'ADD', 'amount': 1},
            {'action': 'ADD', 'amount': 2},
        ], seeds=['https://foo.com'])
    # Action is required in non-terminal:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            {'pattern': r'^https:', 'match': 'MATCHES', 'amount': 1},
            {'action': 'ADD', 'amount': 2},
        ], seeds=['https://foo.com'])
    # Amount is required in non-terminal:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            {'pattern': r'^https:', 'match': 'MATCHES', 'action': 'ADD'},
            {'action': 'ADD', 'amount': 2},
        ], seeds=['https://foo.com'])
    # Pattern must be valid regex:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            {'pattern': r'[',
             'match': 'MATCHES',
             'action': 'ADD',
             'amount': 1},
            {'action': 'ADD', 'amount': 2},
        ], seeds=['https://foo.com'])


def test_policy_url_rules_invalid_terminal():
    rule1 = {'pattern': r'^h', 'match': 'MATCHES', 'action': 'ADD', 'amount': 1}

    # Action is required in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            rule1,
            {'amount': 2},
        ], seeds=['https://foo.com'])
    # Action is required in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            rule1,
            {'action': 'ADD'},
        ], seeds=['https://foo.com'])

    # Match is not allowed in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            rule1,
            {'action': 'ADD', 'amount': 2, 'match': 'MATCHES'},
        ], seeds=['https://foo.com'])
    # Pattern is not allowed in terminal rule:
    with pytest.raises(PolicyValidationError):
        PolicyUrlRules([
            rule1,
            {'action': 'ADD', 'amount': 2, 'pattern': '^https'},
        ], seeds=['https://foo.com'])


def test_policy_user_agent_single_agent():
    '''
    User agents policy is non deterministic if there is more than one user
    agent–it calls random.choice()–so there's no test for multiple user agents,
    but the single agent test is deterministic and provides the same code
    coverage.
    '''
    user_agents = PolicyUserAgents([
        {'name': 'Starbelly/{VERSION}'},
    ], version='1.0.0')
    assert user_agents.get_user_agent() == 'Starbelly/1.0.0'


def test_policy_user_agent_invalid():
    with pytest.raises(PolicyValidationError):
        PolicyUserAgents([], version='1.0.0')
    with pytest.raises(PolicyValidationError):
        PolicyUserAgents([{'name': ''}], version='1.0.0')


def test_policy_constructor():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': updated_at,
        'authentication': {'enabled': True},
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    policy = Policy(doc, version='1.0.0', seeds=[])
    assert isinstance(policy.authentication, PolicyAuthentication)
    assert policy.captcha_solver is None
    assert isinstance(policy.limits, PolicyLimits)
    assert isinstance(policy.mime_type_rules, PolicyMimeTypeRules)
    assert isinstance(policy.proxy_rules, PolicyProxyRules)
    assert isinstance(policy.robots_txt, PolicyRobotsTxt)
    assert isinstance(policy.url_normalization, PolicyUrlNormalization)
    assert isinstance(policy.url_rules, PolicyUrlRules)
    assert isinstance(policy.user_agents, PolicyUserAgents)


def test_policy_constructor_blank_name():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': '',
        'created_at': created_at,
        'updated_at': updated_at,
        'authentication': {'enabled': True},
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    with pytest.raises(PolicyValidationError):
        policy = Policy(doc, version='1.0.0', seeds=[])


def test_policy_constructor_captcha():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': updated_at,
        'authentication': {'enabled': True},
        'captcha_solver': {
            'id': b'captcha1',
            'name': 'CAPTCHA Solver 1',
            'service_url': 'https://solver.example',
            'api_key': 'test-key',
            'require_phrase': False,
            'case_sensitive': False,
            'characters': 'abcdefg',
            'require_math': False,
            'min_length': 6,
            'max_length': 6,
        },
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    policy = Policy(doc, version='1.0.0', seeds=[])
    assert isinstance(policy.captcha_solver, CaptchaSolver)


def test_policy_replace_mime_rules():
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    doc = {
        'id': '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': updated_at,
        'authentication': {'enabled': True},
        'limits': {
            'max_cost': 10,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [
            {'proxy_url': 'socks5://localhost:1234'},
        ],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
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
    policy1 = Policy(doc, version='1.0.0', seeds=[])
    policy2 = policy1.replace_mime_type_rules([
            {'match': 'MATCHES', 'pattern': '^application/', 'save': True},
            {'save': False},
    ])
    # These properties are all the same:
    assert policy1.authentication is policy2.authentication
    assert policy1.captcha_solver is policy2.captcha_solver
    assert policy1.limits is policy2.limits
    assert policy1.proxy_rules is policy2.proxy_rules
    assert policy1.robots_txt is policy2.robots_txt
    assert policy1.url_normalization is policy2.url_normalization
    assert policy1.url_rules is policy2.url_rules
    assert policy1.user_agents is policy2.user_agents
    # The MIME type rules are different:
    assert policy1.mime_type_rules is not policy2.mime_type_rules
    assert     policy1.mime_type_rules.should_save('text/plain')
    assert not policy1.mime_type_rules.should_save('application/json')
    assert not policy2.mime_type_rules.should_save('text/plain')
    assert     policy2.mime_type_rules.should_save('application/json')

