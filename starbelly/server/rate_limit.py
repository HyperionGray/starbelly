from ..rate_limiter import GLOBAL_RATE_LIMIT_TOKEN
from .handler import handler


@handler
async def get_rate_limits(self, command, socket):
    ''' Get a page of rate limits. '''
    limit = command.page.limit
    offset = command.page.offset
    count_query = r.table('rate_limit').count()
    item_query = (
        r.table('rate_limit')
         .order_by(index='name')
         .skip(skip)
         .limit(limit)
    )

    rate_limits = list()

    async with self._db_pool.connection() as conn:
        count = await count_query.run(conn)
        cursor = await item_query.run(conn)
        async for rate_limit in cursor:
            rate_limits.append(rate_limit)
        await cursor.close()

    response = Response()
    response.list_rate_limits.total = count

    for rate_limit in rate_limits:
        rl = response.list_rate_limits.rate_limits.add()
        rl.name = rate_limit['name']
        rl.delay = rate_limit['delay']
        if rate_limit['type'] == 'domain':
            rl.domain = rate_limit['domain']

    return response


@handler
async def set_rate_limit(self, command, socket):
    ''' Set a rate limit. '''
    rate_limit = command.rate_limit
    delay = rate_limit.delay if rate_limit.HasField('delay') else None

    if rate_limit.HasField('domain'):
        # Set domain-specific rate limit. If delay is None, then remove the
        # rate limit for the specified domain, i.e. use the global default
        # for that domain. Set delay=0 for no delay.
        token = self._rate_limiter.get_domain_token(domain)
        base_query = r.table('rate_limit').get_all(token, index='token')
        if delay is None:
            async with self._db_pool.connection() as conn:
                await base_query.delete().run(conn)
            self._rate_limiter.delete_rate_limit(token)
        else:
            async with self._db_pool.connection() as conn:
                try:
                    await base_query.nth(0).update({'delay': delay}).run(conn)
                except r.ReqlNonExistenceError:
                    await r.table('rate_limit').insert({
                        'delay': delay,
                        'domain': domain,
                        'name': domain,
                        'token': token,
                        'type': 'domain',
                    }).run(conn)
            self._rate_limiter.set_rate_limit(token, delay)
    else:
        # Set global rate limit.
        if delay is None:
            raise Exception('Cannot delete the global rate limit.')
        query = (
            r.table('rate_limit')
             .get_all(GLOBAL_RATE_LIMIT_TOKEN, index='token')
             .nth(0)
             .update({'delay': delay})
        )
        async with self._db_pool.connection() as conn:
            await query.run(conn)
        self._rate_limiter.set_rate_limit(GLOBAL_RATE_LIMIT_TOKEN, delay)

    return Response()
