from ..subscription import (
    CrawlSyncSubscription,
    JobStatusSubscription,
    ResourceMonitorSubscription,
    TaskMonitorSubscription
)
from .handler import handler


@handler
async def subscribe_crawl_sync(self, command, socket):
    ''' Handle the subscribe crawl items command. '''
    job_id = str(UUID(bytes=command.job_id))
    compression_ok = command.compression_ok

    if command.HasField('sync_token'):
        sync_token = command.sync_token
    else:
        sync_token = None

    subscription = CrawlSyncSubscription(
        self._tracker, self._db_pool, socket, job_id, compression_ok,
        sync_token
    )

    self._subscription_manager.add(subscription)
    response = Response()
    response.new_subscription.subscription_id = subscription.get_id()
    return response


@handler
async def subscribe_job_status(self, command, socket):
    ''' Handle the subscribe crawl status command. '''
    subscription = JobStatusSubscription(
        self._tracker,
        socket,
        command.min_interval
    )
    self._subscription_manager.add(subscription)
    response = Response()
    response.new_subscription.subscription_id = subscription.get_id()
    return response


@handler
async def subscribe_resource_monitor(self, command, socket):
    ''' Handle the subscribe resource monitor command. '''
    subscription = ResourceMonitorSubscription(socket,
        self._resource_monitor, command.history)
    self._subscription_manager.add(subscription)
    response = Response()
    response.new_subscription.subscription_id = subscription.get_id()
    return response


@handler
async def subscribe_task_monitor(self, command, socket):
    ''' Handle the subscribe task monitor command. '''
    subscription = TaskMonitorSubscription(socket, command.period,
        command.top_n)
    self._subscription_manager.add(subscription)
    response = Response()
    response.new_subscription.subscription_id = subscription.get_id()
    return response


@handler
async def unsubscribe(self, command, socket):
    ''' Handle an unsubscribe command. '''
    sub_id = command.subscription_id
    await self._subscription_manager.unsubscribe(socket, sub_id)
    return Response()
