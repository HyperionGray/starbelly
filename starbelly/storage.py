from binascii import hexlify
import gzip
import hashlib
import logging
import functools

import mimeparse


logger = logging.getLogger(__name__)


class CrawlStorage:
    ''' This class stores crawl items in the database. '''
    def __init__(self, job_id, db_pool, send_channel, receive_channel, policy,
        sequence):
        '''
        Constructor

        :param str job_id: The job to store items for.
        :param db_pool: A RethinkDB connection pool.
        :param starbelly.policy.Policy: A policy to use for determining which
            responses to save.
        :param sequence: An iterator that returns a sequence number for each
            item to be saved.
        '''
        self._job_id = job_id
        self._db_pool = db_pool
        self._send_channel = send_channel
        self._receive_channel = receive_channel
        self._policy = policy
        self._sequence = sequence

    def __repr__(self):
        ''' Put job ID in repr. '''
        return '<CrawlStorage job_id={}>'.format(
            hexlify(self._job_id).decode('ascii')[:8])

    async def run(self):
        '''
        Read items from channel and saves them into the database.

        :returns: This function runs until cancelled.
        '''
        async for response in self._receive_channel:
            await self._save_response(response)
            await self._update_job_stats(response)
            await self._send_channel.send(response)

    async def _save_response(self, response):
        '''
        Save a response to the database.

        :param starbelly.downloader.DownloadResponse response:
        '''
        response_doc = {
            'completed_at': response.completed_at,
            'cost': response.cost,
            'duration': response.duration.total_seconds(),
            'job_id': self.id,
            'started_at': response.started_at,
            'url': response.url,
            'url_can': response.url_can,
        }

        if response.exception is None:
            response_doc['completed_at'] = response.completed_at
            response_doc['content_type'] = response.content_type
            response_doc['is_success'] = response.status_code // 100 == 2
            response_doc['status_code'] = response.status_code
            compress_body = self._should_compress_body(response)

            headers = list()
            for key, value in response.headers.items():
                headers.append(key.upper())
                headers.append(value)
            response_doc['headers'] = headers

            if compress_body:
                body = await trio.run_sync_in_worker_thread(functools.partial(
                    gzip.compress, response.body, compresslevel=6))
            else:
                body = response.body

            body_hash = hashlib.blake2b(body, digest_size=16).digest()
            response_doc['body_id'] = body_hash
            response_body_doc = {
                'id': body_hash,
                'body': body,
                'is_compressed': compress_body,
            }
        else:
            response_doc['exception'] = response.exception
            response_doc['is_success'] = False
            response_body_doc = None

        async with self._db_pool.connection() as conn:
            response_doc['sequence'] = next(self._sequence)
            await r.table('response').insert(response_doc).run(conn)
            if response_body_doc:
                try:
                    await (
                        r.table('response_body')
                         .insert(response_body_doc, conflict='error')
                         .run(conn)
                    )
                except r.RuntimeError:
                    # This response body already exists in the DB.
                    pass

    def _should_compress_body(self, response):
        '''
        Returns true if the response body should be compressed.

        This logic can be amended over time to add additional MIME types that
        should be compressed.

        :param starbelly.downloader.DownloadResponse response:
        '''
        should_compress = False
        type_, subtype, parameters = mimeparse.parse_mime_type(
            response.content_type)
        if type_ == 'text':
            should_compress = True
        elif type_ == 'application' and subtype in ('json', 'pdf'):
            should_compress = True
        return should_compress

    async def _update_job_stats(self, response):
        '''
        Update job stats with this response.

        This function should make an atomic change to the database, e.g. no
        concurrent query should cause a partial read or partial write.

        :param starbelly.downloader.DownloadResponse response:
        '''
        status = str(response.status_code)
        status_first_digit = status[0]
        new_data = {'item_count': r.row['item_count'] + 1}
        self.item_count += 1

        if response.exception is None:
            if 'http_status_counts' not in new_data:
                new_data['http_status_counts'] = {}

            # Increment count for status. (Assume zero if it doesn't exist yet).
            new_data['http_status_counts'][status] = (
                1 + r.branch(
                    r.row['http_status_counts'].has_fields(status),
                    r.row['http_status_counts'][status],
                    0
                )
            )

            if status_first_digit == '2':
                new_data['http_success_count'] = r.row['http_success_count'] + 1
            else:
                new_data['http_error_count'] = r.row['http_error_count'] + 1
        else:
            new_data['exception_count'] = r.row['exception_count'] + 1

        query = r.table('job').get(self.id).update(new_data)

        async with self._db_pool.connection() as conn:
            await query.run(conn)



