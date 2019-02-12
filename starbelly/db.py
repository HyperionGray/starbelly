import logging

from rethinkdb import RethinkDB


logger = logging.getLogger(__name__)
r = RethinkDB()


class ScheduleDb:
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def get_schedule_docs(self):
        ''' Yield schedule database documents. '''
        def latest_job(sched):
            return {'latest_job':
                r.table('job')
                 .order_by(index='schedule')
                 .between((sched['id'], r.minval), (sched['id'], r.maxval))
                 .pluck(['name', 'run_state', 'started_at', 'completed_at'])
                 .nth(-1)
                 .default(None)
            }

        async with self._db_pool.connection() as conn:
            cursor = await r.table('schedule').merge(latest_job).run(conn)
            async with cursor:
                async for schedule_doc in cursor:
                    yield schedule_doc

    async def update_job_count(self, schedule_id, job_count):
        '''
        Update the job count for a given schedule.

        :param str schedule_id: The ID of the schedule to update.
        :param int job_count: The new job count to store.
        '''
        update_query = r.table('schedule').get(schedule_id).update({
            'job_count': job_count})
        async with self._db_pool.connection() as conn:
            await update_query.run(conn)
