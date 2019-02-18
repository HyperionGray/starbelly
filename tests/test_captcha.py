from datetime import datetime, timezone
from uuid import UUID

import pytest

from starbelly.captcha import (
    CaptchaSolver,
    captcha_doc_to_pb,
    captcha_pb_to_doc,
)
from starbelly.starbelly_pb2 import CaptchaSolverAntigateCharacters


def test_captcha_command():
    captcha_doc = {
        'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'name': 'Captcha #1',
        'service_url': 'https://captcha.example/service.php',
        'api_key': 'FAKE-API-KEY',
        'require_phrase': False,
        'case_sensitive': True,
        'characters': 'ALPHANUMERIC',
        'require_math': False,
    }
    solver = CaptchaSolver(captcha_doc)
    img_data = b'\x01\x02\x03\x04'
    command = solver.get_command(img_data)
    assert command['clientKey'] == 'FAKE-API-KEY'
    assert command['task']['type'] == 'ImageToTextTask'
    assert command['task']['body'] == 'AQIDBA==' # Base64 of img_data
    assert not command['task']['phrase']
    assert command['task']['case']
    assert command['task']['numeric'] == 0
    assert not command['task']['math']
    assert command['task']['minLength'] == 0
    assert command['task']['maxLength'] == 0


def test_captcha_doc_to_pb():
    captcha_id = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    captcha_doc = {
        'id': str(captcha_id),
        'type': 'antigate',
        'created_at': datetime(2019, 1, 26, 15, 30, 0, tzinfo=timezone.utc),
        'updated_at': datetime(2019, 1, 26, 15, 35, 0, tzinfo=timezone.utc),
        'name': 'Captcha #1',
        'service_url': 'https://captcha.example/service.php',
        'api_key': 'FAKE-API-KEY',
        'require_phrase': False,
        'case_sensitive': True,
        'characters': 'ALPHANUMERIC',
        'require_math': False,
    }
    pb_captcha = captcha_doc_to_pb(captcha_doc)
    assert pb_captcha.name == 'Captcha #1'
    assert pb_captcha.solver_id == captcha_id.bytes
    assert pb_captcha.created_at == '2019-01-26T15:30:00+00:00'
    assert pb_captcha.updated_at == '2019-01-26T15:35:00+00:00'
    assert pb_captcha.antigate.service_url == \
        'https://captcha.example/service.php'
    assert pb_captcha.antigate.api_key == 'FAKE-API-KEY'
    assert not pb_captcha.antigate.require_phrase
    assert pb_captcha.antigate.case_sensitive
    assert pb_captcha.antigate.characters == \
        CaptchaSolverAntigateCharacters.Value('ALPHANUMERIC')
    assert not pb_captcha.antigate.require_math

    captcha_doc = captcha_pb_to_doc(pb_captcha)
    assert captcha_doc['id'] == str(captcha_id)
    assert captcha_doc['name'] == 'Captcha #1'
    assert captcha_doc['type'] == 'antigate'
    assert captcha_doc['service_url'] == 'https://captcha.example/service.php'
    assert captcha_doc['api_key'] == 'FAKE-API-KEY'
    assert captcha_doc['require_phrase'] == False
    assert captcha_doc['case_sensitive'] == True
    assert captcha_doc['characters'] == 'ALPHANUMERIC'
    assert captcha_doc['require_math'] == False
