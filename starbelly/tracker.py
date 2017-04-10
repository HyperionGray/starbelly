import asyncio
from datetime import datetime, timedelta
import logging

import rethinkdb as r

from . import cancel_futures
from .db import AsyncCursorIterator
from .pubsub import PubSub


logger = logging.getLogger(__name__)


class Tracker:
    '''
    Tracks real-time metadata about Starbelly.

    This is focused on crawl status (# successes, # errors, etc.) for now but
    will eventually include things like CPU utilization, disk space, etc.
    '''

    JOB_STATUS_FIELDS = [
        'id', 'name', 'run_state', 'started_at', 'completed_at', 'item_count',
        'http_success_count', 'http_error_count', 'exception_count',
        'http_status_counts',
    ]

    def __init__(self, db_pool):
        ''' Constructor. '''

        self.job_status_changed = PubSub()

        self._db_pool = db_pool
        self._job_statuses = dict()

    def get_all_job_status(self):
        ''' Return the status of all tracked jobs. '''
        return self._job_statuses

    def get_job_status(self, job_id):
        ''' Get status of a single job. '''
        return self._job_statuses[job_id]

    async def run(self):
        ''' Keep track of stats for all running crawl jobs. '''
        logger.info('Tracker is running.')
        self._task = asyncio.Task.current_task()

        try:
            async with self._db_pool.connection() as conn:
                # Get status for incomplete and recently completed jobs. This
                # query can't use an index because RethinkDB doesn't allow nulls
                # in secondary indexes.
                initial_query = (
                    r.table('crawl_job')
                     .filter((r.row['completed_at'].eq(None)) |
                             (r.row['completed_at'] > r.now() - 3600))
                     .pluck(*self.JOB_STATUS_FIELDS)
                )
                cursor = await initial_query.run(conn)
                async for job in AsyncCursorIterator(cursor):
                    job_id = job.pop('id')
                    self._job_statuses[job_id] = job

                # Now track updates to job status. (There's a race between
                # initial state and first update, but that shouldn't be a big
                # problem in practice.)
                change_query = (
                    r.table('crawl_job')
                     .pluck(*self.JOB_STATUS_FIELDS)
                     .changes(squash=True)
                     .pluck('new_val')
                )
                feed = await change_query.run(conn)
                async for change in AsyncCursorIterator(feed):
                    job = change['new_val']
                    if job is None:
                        # TODO handle deletions: ['new_val'] will be None
                        # Need to notify client of job deletion and remove from
                        # tracker
                        continue

                    job_id = job.pop('id')
                    self.job_status_changed.publish(job_id, job)

                    if job['run_state'] in ('pending', 'running'):
                        self._job_statuses[job_id] = job
                    else:
                        self._job_statuses.pop(job_id, None)
        except asyncio.CancelledError:
            self._task = None
            logger.info('Tracker has stopped.')
