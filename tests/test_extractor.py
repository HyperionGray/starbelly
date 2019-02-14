from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import trio

from . import AsyncMock, fail_after
from starbelly.downloader import DownloadResponse
from starbelly.extractor import CrawlExtractor, extract_urls
from starbelly.policy import Policy


def test_atom():
    ''' Parse links from Atom feed. '''
    base_href = 'http://example.org/atom'
    atom_src = \
     '''<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test Feed</title>
          <link href="http://example.org/"/>
          <updated>2003-12-13T18:30:02Z</updated>
          <author><name>John Doe</name></author>
          <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
          <entry>
            <title>Test 1</title>
            <link href="http://example.org/2003/12/13/test1"/>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <updated>2003-12-13T18:30:02Z</updated>
            <summary>Some text.</summary>
          </entry>
          <entry>
            <title>Test 2</title>
            <link href="http://example.org/2004/01/08/test2"/>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <updated>2004-01-08T17:22:16Z</updated>
            <summary>Some more text.</summary>
          </entry>
        </feed>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='application/atom+xml',
        body=atom_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://example.org/2003/12/13/test1',
        'http://example.org/2004/01/08/test2',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


def test_html():
    ''' Parse links from HTML anchor tags. '''
    base_href = 'http://computer.com/laptops/'
    html_src = \
     '''<!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><title>Test</title></head>
            <body>
                <p>
                    <a href='./netbooks/'>Netbooks</a>
                    <a href="../desktops/">Desktops</a>
                </p>
                <p>
                    <a href='http://partner.computer.com'>Partners</a>
                </p>
            </body>
        </html>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='text/html',
        body=html_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://computer.com/laptops/netbooks/',
        'http://computer.com/desktops/',
        'http://partner.computer.com',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


def test_html_base():
    ''' Parse links from HTML which contains a <base> tag. '''
    base_href = 'http://computer.com/laptops/'
    html_base_src = \
     '''<!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Test</title>
                <base href="http://basecomputer.com/foo/">
            </head>
            <body>
                <p>
                    <a href='./netbooks/'>Netbooks</a>
                    <a href="../desktops/">Desktops</a>
                </p>
                <p>
                    <a href='http://partner.computer.com'>Partners</a>
                </p>
            </body>
        </html>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='text/html',
        body=html_base_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://basecomputer.com/foo/netbooks/',
        'http://basecomputer.com/desktops/',
        'http://partner.computer.com',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


def test_rss():
    ''' Parse links from RSS feed. '''
    base_href = 'http://example.org/rss'
    rss_src = \
     '''<rss version="2.0">
            <channel>
                <title>Test Channel</title>
                <link>http://example.orgtest-chhanel/</link>
                <description>A test RSS feed.</description>
                <language>en-us</language>
                <lastBuildDate>Mon, 30 Sep 2002 11:00:00 GMT</lastBuildDate>
                <generator>RSS Generator 1.0</generator>
                <ttl>40</ttl>
                <item>
                    <description>Sample content</description>
                    <pubDate>Mon, 30 Sep 2002 01:56:02 GMT</pubDate>
                    <guid>http://example.org/2002/09/29/test1</guid>
                </item>
                <item>
                    <description>More content</description>
                    <pubDate>Tue, 01 Oct 2002 02:14:55 GMT</pubDate>
                    <guid>http://example.org/2002/10/01/test2</guid>
                </item>
            </channel>
        </rss>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='application/rss+xml',
        body=rss_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://example.org/2002/09/29/test1',
        'http://example.org/2002/10/01/test2',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


def test_xhtml():
    ''' Parse links from XHTML anchor tags. '''
    base_href = 'http://computer.com/laptops/'
    xhtml_src = \
     '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
            <head><meta charset="UTF-8" /><title>Test</title></head>
            <body>
                <p>
                    <a href='./netbooks/'>Netbooks</a>
                    <a href="../desktops/">Desktops</a>
                </p>
                <p>
                    <a href='http://partner.computer.com'>Partners</a>
                </p>
            </body>
        </html>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='application/xhtml+xml',
        body=xhtml_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://computer.com/laptops/netbooks/',
        'http://computer.com/desktops/',
        'http://partner.computer.com',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


def test_unsupported_content_type():
    ''' Cannot extract links from an unsupported MIME type. '''
    base_href = 'http://computer.com/laptops/'
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='bogus/mime',
        body=b'',
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    with pytest.raises(ValueError):
        extract_urls(item)


