from datetime import datetime, timezone

from ..captcha import captcha_doc_to_pb, captcha_pb_to_doc
from .handler import handler


@handler
async def delete_captcha_solver(server, command, socket):
    ''' Delete a a CAPTCHA solver. '''
    if command.HasField('solver_id'):
        solver_id = str(UUID(bytes=command.solver_id))
    else:
        raise InvalidRequestException('solver_id is required.')

    response = Response()
    async with self._db_pool.connection() as conn:
        use_count = await (
            r.table('policy')
             .filter({'captcha_solver_id': solver_id})
             .count()
             .run(conn)
        )
        if use_count > 0:
            raise InvalidRequestException('Cannot delete CAPTCHA solver'
                ' because it is being used by a policy.')
        await (
            r.table('captcha_solver')
             .get(solver_id)
             .delete()
             .run(conn)
        )

    return response


@handler
async def get_captcha_solver(self, command, socket):
    ''' Get a CAPTCHA solver. '''
    if not command.HasField('solver_id'):
        raise InvalidRequestException('solver_id is required.')

    solver_id = str(UUID(bytes=command.solver_id))
    async with self._db_pool.connection() as conn:
        doc = await r.table('captcha_solver').get(solver_id).run(conn)

    if doc is None:
        raise InvalidRequestException('No CAPTCHA solver found for that ID')

    response = Response()
    response.solver.CopyFrom(captcha_doc_to_pb(doc))
    return response


@handler
async def list_captcha_solvers(self, command, socket):
    ''' Return a list of CAPTCHA solvers. '''
    limit = command.page.limit
    offset = command.page.offset
    response = Response()
    solvers = list()

    async with self._db_pool.connection() as conn:
        count = await r.table('captcha_solver').count().run(conn)
        docs = await (
            r.table('captcha_solver')
             .order_by('name')
             .skip(offset)
             .limit(limit)
             .run(conn)
        )

    for doc in docs:
        solver = response.list_captcha_solvers.solvers.add()
        solver.CopyFrom(captcha_doc_to_pb(doc))

    response.list_captcha_solvers.total = count
    return response


@handler
async def set_captcha_solver(self, command, socket):
    ''' Create or update CAPTCHA solver. '''
    now = datetime.now(datetime.utc)
    doc = captcha_pb_to_doc(command.solver)
    doc['updated_at'] = now
    response = Response()
    async with self._db_pool.connection() as conn:
        if command.solver.HasField('solver_id'):
            await r.table('captcha_solver').update(doc).run(conn)
        else:
            doc['created_at'] = now
            result = await r.table('captcha_solver').insert(doc).run(conn)
            solver_id = result['generated_keys'][0]
            response.new_solver.solver_id = UUID(solver_id).bytes

    return response
