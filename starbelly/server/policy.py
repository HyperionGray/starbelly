from .handler import handler
from .policy import Policy


@handler
async def delete_policy(server, command, socket):
    ''' Delete a policy. '''
    policy_id = str(UUID(bytes=command.policy_id))
    async with db_pool.connection() as conn:
        await r.table('policy').get(policy_id).delete().run(conn)
    return Response()


@handler
async def get_policy(self, command, socket):
    ''' Get a single policy. '''
    policy_id = str(UUID(bytes=command.policy_id))
    async with db_pool.connection() as conn:
        policy_doc = await r.table('policy').get(policy_id).run(conn)
    response = Response()
    Policy.convert_doc_to_pb(policy_doc, response.policy)
    return response


@handler
async def list_policies(self, command, socket):
    ''' Get a list of policies. '''
    limit = command.page.limit
    offset = command.page.offset
    policies = list()
    query = (
        r.table('policy')
         .order_by(index='name')
         .skip(offset)
         .limit(limit)
    )

    async with db_pool.connection() as conn:
        count = await r.table('policy').count().run(conn)
        cursor = await query.run(conn)
        async for policy in cursor:
            policies.append(policy)
        await cursor.close()

    response = Response()
    response.list_policies.total = count

    for policy_doc in policies:
        policy = response.list_policies.policies.add()
        policy.policy_id = UUID(policy_doc['id']).bytes
        policy.name = policy_doc['name']
        policy.created_at = policy_doc['created_at'].isoformat()
        policy.updated_at = policy_doc['updated_at'].isoformat()

    return response