def test_skip_malformed_urls():
    ''' Ignore malformed URLs. '''
    base_href = 'http://computer.com/laptops/'
    html_src = \
     '''<!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><title>Test</title></head>
            <body>
                <a href='http://user@'>Invalid</a>
                <a href='http://partner.computer.com'>Partners</a>
            </body>
        </html>'''.encode('utf8')
    item = DownloadResponse(
        frontier_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        cost=1.0,
        url=base_href,
        canonical_url=base_href,
        content_type='text/html',
        body=html_src,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    expected_links = set([
        'http://partner.computer.com',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links


@fail_after(3)
async def test_crawl_extractor(nursery):
    # Create test fixtures.
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    db.delete_frontier_item = AsyncMock()
    db.insert_frontier_items = AsyncMock()
    to_extractor, extractor_recv = trio.open_memory_channel(0)
    extractor_send, from_extractor = trio.open_memory_channel(0)
    created_at = datetime(2018,12,31,13,47,00)
    policy_doc = {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test',
        'created_at': created_at,
        'updated_at': created_at,
        'authentication': {
            'enabled': False,
        },
        'limits': {
            'max_cost': 10,
            'max_duration': 3600,
            'max_items': 10_000,
        },
        'mime_type_rules': [
            {'match': 'MATCHES', 'pattern': '^text/', 'save': True},
            {'save': False},
        ],
        'proxy_rules': [],
        'robots_txt': {
            'usage': 'IGNORE',
        },
        'url_normalization': {
            'enabled': True,
            'strip_parameters': ['b'],
        },
        'url_rules': [
            {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
             'pattern': '^https?://({SEED_DOMAINS})/'},
            {'action': 'MULTIPLY', 'amount': 0},
        ],
        'user_agents': [
            {'name': 'Test User Agent'}
        ]
    }
    policy = Policy(policy_doc, '1.0.0', ['https://extractor.example'])
    robots_txt_manager = Mock()
    robots_txt_manager.is_allowed = AsyncMock(return_value=True)
    old_urls = {b'\xd2\x1b\x9b(p-\xed\xb2\x10\xdf\xf0\xa8\xe1\xa2*<'}
    stats_dict = {'frontier_size': 0}
    extractor = CrawlExtractor(job_id, db, extractor_send, extractor_recv,
        policy, robots_txt_manager, old_urls, stats_dict, batch_size=3)
    assert repr(extractor) == '<CrawlExtractor job_id=aaaaaaaa>'
    nursery.start_soon(extractor.run)

    # The HTML document has 5 valid links (enough to create two batches when the
    # `insert_batch` is set to 3) as well as 1 link that's out of domain (should
    # not be added to frontier) and 1 link that's in `old_urls` (also should not
    # be added to frontier).
    html_body = \
    b'''<!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><title>Test</title></head>
            <body>
                <a href='http://extractor.example/alpha'>Alpha</a>
                <a href='http://extractor.example/bravo'>Bravo</a>
                <a href='http://extractor.example/charlie'>Charlie</a>
                <a href='http://invalid.example/'>Invalid</a>
                <a href='http://extractor.example/delta'>Delta</a>
                <a href='http://extractor.example/echo'>Echo</a>
                <a href='http://extractor.example/old-url'>Echo</a>
            </body>
        </html>'''
    response = DownloadResponse(
        frontier_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        cost=1.0,
        url='https://extractor.example',
        canonical_url='https://extractor.example',
        content_type='text/html',
        body=html_body,
        started_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        completed_at=datetime(2019, 2, 1, 10, 2, 0, tzinfo=timezone.utc),
        exception=None,
        status_code=200,
        headers=dict()
    )
    await to_extractor.send(response)
    await from_extractor.receive()
    # The item should be deleted from the frontier:
    assert db.delete_frontier_item.call_count == 1
    assert db.delete_frontier_item.call_args[0] == \
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
    # The insert function should be called twice: once with three items
    # (alpha, bravo charlie), and once with two items (delta, echo).
    assert db.insert_frontier_items.call_count == 2
    assert len(db.insert_frontier_items.call_args[0]) == 2
    assert stats_dict['frontier_size'] == 5
    assert robots_txt_manager.is_allowed.call_count == 6
