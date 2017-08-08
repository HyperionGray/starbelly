import logging
import random
import re
from urllib.parse import urlparse
from uuid import UUID

import rethinkdb as r

from . import VERSION
import protobuf.shared_pb2


logger = logging.getLogger(__name__)


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

    def convert_doc_to_pb(self, policy_doc, policy_pb):
        ''' Convert a policy document to a protobuf message. '''
        policy_pb.policy_id = UUID(policy_doc['id']).bytes
        policy_pb.name = policy_doc['name']
        policy_pb.created_at = policy_doc['created_at'].isoformat()
        policy_pb.updated_at = policy_doc['updated_at'].isoformat()
        if policy_doc['limits'].get('max_cost') is not None:
            policy_pb.limits.max_cost = policy_doc['limits']['max_cost']
        if policy_doc['limits'].get('max_duration') is not None:
            policy_pb.limits.max_duration = policy_doc['limits']['max_duration']
        if policy_doc['limits'].get('max_items') is not None:
            policy_pb.limits.max_items = policy_doc['limits']['max_items']
        match_enum = protobuf.shared_pb2.PatternMatch
        for mime_doc in policy_doc['mime_type_rules']:
            mime = policy_pb.mime_type_rules.add()
            if 'pattern' in mime_doc:
                mime.pattern = mime_doc['pattern']
            if 'match' in mime_doc:
                mime.match = match_enum.Value(mime_doc['match'])
            if 'save' in mime_doc:
                mime.save = mime_doc['save']
        for proxy_doc in policy_doc['proxy_rules']:
            proxy = policy_pb.proxy_rules.add()
            if 'pattern' in proxy_doc:
                proxy.pattern = proxy_doc['pattern']
            if 'match' in proxy_doc:
                proxy.match = match_enum.Value(proxy_doc['match'])
            if 'proxy_url' in proxy_doc:
                proxy.proxy_url = proxy_doc['proxy_url']
        usage_enum = protobuf.shared_pb2.PolicyRobotsTxt.Usage
        usage = policy_doc['robots_txt']['usage']
        policy_pb.robots_txt.usage = usage_enum.Value(usage)
        for user_agent_doc in policy_doc['user_agents']:
            user_agent = policy_pb.user_agents.add()
            user_agent.name = user_agent_doc['name']
        action_enum = protobuf.shared_pb2.PolicyUrlRule.Action
        for url_doc in policy_doc['url_rules']:
            url = policy_pb.url_rules.add()
            if 'pattern' in url_doc:
                url.pattern = url_doc['pattern']
            if 'match' in url_doc:
                url.match = match_enum.Value(url_doc['match'])
            if 'action' in url_doc:
                url.action = action_enum.Value(url_doc['action'])
            if 'amount' in url_doc:
                url.amount = url_doc['amount']

    def convert_pb_to_doc(self, policy_pb):
        ''' Convert protobuf policy message into a dict structure. '''
        action_enum = protobuf.shared_pb2.PolicyUrlRule.Action
        match_enum = protobuf.shared_pb2.PatternMatch
        usage_enum = protobuf.shared_pb2.PolicyRobotsTxt.Usage
        policy_doc = {
            'name': policy_pb.name,
            'limits': dict(),
            'mime_type_rules': list(),
            'proxy_rules': list(),
            'robots_txt': dict(),
            'url_rules': list(),
            'user_agents': list(),
        }
        if policy_pb.HasField('policy_id'):
            policy_doc['id'] = str(UUID(bytes=policy_pb.policy_id))
        if policy_pb.HasField('limits'):
            limits = policy_pb.limits
            policy_doc['limits']['max_cost'] = limits.max_cost if \
                limits.HasField('max_cost') else None
            policy_doc['limits']['max_duration'] = limits.max_duration if \
                limits.HasField('max_duration') else None
            policy_doc['limits']['max_items'] = limits.max_items if \
                limits.HasField('max_items') else None
        for mime_type_rule in policy_pb.mime_type_rules:
            new_doc = dict()
            if mime_type_rule.HasField('pattern'):
               new_doc['pattern'] = mime_type_rule.pattern
            if mime_type_rule.HasField('match'):
               new_doc['match'] = match_enum.Name(mime_type_rule.match)
            if mime_type_rule.HasField('save'):
               new_doc['save'] = mime_type_rule.save
            policy_doc['mime_type_rules'].append(new_doc)
        for proxy_rule in policy_pb.proxy_rules:
            new_doc = dict()
            if proxy_rule.HasField('pattern'):
               new_doc['pattern'] = proxy_rule.pattern
            if proxy_rule.HasField('match'):
               new_doc['match'] = match_enum.Name(proxy_rule.match)
            if proxy_rule.HasField('proxy_url'):
               new_doc['proxy_url'] = proxy_rule.proxy_url
            policy_doc['proxy_rules'].append(new_doc)
        if policy_pb.HasField('robots_txt'):
            robots_txt = policy_pb.robots_txt
            if robots_txt.HasField('usage'):
                policy_doc['robots_txt']['usage'] = usage_enum.Name(
                    robots_txt.usage)
        for url_rule in policy_pb.url_rules:
            new_doc = dict()
            if url_rule.HasField('pattern'):
               new_doc['pattern'] = url_rule.pattern
            if url_rule.HasField('match'):
               new_doc['match'] = match_enum.Name(url_rule.match)
            if url_rule.HasField('action'):
               new_doc['action'] = action_enum.Name(url_rule.action)
            if url_rule.HasField('amount'):
               new_doc['amount'] = url_rule.amount
            policy_doc['url_rules'].append(new_doc)
        for user_agent in policy_pb.user_agents:
            new_doc = dict()
            if user_agent.HasField('name'):
               new_doc['name'] = user_agent.name
            policy_doc['user_agents'].append(new_doc)
        return policy_doc

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

    def __init__(self, doc, version, seeds, robots_txt_manager):
        ''' Initialize from ``doc``, a dict representation of a policy. '''
        if doc['name'].strip() == '':
            _invalid('Policy name cannot be blank')

        self.limits = PolicyLimits(doc.get('limits', {}))
        self.mime_type_rules = PolicyMimeTypeRules(
            doc.get('mime_type_rules', []))
        self.proxy_rules = PolicyProxyRules(doc.get('proxy_rules', []))
        self.robots_txt = PolicyRobotsTxt(doc.get('robots_txt', []),
            robots_txt_manager, self)
        self.url_rules = PolicyUrlRules(doc.get('url_rules', []), seeds)
        self.user_agents = PolicyUserAgents(doc.get('user_agents', []), version)


