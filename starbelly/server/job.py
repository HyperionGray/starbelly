from .handler import handler

# TODO: i moved thsi code from crawl manager to here. these methods don't act
# on internal crawl state, so it makes more sense to put them here

    # async def delete_job(self, job_id):
    #     '''
    #     Delete a job, including all of its responses.

    #     Note that response _bodies_ are deduplicated and stored in a separate
    #     table. Those bodies are periodically cleaned up and removed by a
    #     a separate task.

    #     :param bytes job_id: The ID of the job to delete.
    #     '''
    #     job_query = r.table('job').get(job_id).pluck('run_state')
    #     delete_job_query = r.table('job').get(job_id).delete()
    #     delete_items_query = (
    #         r.table('response')
    #          .between((job_id, r.minval),
    #                   (job_id, r.maxval),
    #                   index='sync_index')
    #          .delete()
    #     )

    #     async with self._db_pool.connection() as conn:
    #         job = await job_query.run(conn)

    #         if job['run_state'] not in ('completed', 'cancelled'):
    #             raise Exception('Can only delete cancelled or completed jobs.')

    #         await delete_items_query.run(conn)
    #         await delete_job_query.run(conn)

    # async def get_job(self, job_id):
    #     '''
    #     Get data for the specified job.

    #     :param bytes job_id: The ID of the job to get.
    #     :returns: Database document.
    #     :rtype: dict or None
    #     '''
    #     query = r.table('job').get(job_id).without('frontier_seen')
    #     async with self._db_pool.connection() as conn:
    #         try:
    #             job = await query.run(conn)
    #         except rethinkdb.errors.ReqlNonExistenceError:
    #             job = None
    #     return job

    # async def get_job_items(self, job_id, include_success, include_error,
    #                         include_exception, limit, offset):
    #     '''
    #     List the items downloaded by a job.

    #     :param bytes job_id: The ID of the job to list.
    #     :param bool include_success: If True, include items that were
    #         successfully downloaded.
    #     :param bool include_error: If True, include items that resulted in an
    #         HTTP error.
    #     :param bool include_exception: If True, include items that resulted in
    #         an exception.
    #     :param int limit: The maximum number of items to return.
    #     :param int offeset: The number of rows to skip.
    #     :returns: (total count, item list)
    #     :rtype: tuple
    #     '''
    #     items = list()
    #     filters = []

    #     if include_success:
    #         filters.append(r.row['is_success'] == True)

    #     if include_error:
    #         filters.append((r.row['is_success'] == False) &
    #                        (~r.row.has_fields('exception')))

    #     if include_exception:
    #         filters.append((r.row['is_success'] == False) &
    #                        (r.row.has_fields('exception')))

    #     if len(filters) == 0:
    #         raise Exception('You must set at least one include_* flag to true.')

    #     def get_body(item):
    #         return {
    #             'join': r.branch(
    #                 item.has_fields('body_id'),
    #                 r.table('response_body').get(item['body_id']),
    #                 None
    #             )
    #         }

    #     base_query = (
    #         r.table('response')
    #          .order_by(index='job_sync')
    #          .between((job_id, r.minval),
    #                   (job_id, r.maxval))
    #          .filter(r.or_(*filters))
    #     )

    #     query = (
    #          base_query
    #          .skip(offset)
    #          .limit(limit)
    #          .merge(get_body)
    #          .without('body_id')
    #     )

    #     async with self._db_pool.connection() as conn:
    #         total_count = await base_query.count().run(conn)
    #         cursor = await query.run(conn)
    #         async for item in cursor:
    #             items.append(item)
    #         await cursor.close()

    #     return total_count, items

    # async def list_jobs(self, limit, offset, started_after, tag, schedule_id):
    #     '''
    #     List up to `limit` jobs, starting at row number `offset`, ordered by
    #     start date.
    #     '''
    #     query = r.table('job')

    #     if started_after is not None:
    #         query = query.between(started_after, r.maxval, index='started_at')

    #     # Have to use order_by() before filter().
    #     query = query.order_by(index=r.desc('started_at'))

    #     if tag is not None:
    #         query = query.filter(r.row['tags'].contains(tag))

    #     if schedule_id is not None:
    #         query = query.filter({'schedule_id': schedule_id})

    #     async with self._db_pool.connection() as conn:
    #         count = await query.count().run(conn)

    #     query = (
    #         query
    #         .without('frontier_seen')
    #         .skip(offset)
    #         .limit(limit)
    #     )

    #     jobs = list()

    #     async with self._db_pool.connection() as conn:
    #         cursor = await query.run(conn)
    #         async for job in cursor:
    #             jobs.append(job)
    #         await cursor.close()

    #     return count, jobs

    # async def update_job(self, job_id, name, tags):
    #     ''' Update job metadata. '''
    #     update = dict()

    #     if name is not None:
    #         update['name'] = name
    #     if tags is not None:
    #         update['tags'] = tags

    #     if len(update) > 0:
    #         async with self._db_pool.connection() as conn:
    #             await r.table('job').get(job_id).update(update).run(conn)


@handler
async def delete_job(self, command, socket):
    ''' Delete a job. '''
    job_id = str(UUID(bytes=command.job_id))
    await self._crawl_manager.delete_job(job_id)
    return Response()


