from uuid import UUID

import trio.hazmat

from . import api_handler


@api_handler
async def subscribe_crawl_sync(command, response, subscription_manager):
    ''' Handle the subscribe crawl items command. '''
    job_id = str(UUID(bytes=command.job_id))
    compression_ok = command.compression_ok
    sync_token = command.sync_token if command.HasField('sync_token') else None
    sub_id = subscription_manager.subscribe_crawl_sync(job_id, compression_ok,
        sync_token)
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
async def unsubscribe(command, response, subscription_manager):
    ''' Handle an unsubscribe command. '''
    sub_id = command.subscription_id
    subscription_manager.cancel_subscription(sub_id)
