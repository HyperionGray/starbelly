import asyncio
from collections import defaultdict, namedtuple
import logging
import traceback

import aiohttp
import async_timeout

from . import cancel_futures, raise_future_exception


logger = logging.getLogger(__name__)


class Downloader:
    '''
    This class is responsible for downloading crawl items.

    TODO The constructor takes a ``concurrent`` argument that limits
    simultaneous downloads, but a better strategy would be to somehow monitor
    bandwidth and keep adding concurrent downloads until resources are maxed
    out. This also needs to take into account how quickly writes can be ingested
    into the database.
    '''

    def __init__(self, concurrent=10):
        ''' Constructor. '''
        self._job_downloads = defaultdict(set)
        self._job_pushes = defaultdict(set)
        self._semaphore = asyncio.Semaphore(concurrent)
        self._task = None

    async def push(self, crawl_item):
        '''
        Schedule an item for download.

        Blocks if the downloader is busy. If the crawl item's job is removed
        while a task is waiting to ``push()``, then this coroutine will return
        immediately instead of pushing the item.
        '''

        task = asyncio.Task.current_task()
        job_id = crawl_item.job_id
        job_pushes = self._job_pushes[job_id]
        job_pushes.add(task)

        try:
            await self._semaphore.acquire()
            job_id = crawl_item.job_id
            dl_task = asyncio.ensure_future(self._download(crawl_item))
            raise_future_exception(dl_task)
        except asyncio.CancelledError:
            # Cancellation is fine. Mark the item as complete so that the rate
            # limiter can reset.
            crawl_item.completed.set_result(crawl_item)
            raise
        finally:
            job_pushes.remove(task)
            if len(job_pushes) == 0:
                del self._job_pushes[crawl_item.job_id]

    async def remove_job(self, job_id, finish_downloads=True):
        '''
        Remove any pending downloads for the specified job.

        If ``finish_downloads`` is True, then wait for downloads to finish.
        Otherwise, cancel downloads.
        '''
        # If any task is currently pushing an item for this job: interrupt that
        # task.
        try:
            await cancel_futures(*self._job_pushes[job_id])
        except KeyError:
            # No pushes waiting for this job ID.
            pass

        # Now wait for (or cancel) any current downloads for this job. Make a
        # copy of the jobs since the job list will change as jobs finish.
        try:
            tasks = list(self._job_downloads[job_id])
        except KeyError:
            # No pending items for this job.
            return

        if len(tasks) > 0:
            if finish_downloads:
                logger.info('Waiting on %s downloads for job=%s...',
                    len(tasks), job_id[:8])
                await asyncio.gather(*tasks)
            else:
                logger.info('Cancelling %s downloads for job=%s...',
                    len(tasks), job_id[:8])
                await cancel_futures(*tasks)
            logger.info('All downloads for job=%s are done.', job_id[:8])

    async def _download(self, crawl_item):
        ''' Download a crawl item and update it with the response. '''
        task = asyncio.Task.current_task()
        job_id = crawl_item.job_id
        job_downloads = self._job_downloads[job_id]
        job_downloads.add(task)

        try:
            await self._download_item(crawl_item)
            crawl_item.completed.set_result(crawl_item)
            await crawl_item.download_callback(crawl_item)
            if crawl_item.exception is None:
                logger.info('%d %s (cost=%0.2f)', crawl_item.status_code,
                    crawl_item.url, crawl_item.cost)
        except asyncio.CancelledError:
            # Cancelling the download is okay.
            raise
        finally:
            job_downloads.remove(task)
            if len(job_downloads) == 0:
                del self._job_downloads[job_id]
            self._semaphore.release()

    async def _download_item(self, crawl_item):
        ''' A helper to ``_download()``. '''
        try:
            connector = aiohttp.TCPConnector(verify_ssl=False)
            with aiohttp.ClientSession(connector=connector) as session:
                crawl_item.set_start()
                with async_timeout.timeout(10):
                    async with session.get(crawl_item.url) as response:
                        status = response.status
                        body = await response.read()
                        crawl_item.set_response(status, response.headers, body)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error('Failed downloading %s (exc=%r)', crawl_item.url, exc)
            crawl_item.exception = traceback.format_exc()
