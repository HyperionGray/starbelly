from .handler import handler


@handler
async def delete_job_schedule(server, command, socket):
    ''' Delete a job schedule. '''
    schedule_id = str(UUID(bytes=command.schedule_id))
    async with db_pool.connection() as conn:
        await r.table('job_schedule').get(schedule_id).delete().run(conn)
    self._scheduler.remove_schedule(schedule_id)
    return Response()


@handler
async def get_job_schedule(self, command, socket):
    ''' Get metadata for a job schedule. '''
    schedule_id = str(UUID(bytes=command.schedule_id))
    async with db_pool.connection() as conn:
        doc = await r.table('job_schedule').get(schedule_id).run(conn)
    response = Response()
    if doc is None:
        response.is_success = False
        response.error_message = f'No schedule exists with ID={schedule_id}'
    else:
        pb = response.job_schedule
        Scheduler.doc_to_pb(doc, pb)
    return response


@handler
async def list_job_schedules(self, command, socket):
    ''' Return a list of job schedules. '''
    limit = command.page.limit
    offset = command.page.offset
    schedules = list()
    query = (
        r.table('job_schedule')
         .order_by(index='schedule_name')
         .skip(offset)
         .limit(limit)
    )
    async with db_pool.connection() as conn:
        count = await r.table('job_schedule').count().run(conn)
        cursor = await query.run(conn)
        async for schedule in cursor:
            schedules.append(schedule)
        await cursor.close()
    response = Response()
    response.list_jobs.total = count
    for doc in schedules:
        pb = response.list_job_schedules.job_schedules.add()
        Scheduler.doc_to_pb(doc, pb)
    return response


@handler
async def set_job_schedule(self, command, socket):
    ''' Create or update job schedule metadata. '''
    doc = Scheduler.pb_to_doc(command.job_schedule)
    schedule_id = await set_job_schedule(self._db_pool, doc)
    response = Response()
    if schedule_id is not None:
        response.new_job_schedule.schedule_id = UUID(schedule_id).bytes
    return response
