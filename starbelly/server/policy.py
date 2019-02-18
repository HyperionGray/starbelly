from datetime import datetime, timezone
from uuid import UUID

from . import api_handler, InvalidRequestException
from ..policy import Policy
from ..version import __version__


@api_handler
async def delete_policy(command, server_db):
    ''' Delete a policy. '''
    if not command.HasField('policy_id'):
        raise InvalidRequestException('policy ID is required.')
    policy_id = str(UUID(bytes=command.policy_id))
    await server_db.delete_policy(policy_id)


@api_handler
async def get_policy(command, response, server_db):
    ''' Get a single policy. '''
    if not command.HasField('policy_id'):
        raise InvalidRequestException('policy ID is required.')
    policy_id = str(UUID(bytes=command.policy_id))
    policy_doc = await server_db.get_policy(policy_id)
    Policy.convert_doc_to_pb(policy_doc, response.policy)


@api_handler
async def list_policies(command, response, server_db):
    ''' Get a list of policies. '''
    limit = command.page.limit
    offset = command.page.offset
    policies = list()
    count, docs = await server_db.list_policies(limit, offset)
    response.list_policies.total = count

    for policy_doc in docs:
        policy = response.list_policies.policies.add()
        policy.policy_id = UUID(policy_doc['id']).bytes
        policy.name = policy_doc['name']
        policy.created_at = policy_doc['created_at'].isoformat()
        policy.updated_at = policy_doc['updated_at'].isoformat()

    return response


@api_handler
async def set_policy(command, response, server_db):
    '''
    Create or update a single policy.

    If the policy ID is set, then update the corresponding policy.
    Otherwise, create a new policy.
    '''
    policy_doc = Policy.convert_pb_to_doc(command.policy)
    # Validate policy by trying to instantiate a Policy object, which will
    # raise an exception if the policy is invalid.
    Policy(policy_doc, version=__version__,
        seeds=['http://test1.com', 'http://test2.org'])
    now = datetime.now(timezone.utc)
    new_id = await server_db.set_policy(policy_doc, now)
    if new_id is not None:
        response.new_policy.policy_id = UUID(new_id).bytes
