from . import api_handler, InvalidRequestException
from ..rate_limiter import get_domain_token, GLOBAL_RATE_LIMIT_TOKEN


@api_handler
async def list_rate_limits(command, response, server_db):
    ''' Get a page of rate limits. '''
    limit = command.page.limit
    offset = command.page.offset
    count, rate_limits = await server_db.list_rate_limits(limit, offset)
    response.list_rate_limits.total = count

    for rate_limit in rate_limits:
        rl = response.list_rate_limits.rate_limits.add()
        rl.name = rate_limit['name']
        rl.token = rate_limit['token']
        rl.delay = rate_limit['delay']
        if rl.name.startswith('domain:'):
            rl.domain = rl.name.split(':')[1]


@api_handler
async def set_rate_limit(command, rate_limiter, server_db):
    ''' Set a rate limit. '''
    delay = command.delay if command.HasField('delay') else None

    if command.HasField('domain'):
        # Set a specific rate limit.
        domain = command.domain
        token = get_domain_token(domain)
        name = 'domain:{}'.format(domain)
    else:
        # Set global rate limit.
        if delay is None:
            raise InvalidRequestException(
                'Cannot delete the global rate limit.')
        token = GLOBAL_RATE_LIMIT_TOKEN
        name = 'Global Rate Limit'

    await server_db.set_rate_limit(name, token, delay)
    if delay is None:
        rate_limiter.delete_rate_limit(token)
    else:
        rate_limiter.set_rate_limit(token, delay)
