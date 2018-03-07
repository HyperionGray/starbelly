'''
Clears data from the database. Useful as a dev tool:

    python3 -m starbelly.clear
'''
import logging

import rethinkdb as r

from .config import get_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('clear')


def clear(conn, table):
    logger.info('Clearing table %s', table)
    query = r.table(table)

    if table == 'policy':
        # Exclude built-in policies.
        query = query.filter(
            (r.row['name'] != 'Broad Crawl') &
            (r.row['name'] != 'Deep Crawl')
        )
    elif table == 'rate_limit':
        # Exclude global rate limit.
        query = query.filter(r.row['type'] != 'global')

    query.delete().run(conn)


def main():
    db_config = get_config()['database']
    conn = r.connect(
        host=db_config['host'],
        port=db_config['port'],
        db=db_config['db'],
        user=db_config['user'],
        password=db_config['password'],
    )
    clear(conn, 'captcha_solver')
    clear(conn, 'domain_login')
    clear(conn, 'extraction_queue')
    clear(conn, 'frontier')
    clear(conn, 'job')
    clear(conn, 'job_schedule')
    clear(conn, 'policy')
    clear(conn, 'rate_limit')
    clear(conn, 'response')
    clear(conn, 'response_body')
    clear(conn, 'robots_txt')
    conn.close()


if __name__ == '__main__':
    main()
