import gzip
import hashlib
import logging
import functools

import mimeparse
import soft404
import trio


logger = logging.getLogger(__name__)


def should_compress_body(response):
    '''
    Returns true if the response body should be compressed.

    This logic can be amended over time to add additional MIME types that
    should be compressed.

    :param starbelly.downloader.DownloadResponse response:
    '''
    should_compress = False
    type_, subtype, _ = mimeparse.parse_mime_type(response.content_type)
    if type_ == 'text':
        should_compress = True
    elif type_ == 'application' and subtype in ('json', 'pdf'):
        should_compress = True
    return should_compress


def should_check_soft404(response):
    '''
    Returns true if the response should be checked for soft 404.

    Only check HTML pages with 200 status code.

    :param starbelly.downloader.DownloadResponse response:
    '''
    if response.status_code != 200:
        return False
    type_, subtype, _ = mimeparse.parse_mime_type(response.content_type)
    return type_ == 'text' and subtype == 'html'


def calculate_soft404(body):
    '''
    Calculate the soft 404 probability for a page body.

    :param bytes body: The HTML body of the page.
    :returns: Probability that the page is a soft 404 (0.0 to 1.0).
    :rtype: float
    '''
    try:
        # soft404 expects a string, so decode the body
        html = body.decode('utf-8', errors='ignore')
        return soft404.probability(html)
    except Exception:
        logger.exception('Error calculating soft404 probability')
        return None


class CrawlStorage:
    ''' This class stores crawl items in the database. '''
    def __init__(self, job_id, db, send_channel, receive_channel, policy,
        sequence):
        '''
        Constructor

        :param str job_id: The job to store items for.
        :param starbelly.db.CrawlStorageDb db: Database layer.
        :param starbelly.policy.Policy: A policy to use for determining which
            responses to save.
        :param sequence: An iterator that returns a sequence number for each
            item to be saved.
        '''
        self._job_id = job_id
        self._db = db
        self._send_channel = send_channel
        self._receive_channel = receive_channel
        self._policy = policy
        self._sequence = sequence

    def __repr__(self):
        ''' Put job ID in repr. '''
        return '<CrawlStorage job_id={}>'.format(self._job_id[:8])

    async def run(self):
        '''
        Read items from channel and saves them into the database.

        :returns: This function runs until cancelled.
        '''
        async for response in self._receive_channel:
            await self._save_response(response)
            await self._db.update_job_stats(self._job_id, response)
            await self._send_channel.send(response)

    async def _save_response(self, response):
        '''
        Save a response to the database.

        :param starbelly.downloader.DownloadResponse response:
        '''
        response_doc = {
            'completed_at': response.completed_at,
            'cost': response.cost,
            'duration': response.duration,
            'job_id': self._job_id,
            'started_at': response.started_at,
            'url': response.url.human_repr(),
            'canonical_url': response.canonical_url,
        }

        if response.exception is None:
            response_doc['completed_at'] = response.completed_at
            response_doc['content_type'] = response.content_type
            response_doc['is_success'] = response.status_code // 100 == 2
            response_doc['status_code'] = response.status_code
            compress_body = should_compress_body(response)

            headers = list()
            for key, value in response.headers.items():
                headers.append(key.upper())
                headers.append(value)
            response_doc['headers'] = headers

            body_hash = hashlib.blake2b(response.body, digest_size=16).digest()
            if compress_body:
                body = await trio.run_sync_in_worker_thread(functools.partial(
                    gzip.compress, response.body, compresslevel=6))
            else:
                body = response.body

            response_doc['body_id'] = body_hash
            response_body_doc = {
                'id': body_hash,
                'body': body,
                'is_compressed': compress_body,
            }

            # Check for soft 404
            if should_check_soft404(response):
                soft404_prob = await trio.run_sync_in_worker_thread(
                    calculate_soft404, response.body)
                if soft404_prob is not None:
                    response_doc['soft404_probability'] = soft404_prob
        else:
            response_doc['exception'] = response.exception
            response_doc['is_success'] = False
            response_body_doc = None

        response_doc['sequence'] = next(self._sequence)
        await self._db.save_response(response_doc, response_body_doc)
