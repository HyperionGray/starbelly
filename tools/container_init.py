'''
An entry point for running inside a container, e.g. Docker.

This initializes any external resources (such as config files and database
tables), then it execs the command passed into it.

This is also helpful in development environments if you want to initialize the
database.
'''

import configparser
import logging
import os
import secrets
import shutil
import string
import sys
import time

from rethinkdb import RethinkDB
import trio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from starbelly.config import get_config, get_path


r = RethinkDB()
r.set_loop_type('trio')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('container_init.py')


class ContainerInitException(Exception):
    ''' Indicates a failure to initalize the container. '''


async def connect_db(db_config, nursery):
    '''
    Connect to database as admin (a.k.a. super user).

    Checks for default admin credentials and sets a password if no admin
    password exists.
    '''
    connects_remaining = 10

    while True:
        try:
            conn = await r.connect(
                host=db_config['host'],
                port=db_config['port'],
                user='admin',
                nursery=nursery
            )

            logger.info('Found default admin credentials: setting the admin'
                        ' password. (see conf/local.ini)')

            result = await (
                r.db('rethinkdb')
                 .table('users')
                 .get('admin')
                 .update({'password': db_config['super_password']})
                 .run(conn)
            )

            await conn.close()
        except r.ReqlAuthError:
            # Default credentials didn't work -- this is a good thing.
            break
        except r.ReqlDriverError as e:
            logger.error('Could not connect to RethinkDB: {}'.format(e))
            connects_remaining -= 1
            if connects_remaining > 0:
                logger.error('Will wait 5s and then try to connect again. ({}'
                    ' attempts remaining)'.format(connects_remaining))
                await trio.sleep(5)
            else:
                raise ContainerInitException(
                    'Gave up trying to connect to RethinkDB.'
                )

    try:
        conn = await r.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['super_user'],
            password=db_config['super_password'],
            nursery=nursery
        )
        conn.use(db_config['db'])
    except r.ReqlAuthError as e:
        raise ContainerInitException(
            'RethinkDB authentication failure: {}'.format(e)
        )

    # Hack to allow database to finish initializing:
    await trio.sleep(5)
    logger.info('Connected to RethinkDB.')

    return conn


async def ensure_db(conn, name):
    ''' Create the named database, if it doesn't already exist. '''
    if not await r.db_list().contains(name).run(conn):
        logger.info('Creating DB: {}'.format(name))
        await r.db_create(name).run(conn)
    conn.use(name)


