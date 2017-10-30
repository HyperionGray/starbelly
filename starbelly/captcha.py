from uuid import UUID

import dateutil

from protobuf.shared_pb2 import CaptchaSolver, CaptchaSolverAntigate, \
    CaptchaSolverAntigateCharacters


def captcha_doc_to_pb(doc):
    ''' Convert CAPTCHA solver from database document to protobuf. '''
    pb = CaptchaSolver()
    pb.name = doc['name']
    pb.solver_id = UUID(doc['id']).bytes
    pb.created_at = doc['created_at'].isoformat()
    pb.updated_at = doc['updated_at'].isoformat()
    type_ = doc['type']
    if type_ == 'antigate':
        pb.antigate.CopyFrom(_antigate_doc_to_pb(doc))
    else:
        raise Exception('Unknown CAPTCHA solver type ({})'.format(type_))
    return pb


def _antigate_doc_to_pb(doc):
    ''' Convert Antigate CAPTCHA solver from database doc to protobuf. '''
    pb = CaptchaSolverAntigate()
    pb.service_url = doc['service_url']
    pb.api_key = doc['api_key']
    pb.require_phrase = doc['require_phrase']
    pb.case_sensitive = doc['case_sensitive']
    pb.characters = CaptchaSolverAntigateCharacters.Value(doc['characters'])
    pb.require_math = doc['require_math']
    if 'min_length' in doc:
        pb.min_length = doc['min_length']
    if 'max_length' in doc:
        pb.max_length = doc['max_length']
    return pb


def captcha_pb_to_doc(pb):
    ''' Convert CAPTCHA solver from protobuf to database document. '''
    if pb.name.strip() == '':
        raise Exception('Name is required.')
    doc = {'name': pb.name}
    if pb.HasField('solver_id'):
        doc['id'] = pb.solver_id
    type_ = pb.WhichOneof('SolverType')
    if type_ == 'antigate':
        doc.update(_antigate_pb_to_doc(pb))
    else:
        raise Exception('Unknown CAPTCHA solver type ({})'.format(type_))
    return doc


def _antigate_pb_to_doc(pb):
    ''' Convert Antigate CAPTCHA solver from database doc to protobuf. '''
    antigate = pb.antigate
    doc = {
        'service_url': antigate.service_url,
        'api_key': antigate.api_key,
        'require_phrase': antigate.require_phrase,
        'case_sensitive': antigate.case_sensitive,
        'characters': CaptchaSolverAntigateCharacters.Name(antigate.characters),
        'require_math': antigate.require_math,
        'type': 'antigate',
    }
    if antigate.HasField('min_length'):
        doc['min_length'] = antigate.min_length
    if antigate.HasField('max_length'):
        doc['max_length'] = antigate.min_length
    return doc
