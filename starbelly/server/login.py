from . import api_handler, InvalidRequestException


@api_handler
async def delete_domain_login(command, server_db):
    ''' Delete a domain login and all of its users. '''
    await server_db.delete_domain_login(command.domain)


@api_handler
async def get_domain_login(command, response, server_db):
    ''' Get a domain login. '''
    domain = command.domain
    domain_login = await server_db.get_domain_login(domain)
    if domain_login is None:
        raise InvalidRequestException('No domain credentials found for'
            ' domain={}'.format(domain))
    response.domain_login.domain = domain_login['domain']
    response.domain_login.login_url = domain_login['login_url']
    if domain_login['login_test'] is not None:
        response.domain_login.login_test = domain_login['login_test']

    for user in domain_login['users']:
        dl_user = response.domain_login.users.add()
        dl_user.username = user['username']
        dl_user.password = user['password']
        dl_user.working = user['working']


@api_handler
async def list_domain_logins(command, response, server_db):
    ''' Return a list of domain logins. '''
    limit = command.page.limit
    offset = command.page.offset
    count, docs = await server_db.list_domain_logins(limit, offset)
    response.list_domain_logins.total = count
    for doc in docs:
        dl = response.list_domain_logins.logins.add()
        dl.domain = doc['domain']
        dl.login_url = doc['login_url']
        if doc['login_test'] is not None:
            dl.login_test = doc['login_test']
        for user_doc in doc['users']:
            user = dl.users.add()
            user.username = user_doc['username']
            user.password = user_doc['password']
            user.working = user_doc['working']


@api_handler
async def set_domain_login(command, server_db):
    ''' Create or update a domain login. '''
    domain_login = command.login

    if not domain_login.HasField('domain'):
        raise InvalidRequestException('domain is required.')

    domain = domain_login.domain
    doc = await server_db.get_domain_login(domain)
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

    await server_db.set_domain_login(doc)
