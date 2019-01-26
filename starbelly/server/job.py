from .handler import handler

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
