from .handler import handler


@handler
async def delete_domain_login(server, command, socket):
    ''' Delete a domain login and all of its users. '''
    if command.HasField('domain'):
        domain = command.domain
    else:
        raise InvalidRequestException('domain is required.')

    async with self._db_pool.connection() as conn:
        await (
            r.table('domain_login')
             .get(domain)
             .delete()
             .run(conn)
        )

    return Response()


@handler
async def get_domain_login(self, command, socket):
    ''' Get a domain login. '''
    if not command.HasField('domain'):
        raise InvalidRequestException('domain is required.')

    domain = command.domain
    async with self._db_pool.connection() as conn:
        count = await r.table('domain_login').count().run(conn)
        domain_login = await (
            r.table('domain_login')
             .get(domain)
             .run(conn)
        )

    if domain_login is None:
        raise InvalidRequestException('No domain credentials found for'
            ' domain={}'.format(domain))

    response = Response()
    response.domain_login.domain = domain_login['domain']
    response.domain_login.login_url = domain_login['login_url']
    if domain_login['login_test'] is not None:
        response.domain_login.login_test = domain_login['login_test']
    response.domain_login.auth_count = len(domain_login['users'])

    for user in domain_login['users']:
        dl_user = response.domain_login.users.add()
        dl_user.username = user['username']
        dl_user.password = user['password']
        dl_user.working = user['working']

    return response


@handler
async def list_domain_logins(self, command, socket):
    ''' Return a list of domain logins. '''
    limit = command.page.limit
    skip = command.page.offset

    async with self._db_pool.connection() as conn:
        count = await r.table('domain_login').count().run(conn)
        cursor = await (
            r.table('domain_login')
             .order_by(index='domain')
             .skip(skip)
             .limit(limit)
             .run(conn)
        )

    response = Response()
    response.list_domain_logins.total = count

    async for domain_doc in cursor:
        dl = response.list_domain_logins.logins.add()
        dl.domain = domain_doc['domain']
        dl.login_url = domain_doc['login_url']
        if domain_doc['login_test'] is not None:
            dl.login_test = domain_doc['login_test']
        # Not very efficient way to count users, but don't know a better
        # way...
        dl.auth_count = len(domain_doc['users'])

    return response


@handler
async def set_domain_login(self, command, socket):
    ''' Create or update a domain login. '''
    domain_login = command.login

    if not domain_login.HasField('domain'):
        raise InvalidRequestException('domain is required.')

    domain = domain_login.domain
    async with self._db_pool.connection() as conn:
        doc = await (
            r.table('domain_login')
             .get(domain)
             .run(conn)
        )

    if doc is None:
        if not domain_login.HasField('login_url'):
            raise InvalidRequestException('login_url is required to'
                ' create a domain login.')
        doc = {
            'domain': domain,
            'login_url': domain_login.login_url,
            'login_test': None,
        }

    if domain_login.HasField('login_url'):
        doc['login_url'] = domain_login.login_url

    if domain_login.HasField('login_test'):
        doc['login_test'] = domain_login.login_test

    doc['users'] = list()

    for user in domain_login.users:
        doc['users'].append({
            'username': user.username,
            'password': user.password,
            'working': user.working,
        })

    async with self._db_pool.connection() as conn:
        # replace() is supposed to upsert, but for some reason it doesn't,
        # so I'm calling insert() explicitly.
        response = await (
            r.table('domain_login')
             .replace(doc)
             .run(conn)
        )
        if response['replaced'] == 0:
            await (
                r.table('domain_login')
                 .insert(doc)
                 .run(conn)
            )

    return Response()
