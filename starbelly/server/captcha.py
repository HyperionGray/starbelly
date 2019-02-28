from datetime import datetime, timezone
import logging
from uuid import UUID

from . import api_handler, InvalidRequestException
from ..captcha import captcha_doc_to_pb, captcha_pb_to_doc


logger = logging.getLogger(__name__)


@api_handler
async def delete_captcha_solver(command, server_db):
    ''' Delete a a CAPTCHA solver. '''
    solver_id = str(UUID(bytes=command.solver_id))
    try:
        await server_db.delete_captcha_solver(solver_id)
    except ValueError as ve:
        raise InvalidRequestException(str(ve)) from None


@api_handler
async def get_captcha_solver(command, response, server_db):
    ''' Get a CAPTCHA solver. '''
    solver_id = str(UUID(bytes=command.solver_id))
    doc = await server_db.get_captcha_solver(solver_id)

    if doc is None:
        raise InvalidRequestException('No CAPTCHA solver found for that ID')

    response.solver.CopyFrom(captcha_doc_to_pb(doc))


@api_handler
async def list_captcha_solvers(command, response, server_db):
    ''' Return a list of CAPTCHA solvers. '''
    limit = command.page.limit
    offset = command.page.offset
    count, docs = await server_db.list_captcha_solvers(limit, offset)

    for doc in docs:
        solver = response.list_captcha_solvers.solvers.add()
        solver.CopyFrom(captcha_doc_to_pb(doc))

    response.list_captcha_solvers.total = count


@api_handler
async def set_captcha_solver(command, response, server_db):
    ''' Create or update CAPTCHA solver. '''
    now = datetime.now(timezone.utc)
    doc = captcha_pb_to_doc(command.solver)
    new_id = await server_db.set_captcha_solver(doc, now)
    if new_id:
        response.new_solver.solver_id = UUID(new_id).bytes
