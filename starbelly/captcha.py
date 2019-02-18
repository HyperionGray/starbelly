import base64
from uuid import UUID

import starbelly.starbelly_pb2


class CaptchaSolver:
    ''' An interface for a CAPTCHA solving service. '''
    def __init__(self, doc):
        '''
        Constructor.

        :param dict doc: A database document.
        '''
        self.id = doc['id']
        self.name = doc['name']
        self.service_url = doc['service_url']
        self.api_key = doc['api_key']
        self.require_phrase = doc['require_phrase']
        self.case_sensitive = doc['case_sensitive']
        self.characters = doc['characters']
        self.require_math = doc['require_math']
        self.min_length = doc.get('min_length', 0)
        self.max_length = doc.get('max_length', 0)

    def get_command(self, img_data):
        '''
        Return a JSON API command.

        :param bytes img_data: The image data for the CAPTCHA.
        :returns: A command that can be serialized to JSON.
        :rtype: dict
        '''
        img_b64 = base64.b64encode(img_data).decode('ascii')

        if self.characters == 'ALPHANUMERIC':
            numeric = 0
        elif self.characters == 'NUMERIC_ONLY':
            numeric = 1
        elif self.characters == 'ALPHA_ONLY':
            numeric = 2
        else:
            raise Exception('Invalid characters setting: {}'.format(
                self.characters))

        return {
            'clientKey': self.api_key,
            'task': {
                'type': 'ImageToTextTask',
                'body': img_b64,
                'phrase': self.require_phrase,
                'case': self.case_sensitive,
                'numeric': numeric,
                'math': self.require_math,
                'minLength': self.min_length,
                'maxLength': self.max_length,
            }
        }


def captcha_doc_to_pb(doc):
    '''
    Convert CAPTCHA solver from database document to protobuf.

    :param dict doc: A database document.
    :returns: A protobuf message.
    '''
    pb = starbelly.starbelly_pb2.CaptchaSolver()
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
    '''
    Convert Antigate CAPTCHA solver from database doc to protobuf.

    :param dict doc: A database document.
    :returns: A protobuf message.
   '''
    pb = starbelly.starbelly_pb2.CaptchaSolverAntigate()
    pb.service_url = doc['service_url']
    pb.api_key = doc['api_key']
    pb.require_phrase = doc['require_phrase']
    pb.case_sensitive = doc['case_sensitive']
    pb.characters = starbelly.starbelly_pb2.CaptchaSolverAntigateCharacters \
        .Value(doc['characters'])
    pb.require_math = doc['require_math']
    if 'min_length' in doc:
        pb.min_length = doc['min_length']
    if 'max_length' in doc:
        pb.max_length = doc['max_length']
    return pb


def captcha_pb_to_doc(pb):
    '''
    Convert CAPTCHA solver from protobuf to database document.

    :param pb: A protobuf message.
    :returns: A database document.
    :rtype: dict
    '''
    if pb.name.strip() == '':
        raise Exception('Name is required.')
    doc = {'name': pb.name}
    if pb.HasField('solver_id'):
        doc['id'] = str(UUID(bytes=pb.solver_id))
    type_ = pb.WhichOneof('SolverType')
    if type_ == 'antigate':
        doc.update(_antigate_pb_to_doc(pb))
    else:
        raise Exception('Unknown CAPTCHA solver type ({})'.format(type_))
    return doc


def _antigate_pb_to_doc(pb):
    '''
    Convert Antigate CAPTCHA solver from database doc to protobuf.

    :param pb: A protobuf message.
    :returns: A database document.
    :rtype: dict
    '''
    antigate = pb.antigate
    doc = {
        'service_url': antigate.service_url,
        'api_key': antigate.api_key,
        'require_phrase': antigate.require_phrase,
        'case_sensitive': antigate.case_sensitive,
        'characters': starbelly.starbelly_pb2.CaptchaSolverAntigateCharacters \
            .Name(antigate.characters),
        'require_math': antigate.require_math,
        'type': 'antigate',
    }
    if antigate.HasField('min_length'):
        doc['min_length'] = antigate.min_length
    if antigate.HasField('max_length'):
        doc['max_length'] = antigate.min_length
    return doc
