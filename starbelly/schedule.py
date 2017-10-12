import asyncio
import logging
from uuid import UUID

import protobuf.shared_pb2
import rethinkdb as r


logger = logging.getLogger(__name__)


class ScheduleValidationError(Exception):
    ''' Custom error for job schedule validation. '''


class Scheduler:
    ''' Implements job scheduling. '''
    def __init__(self, db_pool):
        ''' Constructor. '''
        self._db_pool = db_pool

    async def delete_job_schedule(self, schedule_id):
        ''' Delete a job schedule from the database. '''
        async with self._db_pool.connection() as conn:
            await r.table('job_schedule').get(schedule_id).delete().run(conn)

    @staticmethod
    def doc_to_pb(doc, pb):
        ''' Convert database document schedule to protobuf. '''
        pb.schedule_id = UUID(doc['id']).bytes
        pb.created_at = doc['created_at'].isoformat()
        pb.updated_at = doc['updated_at'].isoformat()
        pb.enabled = doc['enabled']
        pb.time_unit = protobuf.shared_pb2.JobScheduleTimeUnit.Value(
            doc['time_unit'])
        pb.num_units = doc['num_units']
        pb.timing = protobuf.shared_pb2.JobScheduleTiming.Value(
            doc['timing'])
        pb.schedule_name = doc['schedule_name']
        pb.job_name = doc['job_name']
        for seed in doc['seeds']:
            pb.seeds.append(seed)
        pb.policy_id = UUID(doc['policy_id']).bytes
        for tag in doc['tags']:
            pb.tag_list.tags.append(tag)
        if 'latest_job_id' in doc:
            pb.latest_job_id = UUID(doc['latest_job_id']).bytes

    async def get_job_schedule(self, schedule_id):
        ''' Get a job schedule from the database. '''
        async with self._db_pool.connection() as conn:
            return await r.table('job_schedule').get(schedule_id).run(conn)

    async def list_job_schedules(self, limit, offset):
        ''' List job schedules in the database. '''
        schedules = list()
        query = (
            r.table('job_schedule')
             .order_by(index='schedule_name')
             .skip(offset)
             .limit(limit)
        )
        async with self._db_pool.connection() as conn:
            count = await r.table('job_schedule').count().run(conn)
            cursor = await query.run(conn)
            async for schedule in cursor:
                schedules.append(schedule)
            await cursor.close()
        return count, schedules

    @staticmethod
    def pb_to_doc(pb):
        ''' Convert a protobuf schedule to a database document. '''
        if pb.num_units <= 0:
            raise ScheduleValidationError('Time units must be positive')

        try:
            pb.job_name.format(COUNT=0, TIME='1506813136',
                DATE='2017-09-30T19:12:59.869751')
        except KeyError:
            raise ScheduleValidationError('Invalid variable in job name:'
                ' COUNT, DATE, & TIME are allowed.')
        except:
            raise ScheduleValidationError('Invalid job name')

        doc = {
            'enabled': pb.enabled,
            'time_unit': protobuf.shared_pb2.JobScheduleTimeUnit.Name(
                pb.time_unit),
            'num_units': pb.num_units,
            'timing': protobuf.shared_pb2.JobScheduleTiming.Name(pb.timing),
            'schedule_name': pb.schedule_name,
            'job_name': pb.job_name,
            'seeds': [seed for seed in pb.seeds],
            'policy_id': str(UUID(bytes=pb.policy_id)),
            'tags': [tag for tag in pb.tag_list.tags],
        }

        if pb.HasField('schedule_id'):
            doc['id'] = str(UUID(bytes=pb.schedule_id))
        if pb.HasField('latest_job_id'):
            doc['latest_job_id'] = str(UUID(bytes=pb.latest_job_id))

        return doc

    async def run(self):
        ''' Run the schedule. '''
        while True:
            await asyncio.sleep(1)

    async def set_job_schedule(self, doc):
        ''' Create or update a job schedule from a database document. '''
        async with self._db_pool.connection() as conn:
            if 'id' not in doc:
                # Create policy
                doc['created_at'] = r.now()
                doc['updated_at'] = r.now()
                result = await r.table('job_schedule').insert(doc).run(conn)
                schedule_id = result['generated_keys'][0]
            else:
                doc['updated_at'] = r.now()
                await (
                    r.table('job_schedule')
                     .get(doc['id'])
                     .update(doc)
                     .run(conn)
                )
                schedule_id = None
        return schedule_id