async def ensure_db_fixtures(conn):
    ''' Create all fixtures. '''
    # Crawl policy fixtures.
    user_agent = 'Starbelly/{VERSION} ' \
        '(+https://github.com/hyperiongray/starbelly)'

    if await r.table('policy').count().run(conn) == 0:
        await r.table('policy').insert({
            'created_at': r.now(),
            'updated_at': r.now(),
            'name': 'Broad Crawl',
            'authentication': {
                'enabled': False,
            },
            'limits': {
              'max_items': 1_000_000,
              'max_cost': 3,
            },
            'mime_type_rules': [
              {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
              {'save': False}
            ],
            'proxy_rules': [{}],
            'robots_txt': {
              'usage': 'OBEY'
            },
            'url_normalization': {
                'enabled': True,
                'strip_parameters': ['JSESSIONID', 'PHPSESSID', 'sid'],
            },
            'url_rules': [
              {'action':'ADD', 'amount':1}
            ],
            'user_agents': [
              {'name': user_agent}
            ]
        }).run(conn)

        await r.table('policy').insert({
            'created_at': r.now(),
            'updated_at': r.now(),
            'name': 'Deep Crawl',
            'authentication': {
                'enabled': True,
            },
            'limits': {
              'max_cost': 10,
            },
            'mime_type_rules': [
              {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
              {'save': False}
            ],
            'proxy_rules': [{}],
            'robots_txt': {
              'usage': 'OBEY'
            },
            'url_normalization': {
                'enabled': True,
                'strip_parameters': ['JSESSIONID', 'PHPSESSID', 'sid'],
            },
            'url_rules': [
              {'match': 'MATCHES', 'pattern':'^https?://({SEED_DOMAINS})/',
               'action':'ADD', 'amount':1},
              {'action':'MULTIPLY', 'amount':0}
            ],
            'user_agents': [
              {'name': user_agent}
            ]
        }).run(conn)

    # Global rate limit fixture.
    global_rate_limit_token = b'\x00' * 16

    try:
        global_rate_limit = await (
            r.table('rate_limit')
             .get_all(global_rate_limit_token, index='token')
             .nth(0)
             .run(conn)
        )
    except r.ReqlNonExistenceError:
        logger.info('Creating global rate limit fixture.')
        await r.table('rate_limit').insert({
            'delay': 5.0,
            'name': 'Global Limit',
            'token': global_rate_limit_token,
            'type': 'global',
        }).run(conn)


async def ensure_db_index(conn, table_name, index_name, index_cols=None):
    ''' Create the named index, if it doesn't already exist. '''
    check_index_query = r.table(table_name).index_list().contains(index_name)
    if not await check_index_query.run(conn):
        logger.info('Creating index: {}.{}'.format(table_name, index_name))
        if index_cols is None:
            await r.table(table_name).index_create(index_name).run(conn)
        else:
            await r.table(table_name).index_create(index_name, index_cols) \
                   .run(conn)
        await r.table(table_name).index_wait(index_name).run(conn)

async def ensure_db_table(conn, name, **options):
    ''' Create the named table, if it doesn't already exist. '''
    options = options or dict()
    if not await r.table_list().contains(name).run(conn):
        logger.info('Creating table: {}'.format(name))
        await r.table_create(name, **options).run(conn)


async def ensure_db_user(conn, db_name, user, password):
    '''
    Create the named user with the specified password, if the user doesn't
    already exist.

    The user is created with permissions necessary for the application. If the
    user does exist, the password argument is ignored.
    '''
    user_count = await (
        r.db('rethinkdb')
         .table('users')
         .filter(r.row['id']==user)
         .count()
         .run(conn)
    )

    if user_count == 0:
        logger.info('Creating RethinkDB user: {}'.format(user))
        result = await (
            r.db('rethinkdb')
             .table('users')
             .insert({
                'id': user,
                'password': password,
             })
             .run(conn)
        )

    result = await (
        r.db(db_name)
         .grant(user, {'read': True, 'write': True})
         .run(conn)
    )


def init_config():
    ''' If local.ini does not exist, then create it. '''

    local_ini_path = get_path('conf/local.ini')

    if not local_ini_path.exists():
        logger.info('Creating conf/local.ini')
        template_path = get_path('conf/local.ini.template')
        shutil.copyfile(template_path, local_ini_path)

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read([local_ini_path])

        config['database']['host'] = 'db'
        config['database']['db'] = 'starbelly'
        config['database']['user'] = 'starbelly-app'
        config['database']['password'] = secrets.token_urlsafe(nbytes=15)
        config['database']['super_user'] = 'admin'
        config['database']['super_password'] = secrets.token_urlsafe(nbytes=15)

        with open(local_ini_path, 'w') as local_ini:
            config.write(local_ini)


async def init_db(db_config):
    '''
    Make sure the database and required objects (users, tables, indices) all
    exist.
    '''

    logger.info('Connecting to RethinkDB: {}'.format(db_config['host']))
    async with trio.open_nursery() as nursery:
        conn = await connect_db(db_config, nursery)
        try:
            await r.db_drop('test').run(conn)
        except r.ReqlRuntimeError:
            pass # Already deleted

        db_name = db_config['db']
        await ensure_db(conn, db_name)
        await ensure_db_user(conn, db_name, db_config['user'],
            db_config['password'])
        await ensure_db_table(conn, 'captcha_solver')
        await ensure_db_table(conn, 'crawl_log')
        await ensure_db_index(conn, 'crawl_log', 'job_id')
        await ensure_db_table(conn, 'domain_login', primary_key='domain')
        await ensure_db_table(conn, 'frontier')
        await ensure_db_index(conn, 'frontier', 'cost_index',
            [r.row['job_id'], r.row['in_flight'], r.row['cost']])
        await ensure_db_table(conn, 'job')
        await ensure_db_index(conn, 'job', 'started_at')
        await ensure_db_index(conn, 'job', 'schedule',
            [r.row['schedule_id'], r.row['started_at']])
        await ensure_db_table(conn, 'policy')
        await ensure_db_index(conn, 'policy', 'name')
        await ensure_db_table(conn, 'rate_limit', primary_key='token')
        await ensure_db_index(conn, 'rate_limit', 'name')
        await ensure_db_table(conn, 'response', primary_key='sequence')
        await ensure_db_index(conn, 'response', 'job_sync',
                [r.row['job_id'], r.row['sequence']])
        await ensure_db_table(conn, 'response_body')
        await ensure_db_table(conn, 'robots_txt')
        await ensure_db_index(conn, 'robots_txt', 'url')
        await ensure_db_table(conn, 'schedule')
        await ensure_db_index(conn, 'schedule', 'schedule_name')
        await ensure_db_fixtures(conn)
        await upgrade_schema(conn)
        await conn.close()


async def main():
    logger.info('Initializing container...')
    init_config()
    config = get_config()
    await init_db(config['database'])
    logger.info('Container initialization finished.')

    sys.argv.pop(0)
    if len(sys.argv) > 0:
        logger.info("Exec target process...")
        os.execvp(sys.argv[0], sys.argv)


async def upgrade_schema(conn):
    ''' Make changes to the database schema. '''
    await upgrade_schema_url_normalization_policy(conn)


async def upgrade_schema_url_normalization_policy(conn):
    ''' Add URL normalization policy to policies. '''
    await (
        r.table('policy')
         .filter(lambda p: ~p.has_fields('url_normalization'))
         .update({
             'url_normalization': {
                 'enabled': True,
                 'strip_parameters': ['JSESSIONID', 'PHPSESSID', 'sid'],
             },
         })
         .run(conn)
    )


if __name__ == '__main__':
    try:
        trio.run(main)
    except ContainerInitException as cie:
        logger.error('Container initalization failed: {}'.format(cie))
        sys.exit(1)
