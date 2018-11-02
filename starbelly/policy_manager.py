import rethinkdb as r

from starbelly.policy import Policy


class PolicyManager:
    '''
    Manages policy storage, including saving, loading, and deleting policies
    in the database.
    '''

    def __init__(self, db_pool):
        '''
        Constructor.

        :param db_pool: A database connection pool.
        :type db_pool: starbelly.db.AsyncRethinkPool
        '''
        self._db_pool = db_pool

    async def delete_policy(self, policy_id):
        '''
        Delete a policy.

        :param bytes policy_id: ID of the policy to delete.
        '''
        async with self._db_pool.connection() as conn:
            await r.table('policy').get(policy_id).delete().run(conn)

    async def get_policy(self, policy_id):
        '''
        Load a policy.

        :param bytes: ID of the policy to load.
        :returns: A policy.
        :rtype: dict
        '''
        async with self._db_pool.connection() as conn:
            policy = await r.table('policy').get(policy_id).run(conn)
        return policy

    async def list_policies(self, limit, offset):
        '''
        Return a list of policies.

        :param int limit: The maximum number of policies to return.
        :param int offset: Skip the first ``offset`` rows.
        :returns: The number of policies and a list of those policies.
        :rtype: list[tuple[int,dict]]
        '''
        policies = list()
        query = (
            r.table('policy')
             .order_by(index='name')
             .skip(offset)
             .limit(limit)
        )

        async with self._db_pool.connection() as conn:
            count = await r.table('policy').count().run(conn)
            cursor = await query.run(conn)
            async for policy in cursor:
                policies.append(policy)
            await cursor.close()

        return count, policies

    async def set_policy(self, policy):
        '''
        Save policy details.

        If the policy has an ID, then that the corresponding document is
        updated and this method returns None. If the policy does not have an ID,
        then a new document is created and this method returns the new ID.

        :param dict policy: The policy object to save.
        '''
        # Validate policy by trying to instantiate a Policy object, which will
        # raise an exception if the policy is invalid.
        Policy(
            policy,
            version=VERSION,
            seeds=['http://test1.com', 'http://test2.org'],
            robots_txt_manager=None
        )

        # Save policy.
        async with self._db_pool.connection() as conn:
            if 'id' in policy:
                policy['updated_at'] = r.now()
                await (
                    r.table('policy')
                     .get(policy['id'])
                     .update(policy)
                     .run(conn)
                )
                policy_id = None
            else:
                policy['created_at'] = r.now()
                policy['updated_at'] = r.now()
                result = await r.table('policy').insert(policy).run(conn)
                policy_id = result['generated_keys'][0]

        return policy_id