@handler
async def get_job(self, command, socket):
    ''' Get status for a single job. '''
    job_id = str(UUID(bytes=command.job_id))
    job_doc = await self._crawl_manager.get_job(job_id)
    response = Response()
    if job_doc is None:
        response.is_success = False
        response.error_message = f'No job exists with ID={job_id}'
    else:
        job = response.job
        job.job_id = UUID(job_doc['id']).bytes
        for seed in job_doc['seeds']:
            job.seeds.append(seed)
        for tag in job_doc['tags']:
            job.tag_list.tags.append(tag)
        Policy.convert_doc_to_pb(job_doc['policy'], job.policy)
        job.name = job_doc['name']
        job.item_count = job_doc['item_count']
        job.http_success_count = job_doc['http_success_count']
        job.http_error_count = job_doc['http_error_count']
        job.exception_count = job_doc['exception_count']
        job.started_at = job_doc['started_at'].isoformat()
        if job_doc['completed_at'] is not None:
            job.completed_at = job_doc['completed_at'].isoformat()
        run_state = job_doc['run_state'].upper()
        job.run_state = protobuf.shared_pb2.JobRunState.Value(run_state)
        http_status_counts = job_doc['http_status_counts']
        for status_code, count in http_status_counts.items():
            job.http_status_counts[int(status_code)] = count
    return response


@handler
async def get_job_items(self, command, socket):
    ''' Get a page of items (crawl responses) from a job. '''
    job_id = str(UUID(bytes=command.job_id))
    limit = command.page.limit
    offset = command.page.offset
    total_items, item_docs = await self._crawl_manager.get_job_items(
        job_id, command.include_success, command.include_error,
        command.include_exception, limit, offset)
    response = Response()
    response.list_items.total = total_items
    compression_ok = command.compression_ok
    for item_doc in item_docs:
        item = response.list_items.items.add()

        if item_doc['join'] is None:
            item.is_compressed = False
        elif item_doc['join']['is_compressed'] and not compression_ok:
            item.body = gzip.decompress(item_doc['join']['body'])
            item.is_compressed = False
        else:
            item.body = item_doc['join']['body']
            item.is_compressed = item_doc['join']['is_compressed']
        if 'content_type' in item_doc:
            item.content_type = item_doc['content_type']
        if 'exception' in item_doc:
            item.exception = item_doc['exception']
        if 'status_code' in item_doc:
            item.status_code = item_doc['status_code']
        header_iter = iter(item_doc.get('headers', []))
        for key in header_iter:
            value = next(header_iter)
            header = item.headers.add()
            header.key = key
            header.value = value
        item.cost = item_doc['cost']
        item.job_id = UUID(item_doc['job_id']).bytes
        item.completed_at = item_doc['completed_at'].isoformat()
        item.started_at = item_doc['started_at'].isoformat()
        item.duration = item_doc['duration']
        item.url = item_doc['url']
        item.url_can = item_doc['url_can']
        item.is_success = item_doc['is_success']
    return response


@handler
async def list_jobs(self, command, socket):
    ''' Return a list of jobs. '''
    limit = command.page.limit
    offset = command.page.offset
    if command.HasField('started_after'):
        started_after = dateutil.parser.parse(command.started_after)
    else:
        started_after = None
    tag = command.tag if command.HasField('tag') else None
    schedule_id = str(UUID(bytes=command.schedule_id)) if \
        command.HasField('schedule_id') else None
    count, job_docs = await self._crawl_manager.list_jobs(limit, offset,
        started_after, tag, schedule_id)

    response = Response()
    response.list_jobs.total = count

    for job_doc in job_docs:
        job = response.list_jobs.jobs.add()
        job.job_id = UUID(job_doc['id']).bytes
        job.name = job_doc['name']
        for seed in job_doc['seeds']:
            job.seeds.append(seed)
        for tag in job_doc['tags']:
            job.tag_list.tags.append(tag)
        job.item_count = job_doc['item_count']
        job.http_success_count = job_doc['http_success_count']
        job.http_error_count = job_doc['http_error_count']
        job.exception_count = job_doc['exception_count']
        job.started_at = job_doc['started_at'].isoformat()
        if job_doc['completed_at'] is not None:
            job.completed_at = job_doc['completed_at'].isoformat()
        run_state = job_doc['run_state'].upper()
        job.run_state = protobuf.shared_pb2.JobRunState \
            .Value(run_state)
        http_status_counts = job_doc['http_status_counts']
        for status_code, count in http_status_counts.items():
            job.http_status_counts[int(status_code)] = count

    return response


@handler
async def set_job(self, command, socket):
    ''' Create or update job metadata. '''
    #TODO
    # Maybe should have separate commands like pause, cancel, start ?
    # A littler clearer than just "set".
    if command.HasField('tag_list'):
        tags = [t.strip() for t in command.tag_list.tags]
    else:
        tags = None

    if command.HasField('job_id'):
        # Update state of existing job.
        job_id = str(UUID(bytes=command.job_id))
        name = command.name if command.HasField('name') else None
        await self._crawl_manager.update_job(job_id, name, tags)

        if command.HasField('run_state'):
            run_state = command.run_state
            if run_state == protobuf.shared_pb2.CANCELLED:
                await self._crawl_manager.cancel_job(job_id)
            elif run_state == protobuf.shared_pb2.PAUSED:
                await self._crawl_manager.pause_job(job_id)
            elif run_state == protobuf.shared_pb2.RUNNING:
                await self._crawl_manager.resume_job(job_id)
            else:
                raise Exception('Not allowed to set job run state: {}'
                    .format(run_state))

        response = Response()
    else:
        # Create new job.
        name = command.name
        policy_id = str(UUID(bytes=command.policy_id))
        seeds = [s.strip() for s in command.seeds]
        tags = tags or []

        if name.strip() == '':
            url = urlparse(seeds[0])
            name = url.hostname
            if len(seeds) > 1:
                name += '& {} more'.format(len(seeds) - 1)

        if command.run_state != protobuf.shared_pb2.RUNNING:
            raise InvalidRequestException(
                'New job state must be set to RUNNING')

        job_id = await self._crawl_manager.start_job(seeds, policy_id, name,
            tags)
        response = Response()
        response.new_job.job_id = UUID(job_id).bytes

    return response
