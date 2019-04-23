from datetime import datetime, timezone
from uuid import UUID

from . import api_handler
from ..schedule import Schedule
from ..starbelly_pb2 import JobRunState as PbRunState


@api_handler
async def delete_schedule(command, scheduler, server_db):
    ''' Delete a job schedule. '''
    schedule_id = str(UUID(bytes=command.schedule_id))
    await server_db.delete_schedule(schedule_id)
    scheduler.remove_schedule(schedule_id)


@api_handler
async def get_schedule(command, response, server_db):
    ''' Get metadata for a job schedule. '''
    schedule_id = str(UUID(bytes=command.schedule_id))
    doc = await server_db.get_schedule(schedule_id)
    if doc is None:
        response.is_success = False
        response.error_message = f'No schedule exists with ID={schedule_id}'
    else:
        pb = response.schedule
        Schedule.from_doc(doc).to_pb(pb)


@api_handler
async def list_schedules(command, response, server_db):
    ''' Return a list of job schedules. '''
    limit = command.page.limit
    offset = command.page.offset
    count, schedules = await server_db.list_schedules(limit, offset)
    response.list_schedules.total = count
    for doc in schedules:
        pb = response.list_schedules.schedules.add()
        Schedule.from_doc(doc).to_pb(pb)


@api_handler
async def list_schedule_jobs(command, response, server_db):
    ''' Return a list of job schedules. '''
    schedule_id = str(UUID(bytes=command.schedule_id))
    limit = command.page.limit
    offset = command.page.offset
    count, jobs = await server_db.list_schedule_jobs(schedule_id, limit, offset)
    response.list_schedule_jobs.total = count
    for job_doc in jobs:
        job = response.list_schedule_jobs.jobs.add()
        job.job_id = UUID(job_doc['id']).bytes
        job.name = job_doc['name']
        for seed in job_doc['seeds']:
            job.seeds.append(seed)
        for tag in job_doc['tags']:
            job.tags.append(tag)
        job.item_count = job_doc['item_count']
        job.http_success_count = job_doc['http_success_count']
        job.http_error_count = job_doc['http_error_count']
        job.exception_count = job_doc['exception_count']
        job.started_at = job_doc['started_at'].isoformat()
        if job_doc['completed_at'] is not None:
            job.completed_at = job_doc['completed_at'].isoformat()
        run_state = job_doc['run_state'].upper()
        job.run_state = PbRunState.Value(run_state)
        http_status_counts = job_doc['http_status_counts']
        for status_code, count in http_status_counts.items():
            job.http_status_counts[int(status_code)] = count


@api_handler
async def set_schedule(command, response, scheduler, server_db):
    ''' Create or update job schedule metadata. '''
    doc = Schedule.from_pb(command.schedule).to_doc()
    now = datetime.now(timezone.utc)
    schedule_id = await server_db.set_schedule(doc, now)
    if schedule_id:
        response.new_schedule.schedule_id = UUID(schedule_id).bytes
    else:
        schedule_id = str(UUID(bytes=command.schedule.schedule_id))
    scheduler.remove_schedule(schedule_id)
    if command.schedule.enabled:
        schedule_doc = await server_db.get_schedule(schedule_id)
        job_docs = await server_db.list_schedule_jobs(schedule_id, limit=1,
            offset=0)
        try:
            latest_job_doc = job_docs[0]
        except IndexError:
            latest_job_doc = None
        scheduler.add_schedule(schedule_doc, latest_job_doc)
