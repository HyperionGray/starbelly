from datetime import datetime, timedelta
import unittest

from ..policy import *


SEEDS = {'http://test1.com', 'https://test2.org'}
VERSION = '1.0.0'
ACTION_ENUM = protobuf.shared_pb2.PolicyUrlRule.Action
MATCH_ENUM = protobuf.shared_pb2.PatternMatch
USAGE_ENUM = protobuf.shared_pb2.PolicyRobotsTxt.Usage


class TestPolicy(unittest.TestCase):
    def test_convert_doc_to_pb(self):
        created_at = datetime.now()
        updated_at = datetime.now() + timedelta(minutes=1)
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
        pb = protobuf.shared_pb2.Policy()
        Policy.convert_doc_to_pb(doc, pb)
        self.assertEqual(pb.policy_id,
            b'\x01\xb6\x0e\xeb*\xc9OA\x9b\x0cG\xdc\xbc\xf67\xf7')
        self.assertEqual(pb.name, 'Test')
        self.assertEqual(pb.created_at, created_at.isoformat())
        self.assertEqual(pb.updated_at, updated_at.isoformat())

        # Authentication
        self.assertTrue(pb.authentication.enabled)

        # Limits
        self.assertEqual(pb.limits.max_cost, 10)

        # MIME type rules
        self.assertEqual(len(pb.mime_type_rules), 2)
        self.assertEqual(pb.mime_type_rules[0].match,
            MATCH_ENUM.Value('MATCHES'))
        self.assertEqual(pb.mime_type_rules[0].pattern, '^text/')
        self.assertTrue(pb.mime_type_rules[0].save)
        self.assertFalse(pb.mime_type_rules[1].save)

        # Proxy rules
        self.assertEqual(len(pb.proxy_rules), 1)
        self.assertEqual(pb.proxy_rules[0].proxy_url,
            'socks5://localhost:1234')

        # Robots.txt
        self.assertEqual(pb.robots_txt.usage, USAGE_ENUM.Value('IGNORE'))

        # URL normalization
        self.assertTrue(pb.url_normalization.enabled)
        self.assertEqual(pb.url_normalization.strip_parameters,
            ['PHPSESSID'])

        # URL rules
        self.assertEqual(len(pb.url_rules), 2)
        self.assertEqual(pb.url_rules[0].action, ACTION_ENUM.Value('ADD'))
        self.assertEqual(pb.url_rules[0].amount, 1)
        self.assertEqual(pb.url_rules[0].match,
            MATCH_ENUM.Value('MATCHES'))
        self.assertEqual(pb.url_rules[0].pattern,
            '^https?://({SEED_DOMAINS})/')
        self.assertEqual(pb.url_rules[1].action,
            ACTION_ENUM.Value('MULTIPLY'))
        self.assertEqual(pb.url_rules[1].amount, 0)

        # User agents
        self.assertEqual(len(pb.user_agents), 1)
        self.assertEqual(pb.user_agents[0].name, 'Test User Agent')

    def test_convert_pb_to_doc(self):
        created_at = datetime.now()
        updated_at = datetime.now() + timedelta(minutes=1)
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
        self.assertEqual(doc['id'],
            '01b60eeb-2ac9-4f41-9b0c-47dcbcf637f7')
        self.assertEqual(doc['name'], 'Test')
        self.assertEqual(doc['created_at'], created_at)
        self.assertEqual(doc['updated_at'], updated_at)

        # Authentication
        self.assertTrue(doc['authentication']['enabled'])

        # Limits
        self.assertEqual(doc['limits']['max_cost'], 10)

        # MIME type rules
        self.assertEqual(len(doc['mime_type_rules']), 2)
        mime1 = doc['mime_type_rules'][0]
        self.assertEqual(mime1['match'], 'MATCHES')
        self.assertEqual(mime1['pattern'], '^text/')
        self.assertTrue(mime1['save'])
        mime2 = doc['mime_type_rules'][1]
        self.assertFalse(mime2['save'])

        # Proxy rules
        self.assertEqual(len(doc['proxy_rules']), 1)
        proxy1 = doc['proxy_rules'][0]
        self.assertEqual(proxy1['proxy_url'], 'socks5://localhost:1234')

        # Robots.txt
        self.assertEqual(doc['robots_txt']['usage'], 'IGNORE')

        # URL normalization
        self.assertTrue(doc['url_normalization']['enabled'])
        self.assertEqual(doc['url_normalization']['strip_parameters'],
            ['PHPSESSID'])

        # URL rules
        self.assertEqual(len(doc['url_rules']), 2)
        url1 = doc['url_rules'][0]
        self.assertEqual(url1['action'], 'ADD')
        self.assertEqual(url1['amount'], 1)
        self.assertEqual(url1['match'], 'MATCHES')
        self.assertEqual(url1['pattern'], '^https?://({SEED_DOMAINS})/')
        url2 = doc['url_rules'][1]
        self.assertEqual(url2['action'], 'MULTIPLY')
        self.assertEqual(url2['amount'], 0)

        # User agents
        self.assertEqual(len(doc['user_agents']), 1)
        agent1 = doc['user_agents'][0]
        self.assertEqual(agent1['name'], 'Test User Agent')

