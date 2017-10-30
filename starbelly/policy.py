import base64
import logging
import random
import re
from urllib.parse import urlparse
from uuid import UUID

import dateutil.parser
import rethinkdb as r
import w3lib.url

from . import VERSION
import protobuf.shared_pb2


logger = logging.getLogger(__name__)
ACTION_ENUM = protobuf.shared_pb2.PolicyUrlRule.Action
MATCH_ENUM = protobuf.shared_pb2.PatternMatch
USAGE_ENUM = protobuf.shared_pb2.PolicyRobotsTxt.Usage


class PolicyValidationError(Exception):
    ''' Custom error for policy validation. '''


def _invalid(message, location=None):
    ''' A helper for validating policies. '''
    if location is None:
        raise PolicyValidationError(f'{message}.')
    else:
        raise PolicyValidationError(f'{message} in {location}.')


class PolicyManager:
    ''' Manages policy objects. '''

    def __init__(self, db_pool):
        ''' Constructor. '''
        self._db_pool = db_pool

    async def delete_policy(self, policy_id):
        ''' Delete a policy. '''
        async with self._db_pool.connection() as conn:
            await r.table('policy').get(policy_id).delete().run(conn)

    async def get_policy(self, policy_id):
        ''' Get policy details. '''
        async with self._db_pool.connection() as conn:
            policy = await r.table('policy').get(policy_id).run(conn)
        return policy

    async def list_policies(self, limit, offset):
        ''' Return a list of policies. '''
        policies = list()
        query = (
            r.table('policy')
             .order_by(index='name')
             .skip(offset)
             .limit(limit)
        )

        async with self._db_pool.connection() as conn:
            count = await r.table('policy').count().run(conn)
            cursor = await query.run(conn)
            async for policy in cursor:
                policies.append(policy)
            await cursor.close()

        return count, policies

    async def set_policy(self, policy):
        '''
        Save policy details.

        If the policy has an ID, then that the corresponding document is
        updated and this method returns None. If the policy does not have an ID,
        then a new document is created and this method returns the new ID.
        '''
        # Validate policy by trying to instantiate a Policy object, which will
        # raise an exception if the policy is invalid.
        Policy(
            policy,
            version=VERSION,
            seeds=['http://test1.com', 'http://test2.org'],
            robots_txt_manager=None
        )

        # Save policy.
        async with self._db_pool.connection() as conn:
            if 'id' in policy:
                policy['updated_at'] = r.now()
                await (
                    r.table('policy')
                     .get(policy['id'])
                     .update(policy)
                     .run(conn)
                )
                policy_id = None
            else:
                policy['created_at'] = r.now()
                policy['updated_at'] = r.now()
                result = await r.table('policy').insert(policy).run(conn)
                policy_id = result['generated_keys'][0]

        return policy_id


