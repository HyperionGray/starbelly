'''
An entry point for running inside a container, e.g. Docker.

This initializes any external resources (such as config files and database
tables), then it execs the command passed into it.
'''

import configparser
import logging
import os
import secrets
import shutil
import string
import sys
import time

import rethinkdb as r

from . import get_path
from .config import get_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('container_init')


class ContainerInitException(Exception):
    ''' Indicates a failure to initalize the container. '''



def connect_db(db_config):
    '''
    Connect to database as admin (a.k.a. super user).

    Checks for default admin credentials and sets a password if no admin
    password exists.
    '''

    connects_remaining = 10

    while True:
        try:
            conn = r.connect(
                host=db_config['host'],
                port=db_config['port'],
                user='admin'
            )

            logger.info('Found default admin credentials: setting the admin'
                        ' password. (see conf/local.ini)')

            result = (
                r.db('rethinkdb')
                 .table('users')
                 .get('admin')
                 .update({'password': db_config['super_password']})
                 .run(conn)
            )

            conn.close()
        except r.ReqlAuthError:
            # Default credentials didn't work -- this is a good thing.
            break
        except r.ReqlDriverError as e:
            logger.error('Could not connect to RethinkDB: {}'.format(e))
            connects_remaining -= 1
            if connects_remaining > 0:
                logger.error('Will wait 5s and then try to connect again. ({}'
                    ' attempts remaining)'.format(connects_remaining))
                time.sleep(5)
            else:
                raise ContainerInitException(
                    'Gave up trying to connect to RethinkDB.'
                )

    try:
        conn = r.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['super_user'],
            password=db_config['super_password']
        )
        conn.use(db_config['db'])
    except r.ReqlAuthError as e:
        raise ContainerInitException(
            'RethinkDB authentication failure: {}'.format(e)
        )

    logger.info('Connected to RethinkDB.')

    return conn

def ensure_db(conn, name):
    ''' Create the named database, if it doesn't already exist. '''
    if not r.db_list().contains(name).run(conn):
        logger.info('Creating DB: {}'.format(name))
        r.db_create(name).run(conn)
    conn.use(name)


def ensure_db_index(conn, table_name, index_name, index_cols=None):
    ''' Create the named index, if it doesn't already exist. '''
    if not r.table(table_name).index_list().contains(index_name).run(conn):
        logger.info('Creating index: {}.{}'.format(table_name, index_name))
        if index_cols is None:
            r.table(table_name).index_create(index_name).run(conn)
        else:
            r.table(table_name).index_create(index_name, index_cols).run(conn)


def ensure_db_table(conn, name):
    ''' Create the named table, if it doesn't already exist. '''
    if not r.table_list().contains(name).run(conn):
        logger.info('Creating table: {}'.format(name))
        r.table_create(name).run(conn)


def ensure_db_user(conn, db_name, user, password):
    '''
    Create the named user with the specified password, if the user doesn't
    already exist.

    The user is created with permissions necessary for the application. If the
    user does exist, the password argument is ignored.
    '''
    user_count = (
        r.db('rethinkdb')
         .table('users')
         .filter(r.row['id']==user)
         .count()
         .run(conn)
    )

    if user_count == 0:
        logger.info('Creating RethinkDB user: {}'.format(user))
        result = (
            r.db('rethinkdb')
             .table('users')
             .insert({
                'id': user,
                'password': password,
             })
             .run(conn)
        )
        result = (
            r.db(db_name)
             .grant(user, {'read': True, 'write': True})
             .run(conn)
        )


def init_config():
    ''' If local.ini does not exist, then create it. '''

    local_ini_path = get_path('conf/local.ini')

    if not os.path.exists(local_ini_path):
        logger.info('Creating conf/local.ini')
        template_path = get_path('conf/local.ini.template')
        shutil.copyfile(template_path, local_ini_path)

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read([local_ini_path])

        config['database']['host'] = 'starbelly-dev-db'
        config['database']['db'] = 'starbelly'
        config['database']['user'] = 'starbelly-app'
        config['database']['password'] = random_password(length=20)
        config['database']['super_user'] = 'admin'
        config['database']['super_password'] = random_password(length=20)

        with open(local_ini_path, 'w') as local_ini:
            config.write(local_ini)


def init_db(db_config):
    '''
    Make sure the database and required objects (users, tables, indices) all
    exist.
    '''

    logger.info('Connecting to RethinkDB: {}'.format(db_config['host']))
    conn = connect_db(db_config)

    try:
        r.db_drop('test').run(conn)
    except r.ReqlRuntimeError:
        pass # Already deleted

    db_name = db_config['db']
    ensure_db(conn, db_name)
    ensure_db_user(conn, db_name, db_config['user'], db_config['password'])
    ensure_db_table(conn, 'crawl_item')
    ensure_db_index(conn, 'crawl_item', 'sync_index',
        [r.row['job_id'], r.row['insert_sequence']])
    ensure_db_table(conn, 'crawl_job')
    ensure_db_index(conn, 'crawl_job', 'run_state')
    ensure_db_table(conn, 'crawl_frontier')
    ensure_db_index(conn, 'crawl_frontier', 'cost_index',
        [r.row['job_id'], r.row['cost']])
    conn.close()


def main():
    logger.info('Initializing container...')
    init_config()
    config = get_config()
    init_db(config['database'])
    logger.info('Container initialization finished.')

    sys.argv.pop(0)
    if len(sys.argv) > 0:
        logger.info("Exec target process...")
        os.execvp(sys.argv[0], sys.argv)
        print(cmd, sys.argv)


def random_password(length):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


if __name__ == '__main__':
    try:
        main()
    except ContainerInitException as cie:
        logging.error('Container initalization failed: {}'.format(cie))
        sys.exit(1)
