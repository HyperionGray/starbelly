import unittest

from ..policy import *


SEEDS = {'http://test1.com', 'https://test2.org'}
VERSION = '1.0.0'


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
        self.assertFalse(limits.exceeds_max_duration(60.0))
        self.assertTrue(limits.exceeds_max_duration(60.1))

        # These should be false because we didn't set limits on them.
        self.assertFalse(limits.exceeds_max_cost(100))
        self.assertFalse(limits.exceeds_max_items(100))

    def test_items(self):
        limits = PolicyLimits({"max_items": 60})
        self.assertFalse(limits.exceeds_max_items(59))
        self.assertFalse(limits.exceeds_max_items(60))
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


class TestPolicyRobotsTxt(unittest.TestCase):
    # PolicyRobotsTxt.is_allowed() is async, so I don't know how to write
    # tests for it. This is just a placeholder test to fill in later.
    pass


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