class Policy:
    ''' Container for policies. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        pb.policy_id = UUID(doc['id']).bytes
        pb.name = doc['name']
        pb.created_at = doc['created_at'].isoformat()
        pb.updated_at = doc['updated_at'].isoformat()

        # A copy of a policy is stored with each job, so we need to be able
        # to gracefully handle old policies that are missing expected fields.
        PolicyAuthentication.convert_doc_to_pb(doc.get('authentication',
            dict()), pb.authentication)
        PolicyLimits.convert_doc_to_pb(doc.get('limits', dict()), pb.limits)
        PolicyMimeTypeRules.convert_doc_to_pb(doc.get('mime_type_rules',
            list()), pb.mime_type_rules)
        PolicyProxyRules.convert_doc_to_pb(doc.get('proxy_rules', list()),
            pb.proxy_rules)
        PolicyRobotsTxt.convert_doc_to_pb(doc.get('robots_txt', dict()),
            pb.robots_txt)
        PolicyUrlNormalization.convert_doc_to_pb(doc.get('url_normalization',
            dict()), pb.url_normalization)
        PolicyUrlRules.convert_doc_to_pb(doc.get('url_rules', list()),
            pb.url_rules)
        PolicyUserAgents.convert_doc_to_pb(doc.get('user_agents', list()),
            pb.user_agents)

    @staticmethod
    def convert_pb_to_doc(pb):
        ''' Convert policy from protobuf to document. '''
        doc = {
            'name': pb.name,
            'authentication': dict(),
            'limits': dict(),
            'mime_type_rules': list(),
            'proxy_rules': list(),
            'robots_txt': dict(),
            'url_normalization': dict(),
            'url_rules': list(),
            'user_agents': list(),
        }
        if pb.HasField('policy_id'):
            doc['id'] = str(UUID(bytes=pb.policy_id))
        if pb.HasField('created_at'):
            doc['created_at'] = dateutil.parser.parse(pb.created_at)
        if pb.HasField('updated_at'):
            doc['updated_at'] = dateutil.parser.parse(pb.updated_at)
        PolicyAuthentication.convert_pb_to_doc(pb.authentication,
            doc['authentication'])
        PolicyLimits.convert_pb_to_doc(pb.limits, doc['limits'])
        PolicyMimeTypeRules.convert_pb_to_doc(pb.mime_type_rules,
            doc['mime_type_rules'])
        PolicyProxyRules.convert_pb_to_doc(pb.proxy_rules, doc['proxy_rules'])
        PolicyRobotsTxt.convert_pb_to_doc(pb.robots_txt, doc['robots_txt'])
        PolicyUrlNormalization.convert_pb_to_doc(pb.url_normalization,
            doc['url_normalization'])
        PolicyUrlRules.convert_pb_to_doc(pb.url_rules, doc['url_rules'])
        PolicyUserAgents.convert_pb_to_doc(pb.user_agents, doc['user_agents'])
        return doc

    def __init__(self, doc, version, seeds, robots_txt_manager):
        ''' Initialize from ``doc``, a dict representation of a policy. '''
        if doc['name'].strip() == '':
            _invalid('Policy name cannot be blank')

        self.authentication = PolicyAuthentication(doc['authentication'])
        self.captcha_solver = PolicyCaptchaSolver() #TODO
        self.limits = PolicyLimits(doc['limits'])
        self.mime_type_rules = PolicyMimeTypeRules(doc['mime_type_rules'])
        self.proxy_rules = PolicyProxyRules(doc['proxy_rules'])
        self.robots_txt = PolicyRobotsTxt(doc['robots_txt'], robots_txt_manager,
            self)
        self.url_normalization = PolicyUrlNormalization(
            doc['url_normalization'])
        self.url_rules = PolicyUrlRules(doc['url_rules'], seeds)
        self.user_agents = PolicyUserAgents(doc['user_agents'], version)

    def replace_mime_type_rules(self, doc):
        '''
        Return a shallow copy of this policy with new MIME type rules from
        ``doc``.
        '''
        policy = Policy.__new__(Policy)
        policy.authentication = self.authentication
        policy.captcha_solver = self.captcha_solver
        policy.limits = self.limits
        policy.mime_type_rules = PolicyMimeTypeRules(doc)
        policy.proxy_rules = self.proxy_rules
        policy.robots_txt = self.robots_txt
        policy.url_normalization = self.url_normalization
        policy.url_rules = self.url_rules
        policy.user_agents = self.user_agents
        return policy


class PolicyAuthentication:
    ''' Policy for authenticated crawling. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        pb.enabled = doc['enabled']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        doc['enabled'] = pb.enabled

    def __init__(self, doc):
        ''' Initialize from ``doc``, a dict representation of limits. '''
        self._enabled = doc.get('enabled', False)

    def is_enabled(self):
        ''' Return True if authentication is enabled. '''
        return self._enabled


class PolicyCaptchaSolver:
    ''' Encapsulates a CAPTCHA solving service. '''
    def __init__(self):
        ''' Constructor. '''
        self.service_url = 'https://api.anti-captcha.com/'
        self.client_key = '--------------------------------'
        self.phrase = False
        self.case = False
        self.numeric = 0
        self.math = False
        self.min_length = None
        self.max_length = None

    def get_command(self, img_data):
        ''' Return a JSON command suitable for posting to CAPTCHA API. '''
        img_b64 = base64.b64encode(img_data).decode('ascii')
        return {
            'clientKey': self.client_key,
            'task': {
                'type': 'ImageToTextTask',
                'body': img_b64,
                'phrase': self.phrase,
                'case': self.case,
                'numeric': self.numeric,
                'math': self.math,
                'minLength': self.min_length or 0,
                'maxLength': self.max_length or 0,
            }
        }


