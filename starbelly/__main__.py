import asyncio
import logging
import sys

from . import logger
from .downloader import Downloader
from .frontier import Frontier
from .rate_limiter import DomainRateLimiter
from .server import Server


if len(sys.argv) > 1 and sys.argv[1] == '-d':
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

rate_limiter = DomainRateLimiter()
frontier = Frontier(rate_limiter)
downloader = Downloader(frontier)
server = Server('localhost', 8000, frontier, downloader, rate_limiter)

loop = asyncio.get_event_loop()
logger.info('Starting server')
loop.run_until_complete(server.start())
try:
    loop.run_forever()
except KeyboardInterrupt:
    logger.info('Received interrupt... trying graceful shutdown.')
    remaining_tasks = asyncio.Task.all_tasks()
    for task in remaining_tasks:
        task.cancel()
    if len(remaining_tasks) > 0:
        loop.run_until_complete(asyncio.wait(remaining_tasks))

loop.close()
logger.info('Server is stopped.')