class TestPolicyAuthentication(unittest.TestCase):
    def test_enabled(self):
        auth = PolicyAuthentication({'enabled': True})
        self.assertTrue(auth.is_enabled())

    def test_disabled(self):
        auth = PolicyAuthentication({'enabled': False})
        self.assertFalse(auth.is_enabled())


class TestPolicyLimits(unittest.TestCase):
    def test_cost(self):
        limits = PolicyLimits({"max_cost": 10.5})
        self.assertFalse(limits.exceeds_max_cost(10.0))
        self.assertFalse(limits.exceeds_max_cost(10.5))
        self.assertTrue(limits.exceeds_max_cost(11.0))

        # These should be false because we didn't set limits on them.
        self.assertFalse(limits.exceeds_max_duration(100))
        self.assertFalse(limits.exceeds_max_items(100))

    def test_duration(self):
        limits = PolicyLimits({"max_duration": 60.0})
        self.assertFalse(limits.exceeds_max_duration(59.9))
        self.assertTrue(limits.exceeds_max_duration(60.0))
        self.assertTrue(limits.exceeds_max_duration(60.1))

        # These should be false because we didn't set limits on them.
        self.assertFalse(limits.exceeds_max_cost(100))
        self.assertFalse(limits.exceeds_max_items(100))

    def test_items(self):
        limits = PolicyLimits({"max_items": 60})
        self.assertFalse(limits.exceeds_max_items(59))
        self.assertTrue(limits.exceeds_max_items(60))
        self.assertTrue(limits.exceeds_max_items(61))

        # These should be false because we didn't set limits on them.
        self.assertFalse(limits.exceeds_max_cost(100))
        self.assertFalse(limits.exceeds_max_duration(100))

    def test_invalid(self):
        with self.assertRaises(PolicyValidationError):
            PolicyLimits({"max_items": -10})
        with self.assertRaises(PolicyValidationError):
            PolicyLimits({"max_duration": -10})


