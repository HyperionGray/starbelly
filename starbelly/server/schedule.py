from datetime import datetime, timezone
from uuid import UUID

from . import api_handler, InvalidRequestException
from ..schedule import Schedule


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
async def set_schedule(command, response, scheduler, server_db):
    ''' Create or update job schedule metadata. '''
    doc = Schedule.from_pb(command.schedule).to_doc()
    now = datetime.now(timezone.utc)
    schedule_doc = await server_db.set_schedule(doc, now)
    if doc['id']:
        scheduler.remove_schedule(doc['id'])
    else:
        response.new_schedule.schedule_id = UUID(schedule_doc['id']).bytes
    scheduler.add_schedule(schedule_doc)