class PolicyLimits:
    ''' Limits on crawl size/duration. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        if doc.get('max_cost') is not None:
            pb.max_cost = doc['max_cost']
        if doc.get('max_duration') is not None:
            pb.max_duration = doc['max_duration']
        if doc.get('max_items') is not None:
            pb.max_items = doc['max_items']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        doc['max_cost'] = pb.max_cost if pb.HasField('max_cost') else None
        doc['max_duration'] = pb.max_duration if pb.HasField('max_duration') \
            else None
        doc['max_items'] = pb.max_items if pb.HasField('max_items') else None

    def __init__(self, doc):
        ''' Initialize from ``doc``, a dict representation of limits. '''
        self._max_cost = doc.get('max_cost')
        self._max_duration = doc.get('max_duration')
        self._max_items = doc.get('max_items')
        if self._max_duration is not None and self._max_duration < 0:
            _invalid('Max duration must be ≥0')
        if self._max_items is not None and self._max_items < 0:
            _invalid('Max items must be ≥0')

    def exceeds_max_cost(self, cost):
        ''' Return true if ``cost`` is greater than the policy's max cost. '''
        return self._max_cost is not None and cost > self._max_cost

    def exceeds_max_duration(self, duration):
        '''
        Return true if ``duration`` is greater than or equal to the policy's max
        duration.
        '''
        return self._max_duration is not None and duration >= self._max_duration

    def exceeds_max_items(self, items):
        '''
        Return true if ``items`` is greater than or equal to the policy's max
        item count.
        '''
        return self._max_items is not None and items >= self._max_items