class PolicyLimits:
    ''' Limits on crawl size/duration. '''

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

    def __init__(self, docs):
        ''' Initialize from ``docs``, a dict representation of MIME rules. '''

        if len(docs) == 0:
            _invalid('At least one MIME type rule is required')

        # Rules are stored as list of tuples: (pattern, match, save)
        self._rules = list()
        max_index = len(docs) - 1
        match_enum = protobuf.shared_pb2.PatternMatch

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

    def __init__(self, docs):
        ''' Initialize from ``docs``, a dict representation of proxy rules. '''

        # Rules are stored as list of tuples: (pattern, match, proxy_type,
        # proxy_url)
        self._rules = list()
        max_index = len(docs) - 1
        match_enum = protobuf.shared_pb2.PatternMatch

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


class PolicyUrlRules:
    ''' Customize link priorities based on URL. '''

    def __init__(self, docs, seeds):
        ''' Initialize from ``docs``, a dict representation of url rules. '''
        if len(docs) == 0:
            _invalid('At least one URL rule is required')

        # Rules are stored as tuples: (pattern, match, action, amount)
        self._rules = list()
        max_index = len(docs) - 1
        seed_domains = {urlparse(seed).hostname for seed in seeds}
        action_enum = protobuf.shared_pb2.PolicyUrlRule.Action
        match_enum = protobuf.shared_pb2.PatternMatch

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
