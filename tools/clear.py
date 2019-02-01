'''
Clears data from the database. Only intended for developers who want to clear
their environment and start from scratch.
'''
import logging
import os
import sys

from rethinkdb import RethinkDB
import trio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import tools
from starbelly.config import get_config


r = RethinkDB()
r.set_loop_type('trio')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('clear.py')


async def clear(conn, table):
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

    await query.delete().run(conn)


async def main():
    db_config = get_config()['database']
    async with trio.open_nursery() as nursery:
        conn = await r.connect(
            host=db_config['host'],
            port=db_config['port'],
            db=db_config['db'],
            user=db_config['user'],
            password=db_config['password'],
            nursery=nursery
        )
        await clear(conn, 'captcha_solver')
        await clear(conn, 'domain_login')
        await clear(conn, 'frontier')
        await clear(conn, 'job')
        await clear(conn, 'job_schedule')
        await clear(conn, 'policy')
        await clear(conn, 'rate_limit')
        await clear(conn, 'response')
        await clear(conn, 'response_body')
        await clear(conn, 'robots_txt')
        await conn.close()


if __name__ == '__main__':
    trio.run(main)
