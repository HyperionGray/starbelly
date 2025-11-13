import gzip
import logging
from uuid import UUID
from yarl import URL

import dateutil.parser

from . import api_handler, InvalidRequestException
from ..policy import Policy
from ..starbelly_pb2 import JobRunState as PbRunState


logger = logging.getLogger(__name__)


@api_handler
async def delete_job(command, server_db, stats_tracker):
    """ Delete a job. """
    job_id = str(UUID(bytes=command.job_id))
    await server_db.delete_job(job_id)
    stats_tracker.delete_job(job_id)


@api_handler
async def get_job(command, response, server_db):
    """ Get status for a single job. """
    job_id = str(UUID(bytes=command.job_id))
    job_doc = await server_db.get_job(job_id)
    if not job_doc:
        raise InvalidRequestException(f"No job exists with ID={job_id}")

    job = response.job
    job.job_id = UUID(job_doc["id"]).bytes
    for seed in job_doc["seeds"]:
        job.seeds.append(seed)
    for tag in job_doc["tags"]:
        job.tags.append(tag)
    Policy.convert_doc_to_pb(job_doc["policy"], job.policy)
    job.name = job_doc["name"]
    job.item_count = job_doc["item_count"]
    job.http_success_count = job_doc["http_success_count"]
    job.http_error_count = job_doc["http_error_count"]
    job.exception_count = job_doc["exception_count"]
    job.started_at = job_doc["started_at"].isoformat()
    if job_doc["completed_at"] is not None:
        job.completed_at = job_doc["completed_at"].isoformat()
    run_state = job_doc["run_state"].upper()
    job.run_state = PbRunState.Value(run_state)
    http_status_counts = job_doc["http_status_counts"]
    for status_code, count in http_status_counts.items():
        job.http_status_counts[int(status_code)] = count


@api_handler
async def get_job_items(command, response, server_db):
    """ Get a page of items (crawl responses) from a job. """
    job_id = str(UUID(bytes=command.job_id))
    limit = command.page.limit
    offset = command.page.offset
    count, items = await server_db.get_job_items(
        job_id,
        limit,
        offset,
        command.include_success,
        command.include_error,
        command.include_exception,
    )
    response.list_items.total = count
    compression_ok = command.compression_ok
    for item_doc in items:
        item = response.list_items.items.add()

        if item_doc["join"] is None:
            item.is_compressed = False
        elif item_doc["join"]["is_compressed"] and not compression_ok:
            item.body = gzip.decompress(item_doc["join"]["body"])
            item.is_compressed = False
        else:
            item.body = item_doc["join"]["body"]
            item.is_compressed = item_doc["join"]["is_compressed"]
        if "content_type" in item_doc:
            item.content_type = item_doc["content_type"]
        if "exception" in item_doc:
            item.exception = item_doc["exception"]
        if "status_code" in item_doc:
            item.status_code = item_doc["status_code"]
        header_iter = iter(item_doc.get("headers", []))
        for key in header_iter:
            value = next(header_iter)
            header = item.headers.add()
            header.key = key
            header.value = value
        item.cost = item_doc["cost"]
        item.job_id = UUID(item_doc["job_id"]).bytes
        item.completed_at = item_doc["completed_at"].isoformat()
        item.started_at = item_doc["started_at"].isoformat()
        item.duration = item_doc["duration"]
        item.url = item_doc["url"]
        item.url_can = item_doc["canonical_url"]
        item.is_success = item_doc["is_success"]


# Note: A get_job_item() API handler would be useful here to fetch a single
# item by sequence number, but it requires adding RequestGetJobItem to the
# protobuf definitions in the starbelly-protobuf repository. The database
# method get_job_item() has been added to support this functionality when
# the protobuf is updated. For now, the frontend can use get_job_items with
# limit=1 and appropriate offset to fetch individual items.


@api_handler
async def list_jobs(command, response, server_db):
    """ Return a list of jobs. """
    limit = command.page.limit
    offset = command.page.offset
    if command.HasField("started_after"):
        started_after = dateutil.parser.parse(command.started_after)
    else:
        started_after = None
    tag = command.tag if command.HasField("tag") else None
    schedule_id = (
        str(UUID(bytes=command.schedule_id))
        if command.HasField("schedule_id")
        else None
    )
    count, jobs = await server_db.list_jobs(
        limit, offset, started_after, tag, schedule_id
    )
    response.list_jobs.total = count

    for job_doc in jobs:
        job = response.list_jobs.jobs.add()
        job.job_id = UUID(job_doc["id"]).bytes
        job.name = job_doc["name"]
        for seed in job_doc["seeds"]:
            job.seeds.append(seed)
        for tag in job_doc["tags"]:
            job.tags.append(tag)
        job.item_count = job_doc["item_count"]
        job.http_success_count = job_doc["http_success_count"]
        job.http_error_count = job_doc["http_error_count"]
        job.exception_count = job_doc["exception_count"]
        job.started_at = job_doc["started_at"].isoformat()
        if job_doc["completed_at"] is not None:
            job.completed_at = job_doc["completed_at"].isoformat()
        run_state = job_doc["run_state"].upper()
        job.run_state = PbRunState.Value(run_state)
        http_status_counts = job_doc["http_status_counts"]
        for status_code, count in http_status_counts.items():
            job.http_status_counts[int(status_code)] = count


@api_handler
async def set_job(command, crawl_manager, response):
    """ Create or update job metadata. """
    if command.HasField("job_id"):
        # Update run state of existing job.
        job_id = str(UUID(bytes=command.job_id))
        if command.HasField("run_state"):
            run_state = command.run_state
            if run_state == PbRunState.Value("CANCELLED"):
                await crawl_manager.cancel_job(job_id)
            elif run_state == PbRunState.Value("PAUSED"):
                await crawl_manager.pause_job(job_id)
            elif run_state == PbRunState.Value("RUNNING"):
                await crawl_manager.resume_job(job_id)
            else:
                raise InvalidRequestException(
                    f"Not allowed to set job run state: {run_state}"
                )
    else:
        # Create new job.
        if not command.policy_id:
            raise InvalidRequestException('"policy_id" is required')
        if not command.seeds:
            raise InvalidRequestException('"seeds" is required')
        name = command.name
        policy_id = str(UUID(bytes=command.policy_id))
        seeds = [s.strip() for s in command.seeds]
        tags = [t.strip() for t in command.tags]

        if name.strip() == "":
            url = URL(seeds[0])
            name = url.host
            if len(seeds) > 1:
                name += "& {} more".format(len(seeds) - 1)

        job_id = await crawl_manager.start_job(name, seeds, tags, policy_id)
        response.new_job.job_id = UUID(job_id).bytes
