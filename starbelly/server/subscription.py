from uuid import UUID

import trio.hazmat

from . import api_handler


@api_handler
async def subscribe_job_sync(command, crawl_manager, response,
        subscription_manager, server_db):
    ''' 
    Handle the subscribe crawl items command.
    
    Supports three subscription modes via the job_id parameter:
    1. Single job: Pass a 16-byte UUID 
    2. Tag subscription: Pass b"tag:" + tag_name (UTF-8 encoded)
    3. Schedule subscription: Pass b"schedule:" + schedule_id (16-byte UUID)
    '''
    job_id_bytes = command.job_id
    compression_ok = command.compression_ok
    job_state_recv = crawl_manager.get_job_state_channel()
    sync_token = command.sync_token if command.HasField('sync_token') else None
    
    # Detect subscription type based on job_id content
    if job_id_bytes.startswith(b'tag:'):
        # Tag-based subscription
        tag = job_id_bytes[4:].decode('utf-8')
        sub_id = subscription_manager.subscribe_job_sync_by_tag(
            tag, compression_ok, job_state_recv, server_db, sync_token)
    elif job_id_bytes.startswith(b'schedule:'):
        # Schedule-based subscription  
        schedule_id = str(UUID(bytes=job_id_bytes[9:9+16]))
        sub_id = subscription_manager.subscribe_job_sync_by_schedule(
            schedule_id, compression_ok, job_state_recv, server_db, sync_token)
    else:
        # Single job subscription (original behavior)
        job_id = str(UUID(bytes=job_id_bytes))
        sub_id = subscription_manager.subscribe_job_sync(job_id, compression_ok,
            job_state_recv, sync_token)
    
    response.new_subscription.subscription_id = sub_id


@api_handler
async def subscribe_job_status(command, response, subscription_manager,
        stats_tracker):
    ''' Handle the subscribe crawl status command. '''
    sub_id = subscription_manager.subscribe_job_status(stats_tracker,
        command.min_interval)
    response.new_subscription.subscription_id = sub_id


@api_handler
async def subscribe_resource_monitor(command, response, resource_monitor,
        subscription_manager):
    ''' Handle the subscribe resource monitor command. '''
    sub_id = subscription_manager.subscribe_resource_monitor(resource_monitor,
        command.history)
    response.new_subscription.subscription_id = sub_id


@api_handler
async def subscribe_task_monitor(command, response, subscription_manager):
    ''' Handle the subscribe task monitor command. '''
    root_task = trio.hazmat.current_root_task()
    sub_id = subscription_manager.subscribe_task_monitor(command.period,
        root_task)
    response.new_subscription.subscription_id = sub_id


@api_handler
async def unsubscribe(command, subscription_manager):
    ''' Handle an unsubscribe command. '''
    sub_id = command.subscription_id
    subscription_manager.cancel_subscription(sub_id)