class PolicyMimeTypeRules:
    ''' Filter responses by MIME type. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        for doc_mime in doc:
            pb_mime = pb.add()
            if 'pattern' in doc_mime:
                pb_mime.pattern = doc_mime['pattern']
            if 'match' in doc_mime:
                pb_mime.match = MATCH_ENUM.Value(doc_mime['match'])
            if 'save' in doc_mime:
                pb_mime.save = doc_mime['save']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        for pb_mime in pb:
            doc_mime = dict()
            if pb_mime.HasField('pattern'):
               doc_mime['pattern'] = pb_mime.pattern
            if pb_mime.HasField('match'):
               doc_mime['match'] = MATCH_ENUM.Name(pb_mime.match)
            if pb_mime.HasField('save'):
               doc_mime['save'] = pb_mime.save
            doc.append(doc_mime)

    def __init__(self, docs):
        ''' Initialize from ``docs``, a dict representation of MIME rules. '''

        if len(docs) == 0:
            _invalid('At least one MIME type rule is required')

        # Rules are stored as list of tuples: (pattern, match, save)
        self._rules = list()
        max_index = len(docs) - 1
        MATCH_ENUM = protobuf.shared_pb2.PatternMatch

        for index, mime_type_rule in enumerate(docs):
            if index < max_index:
                location = 'MIME type rule #{}'.format(index+1)
                if mime_type_rule.get('pattern', '').strip() == '':
                    _invalid('Pattern is required', location)
                if 'save' not in mime_type_rule:
                    _invalid('Save selector is required', location)
                if 'match' not in mime_type_rule:
                    _invalid('Match selector is required', location)

                try:
                    pattern_re = re.compile(mime_type_rule['pattern'])
                except:
                    _invalid('Invalid regular expression', location)

                self._rules.append((
                    pattern_re,
                    mime_type_rule['match'],
                    mime_type_rule['save'],
                ))
            else:
                location = 'last MIME type rule'
                if 'save' not in mime_type_rule:
                    _invalid('Save selector is required', location)
                if 'pattern' in mime_type_rule:
                    _invalid('Pattern is not allowed', location)
                if 'match' in mime_type_rule:
                    _invalid('Match selector is not allowed', location)
                self._rules.append((None, None, mime_type_rule['save']))

    def should_save(self, mime_type):
        '''
        Returns True if ``mime_type`` is approved by this policy.

        If rules are valid, this method always returns True or False.
        '''
        for pattern, match, save in self._rules:
            if pattern is None:
                return save
            else:
                result = pattern.search(mime_type) is not None
                if match == 'DOES_NOT_MATCH':
                    result = not result
                if result:
                    return save


class PolicyProxyRules:
    ''' Modify which proxies are used for each request. '''

    PROXY_SCHEMES = ('http', 'https', 'socks4', 'socks4a', 'socks5')

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        for doc_proxy in doc:
            pb_proxy = pb.add()
            if 'pattern' in doc_proxy:
                pb_proxy.pattern = doc_proxy['pattern']
            if 'match' in doc_proxy:
                pb_proxy.match = MATCH_ENUM.Value(doc_proxy['match'])
            if 'proxy_url' in doc_proxy:
                pb_proxy.proxy_url = doc_proxy['proxy_url']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        for pb_proxy in pb:
            doc_proxy = dict()
            if pb_proxy.HasField('pattern'):
               doc_proxy['pattern'] = pb_proxy.pattern
            if pb_proxy.HasField('match'):
               doc_proxy['match'] = MATCH_ENUM.Name(pb_proxy.match)
            if pb_proxy.HasField('proxy_url'):
               doc_proxy['proxy_url'] = pb_proxy.proxy_url
            doc.append(doc_proxy)

    def __init__(self, docs):
        ''' Initialize from ``docs``, a dict representation of proxy rules. '''

        # Rules are stored as list of tuples: (pattern, match, proxy_type,
        # proxy_url)
        self._rules = list()
        max_index = len(docs) - 1
        MATCH_ENUM = protobuf.shared_pb2.PatternMatch

        for index, proxy_rule in enumerate(docs):
            if index < max_index:
                location = 'proxy rule #{}'.format(index+1)

                if proxy_rule.get('pattern', '').strip() == '':
                    _invalid('Pattern is required', location)
                try:
                    pattern_re = re.compile(proxy_rule['pattern'])
                except:
                    _invalid('Invalid regular expression', location)

                try:
                    match = (proxy_rule['match'] == 'MATCHES')
                except KeyError:
                    _invalid('Match selector is required', location)

                proxy_url = proxy_rule.get('proxy_url', '')
                if proxy_url == '':
                    _invalid('Proxy URL is required', location)
            else:
                location = 'last proxy rule'

                if 'pattern' in proxy_rule:
                    _invalid('Pattern is not allowed', location)
                if 'match' in proxy_rule:
                    _invalid('Pattern is not allowed', location)

                pattern_re = None
                match = None
                proxy_type = None
                proxy_url = proxy_rule.get('proxy_url')

            if proxy_url is None:
                proxy_type = None
            else:
                proxy_url = proxy_url.strip()
                try:
                    parsed = urlparse(proxy_url)
                    proxy_type = parsed.scheme
                    if proxy_type not in self.PROXY_SCHEMES:
                        raise ValueError()
                except:
                    schemes = ', '.join(self.PROXY_SCHEMES)
                    _invalid('Must have a valid URL with one of the '
                             f'following schemes: {schemes}', location)


            self._rules.append((
                pattern_re,
                match,
                proxy_type,
                proxy_url,
            ))

    def get_proxy_url(self, target_url):
        '''
        Return a proxy (type, URL) tuple associated with ``target_url`` or
        (None, None) if no such proxy is defined.
        '''
        proxy = None, None

        for pattern, needs_match, proxy_type, proxy_url in self._rules:
            if pattern is not None:
                has_match = pattern.search(target_url) is not None
                if has_match == needs_match:
                    proxy = proxy_type, proxy_url
                    break
            elif proxy_url is not None:
                proxy = proxy_type, proxy_url
                break

        return proxy


class PolicyRobotsTxt:
    ''' Designate how robots.txt affects crawl behavior. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        pb.usage = USAGE_ENUM.Value(doc['usage'])

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        if pb.HasField('usage'):
            doc['usage'] = USAGE_ENUM.Name(pb.usage)

    def __init__(self, doc, robots_txt_manager, parent_policy):
        ''' Initialize from ``doc``, a dict representation of robots policy. '''
        if 'usage' not in doc:
            _invalid('Robots.txt usage is required')
        self._parent_policy = parent_policy
        self._usage = doc['usage']
        self._robots_txt_manager = robots_txt_manager

    async def is_allowed(self, url):
        ''' Returns True if robots policy permits ``url``. '''
        if self._usage == 'IGNORE':
            return True

        result = await self._robots_txt_manager.is_allowed(
            url,
            self._parent_policy
        )

        if self._usage == 'INVERT':
            result = not result

        return result