class TestPolicyMimeTypeRules(unittest.TestCase):
    def test_text_only(self):
        mime_type_rules = PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
            {'save': False},
        ])
        self.assertTrue(mime_type_rules.should_save('text/plain'))
        self.assertFalse(mime_type_rules.should_save('application/pdf'))
        self.assertFalse(mime_type_rules.should_save('image/png'))

        # Same rules but with the match & save inverted.
        mime_type_rules = PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'DOES_NOT_MATCH', 'save': False},
            {'save': True},
        ])
        self.assertTrue(mime_type_rules.should_save('text/plain'))
        self.assertFalse(mime_type_rules.should_save('application/pdf'))
        self.assertFalse(mime_type_rules.should_save('image/png'))

    def test_no_images(self):
        mime_type_rules = PolicyMimeTypeRules([
            {'pattern': '^image/', 'match': 'MATCHES', 'save': False},
            {'save': True},
        ])
        self.assertTrue(mime_type_rules.should_save('text/plain'))
        self.assertTrue(mime_type_rules.should_save('application/pdf'))
        self.assertFalse(mime_type_rules.should_save('image/png'))

    def test_text_and_images(self):
        mime_type_rules = PolicyMimeTypeRules([
            {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
            {'pattern': '^image/', 'match': 'MATCHES', 'save': True},
            {'save': False},
        ])
        self.assertTrue(mime_type_rules.should_save('text/plain'))
        self.assertFalse(mime_type_rules.should_save('application/pdf'))
        self.assertTrue(mime_type_rules.should_save('image/png'))

    def test_no_rules(self):
        with self.assertRaises(PolicyValidationError):
            PolicyMimeTypeRules([])

    def test_missing_pattern_or_match(self):
        with self.assertRaises(PolicyValidationError):
            PolicyMimeTypeRules([
                {'pattern': '^text/', 'save': True},
                {'save': False},
            ])

        with self.assertRaises(PolicyValidationError):
            PolicyMimeTypeRules([
                {'match': 'MATCHES', 'save': True},
                {'save': False},
            ])

    def test_invalid_regex(self):
        with self.assertRaises(PolicyValidationError):
            PolicyMimeTypeRules([
                {'pattern': '^text/(', 'match': 'MATCHES', 'save': True},
                {'save': False},
            ])

    def test_invalid_last_rule(self):
        with self.assertRaises(PolicyValidationError):
            PolicyMimeTypeRules([
                {'pattern': '^text/', 'match': 'MATCHES', 'save': True},
                {'pattern': '^image/', 'match': 'MATCHES', 'save': True},
            ])


class TestPolicyProxyRules(unittest.TestCase):
    def test_never_proxy(self):
        ''' Never use a proxy. '''
        proxy_rules = PolicyProxyRules([
            {},
        ])
        self.assertEqual(
            (None, None),
            proxy_rules.get_proxy_url('https://foo.com/index.html')
        )

    def test_last_rule(self):
        ''' Last rule may not contain match or pattern. '''
        with self.assertRaises(PolicyValidationError):
            proxy_rules = PolicyProxyRules([
                {'match': 'MATCHES'},
            ])
        with self.assertRaises(PolicyValidationError):
            proxy_rules = PolicyProxyRules([
                {'pattern': '[a-z]+'},
            ])

    def test_always_proxy(self):
        ''' Always use a proxy. '''
        proxy_rules = PolicyProxyRules([
            {'proxy_url': 'socks5://squid:3128'},
        ])
        self.assertEqual(
            ('socks5', 'socks5://squid:3128'),
            proxy_rules.get_proxy_url('https://foo.com/index.html')
        )

    def test_conditional_proxy(self):
        ''' Use a proxy for certain hosts. '''
        proxy_rules = PolicyProxyRules([
            {'match': 'MATCHES',
             'pattern': '\.onion',
             'proxy_url': 'socks5://tor:9050'},
            {}
        ])
        self.assertEqual(
            ('socks5', 'socks5://tor:9050'),
            proxy_rules.get_proxy_url('https://foo.onion/index.html')
        )
        self.assertEqual(
            (None, None),
            proxy_rules.get_proxy_url('https://foo.com/index.html')
        )


class TestPolicyRobotsTxt(unittest.TestCase):
    # PolicyRobotsTxt.is_allowed() is async, so I don't know how to write
    # tests for it. This is just a placeholder test to fill in later.
    pass


class TestPolicyUrlNormalization(unittest.TestCase):
    def test_normalize(self):
        ''' Normalize a URL. '''
        url_normalization = PolicyUrlNormalization({
            'enabled': True,
            'strip_parameters': list(),
        })
        self.assertEqual(
            url_normalization.normalize(
                'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4'),
            'http://a.com/?PHPSESSID=4&bar=3&foo=1&foo=2'
        )

    def test_no_normalize(self):
        ''' Do not normalize a URL. '''
        url_normalization = PolicyUrlNormalization({
            'enabled': False,
        })
        self.assertEqual(
            url_normalization.normalize(
                'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4'),
            'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4'
        )

    def test_strip(self):
        ''' Strip a parameter from a URL. '''
        url_normalization = PolicyUrlNormalization({
            'enabled': True,
            'strip_parameters': ['PHPSESSID'],
        })
        self.assertEqual(
            url_normalization.normalize(
                'http://a.com/?foo=2&foo=1&bar=3&PHPSESSID=4'),
            'http://a.com/?bar=3&foo=1&foo=2'
        )


class TestPolicyUrlRules(unittest.TestCase):
    def test_crawl_depth(self):
        # This URL policy increases cost by 1, i.e. tracks crawl depth.
        url_rules = PolicyUrlRules(
            [{'action': 'ADD', 'amount': 1}],
            seeds=['https://foo.com/']
        )
        self.assertEqual(
            11,
            url_rules.get_cost(10, 'https://foo.com/index.html')
        )

    def test_regex(self):
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
        self.assertEqual(
            url_rules.get_cost(10, 'https://foo.com/index.html'),
            11
        )
        self.assertEqual(
            url_rules.get_cost(10, 'https://bar.net/index.html'),
            -10
        )

    def test_stay_in_domain(self):
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
        self.assertEqual(
            url_rules.get_cost(10, 'http://foo.com/about.html'),
            11.5
        )
        self.assertEqual(
            url_rules.get_cost(10, 'https://bar.net/about.php'),
            11.5
        )
        self.assertEqual(
            url_rules.get_cost(10, 'http://baz.org/?q=about'),
            -10
        )

    def test_no_rules(self):
        with self.assertRaises(PolicyValidationError):
            PolicyUrlRules([], seeds=['https://foo.com'])

    def test_missing_pattern_or_match(self):
        with self.assertRaises(PolicyValidationError):
            PolicyUrlRules([
                {'pattern': '^https:', 'action': 'ADD', 'amount': 1},
                {'action': 'ADD', 'amount': 2},
            ], seeds=['https://foo.com'])

        with self.assertRaises(PolicyValidationError):
            PolicyUrlRules([
                {'match': 'MATCHES', 'action': 'ADD', 'amount': 1},
                {'action': 'ADD', 'amount': 2},
            ], seeds=['https://foo.com'])

    def test_invalid_last_rule(self):
        with self.assertRaises(PolicyValidationError):
            PolicyUrlRules([
                {
                    'pattern': '^https:',
                    'match': 'MATCHES',
                    'action': 'ADD',
                    'amount': 1
                },
                {
                    'pattern': '^http:',
                    'match': 'MATCHES',
                    'action': 'ADD',
                    'amount': 2
                },
            ], seeds=['https://foo.com'])


class TestPolicyUserAgents(unittest.TestCase):
    def test_single_agent(self):
        '''
        User agents policy is non deterministic if there is more than one user
        agent – it calls random.choice()) – so there's no test for multiple user
        agents, but the single agent test provides the same code coverage.
        '''
        user_agents = PolicyUserAgents([
            {'name': 'Starbelly/{VERSION}'},
        ], version='1.0.0')
        self.assertEqual(
            user_agents.get_user_agent(),
            'Starbelly/1.0.0'
        )

    def test_no_user_agents(self):
        with self.assertRaises(PolicyValidationError):
            PolicyUserAgents([], version='1.0.0')
