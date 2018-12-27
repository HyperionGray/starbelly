from unittest.mock import Mock
from uuid import UUID

import trio


from starbelly.downloader import (
    Downloader,
    DownloadRequest,
    DownloadResponse,
)


def test_request():
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    req = DownloadRequest(
        job_id=job_id,
        method='GET',
        url='http://downloader.example/path1/path2?k2=v2&k1=v1',
        form_data=None,
        cost=1.0,
        policy=None,
        cookie_jar=None
    )
    assert req.job_id == job_id
    assert req.url.host == 'downloader.example'
    assert req.canonical_url == 'http://downloader.example/path1/' \
        'path2?k1=v1&k2=v2'


def test_response():
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    req = DownloadRequest(
        job_id=job_id,
        method='GET',
        url='http://downloader.example/path1/path2?k2=v2&k1=v1',
        form_data=None,
        cost=1.0,
        policy=None,
        cookie_jar=None
    )
    resp = DownloadResponse.from_request(req)
    resp.start()
    assert resp.duration is None
    http_response = Mock(object())
    http_response.status = 200
    http_response.content_type = 'text/html'
    http_response.headers = {'User-agent': 'foo'}
    body = b'<html><head><title>test</title></head><body>test</body></html>'
    resp.set_response(http_response, body)
    assert resp.duration > 0
    assert resp.status_code == 200
    assert resp.content_type == 'text/html'
    assert resp.headers['User-agent'] == 'foo'
    assert resp.body.startswith(b'<html>')


def test_response_exception():
    job_id = UUID('123e4567-e89b-12d3-a456-426655440001').bytes
    req = DownloadRequest(
        job_id=job_id,
        method='GET',
        url='http://downloader.example/path1/path2?k2=v2&k1=v1',
        form_data=None,
        cost=1.0,
        policy=None,
        cookie_jar=None
    )
    resp = DownloadResponse.from_request(req)
    resp.start()
    assert resp.duration is None
    resp.set_exception('Sample exception')
    assert resp.duration > 0
    assert resp.exception == 'Sample exception'


# async def test_download_one_resource(autojump_clock, nursery):
#     request_send, request_recv = trio.open_memory_channel(0)
#     response_send, response_recv = trio.open_memory_channel(0)
#     dl = Downloader(request_recv, response_send, concurrent=1)
#     nursery.start_soon(dl.run)