class PolicyUrlNormalization:
    ''' Customize URL normalization. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        if 'enabled' in doc:
            pb.enabled = doc['enabled']
        if 'strip_parameters' in doc:
            pb.strip_parameters.extend(doc['strip_parameters'])

    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        if pb.HasField('enabled'):
            doc['enabled'] = pb.enabled
        doc['strip_parameters'] = list(pb.strip_parameters)

    def __init__(self, doc):
        ''' Instantiate from a dictionary representation ``doc``. '''
        self._enabled = doc.get('enabled', True)
        self._strip_parameters = doc.get('strip_parameters', list())

    def normalize(self, url):
        ''' Normalize ``url`` according to policy. '''
        if self._enabled:
            if len(self._strip_parameters) > 0:
                url = w3lib.url.url_query_cleaner(url, remove=True,
                    unique=False, parameterlist=self._strip_parameters)

            url = w3lib.url.canonicalize_url(url)

        return url


class PolicyUrlRules:
    ''' Customize link priorities based on URL. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        for doc_url in doc:
            pb_url = pb.add()
            if 'pattern' in doc_url:
                pb_url.pattern = doc_url['pattern']
            if 'match' in doc_url:
                pb_url.match = MATCH_ENUM.Value(doc_url['match'])
            if 'action' in doc_url:
                pb_url.action = ACTION_ENUM.Value(doc_url['action'])
            if 'amount' in doc_url:
                pb_url.amount = doc_url['amount']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        for pb_url in pb:
            doc_url = dict()
            if pb_url.HasField('pattern'):
               doc_url['pattern'] = pb_url.pattern
            if pb_url.HasField('match'):
               doc_url['match'] = MATCH_ENUM.Name(pb_url.match)
            if pb_url.HasField('action'):
               doc_url['action'] = ACTION_ENUM.Name(pb_url.action)
            if pb_url.HasField('amount'):
               doc_url['amount'] = pb_url.amount
            doc.append(doc_url)

    def __init__(self, docs, seeds):
        ''' Initialize from ``docs``, a dict representation of url rules. '''
        if len(docs) == 0:
            _invalid('At least one URL rule is required')

        # Rules are stored as tuples: (pattern, match, action, amount)
        self._rules = list()
        max_index = len(docs) - 1
        seed_domains = {urlparse(seed).hostname for seed in seeds}
        ACTION_ENUM = protobuf.shared_pb2.PolicyUrlRule.Action
        MATCH_ENUM = protobuf.shared_pb2.PatternMatch

        for index, url_rule in enumerate(docs):
            if index < max_index:
                location = 'URL rule #{}'.format(index+1)
                if url_rule.get('pattern', '').strip() == '':
                    _invalid('Pattern is required', location)
                if 'match' not in url_rule:
                    _invalid('Match selector is required', location)
                if 'action' not in url_rule:
                    _invalid('Action selector is required', location)
                if 'amount' not in url_rule:
                    _invalid('Amount is required', location)

                try:
                    pattern_re = re.compile(url_rule['pattern']
                        .format(SEED_DOMAINS='|'.join(seed_domains)))
                except:
                    _invalid('Invalid regular expression', location)

                self._rules.append((
                    pattern_re,
                    url_rule['match'],
                    url_rule['action'],
                    url_rule['amount'],
                ))
            else:
                location = 'last URL rule'
                if 'pattern' in url_rule:
                    _invalid('Pattern is not allowed', location)
                if 'match' in url_rule:
                    _invalid('Match is not allowed', location)
                if 'action' not in url_rule:
                    _invalid('Action is required', location)
                if 'amount' not in url_rule:
                    _invalid('Amount is required', location)
                self._rules.append((
                    None,
                    None,
                    url_rule['action'],
                    url_rule['amount'],
                ))

    def get_cost(self, parent_cost, url):
        ''' Return the cost for a URL. '''
        for pattern, match, action, amount in self._rules:
            if pattern is None:
                break
            else:
                result = pattern.search(url) is not None
                if match == 'DOES_NOT_MATCH':
                    result = not result
                if result:
                    break

        if action == 'ADD':
            return parent_cost + amount
        elif action == 'MULTIPLY':
            return parent_cost * amount

class PolicyUserAgents:
    ''' Specify user agent string to send in HTTP requests. '''

    @staticmethod
    def convert_doc_to_pb(doc, pb):
        ''' Convert policy from document to protobuf. '''
        for doc_user_agent in doc:
            pb_user_agent = pb.add()
            pb_user_agent.name = doc_user_agent['name']

    @staticmethod
    def convert_pb_to_doc(pb, doc):
        ''' Convert policy from protobuf to document. '''
        for user_agent in pb:
            doc.append({
                'name': user_agent.name,
            })

    def __init__(self, docs, version):
        ''' Initialize from ``docs``, a dict representation of user agents. '''
        if len(docs) == 0:
            _invalid('At least one user agent is required')
        self._user_agents = list()
        for index, user_agent in enumerate(docs):
            location = 'User agent #{}'.format(index + 1)
            if user_agent.get('name', '').strip() == '':
                _invalid('Name is required', location)
            self._user_agents.append(user_agent['name'].format(VERSION=version))

    def get_user_agent(self):
        ''' Return a user agent string. '''
        return random.choice(self._user_agents)
