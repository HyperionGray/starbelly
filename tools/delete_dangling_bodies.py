'''
Response bodies are deduplicated and stored separate from response headers. When
crawls are deleted, the response bodies remain behind. This script finds
"dangling" response bodies—i.e. bodies that don't match to any existing
response—and deletes them.

This is a slow process, since it involves looking at every single response body.
'''
import logging
import os
import sys

from rethinkdb import RethinkDB

import trio

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from starbelly.config import get_config


r = RethinkDB()
r.set_loop_type('trio')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('clear.py')


async def clear_dangling_response_bodies(conn):
    '''
    Response bodies are deduplicated and stored in a separate table from
    response metadata. When a job is deleted, only the response metadata is
    removed. This method finds response bodies that are dangling (not
    referred to by any existing response) and removes them.

    Note: this is a very slow operation because it has to iterate over all
    existing response bodies. This should only be run periodically.

    :param db_pool: A RethinkDB connection pool.
    '''
    def dangling(body):
        responses = r.table('response').get_all(body['id'], index='body_id')
        return  responses.count().eq(0)

    await (
        r.table('response_body')
         .order_by('id')
         .filter(dangling)
         .delete()
         .run(conn)
    )


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
        await clear_dangling_response_bodies(conn)


if __name__ == '__main__':
    trio.run(main)
