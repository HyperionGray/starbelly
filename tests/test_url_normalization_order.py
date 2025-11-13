"""
Tests for verifying that URL normalization is applied before URL rules.

This is a regression test for the issue where session IDs in URLs interfere
with URL rule regex matching because normalization happens after rule matching.
"""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import trio

from . import AsyncMock, fail_after
from starbelly.downloader import DownloadResponse
from starbelly.extractor import CrawlExtractor
from starbelly.policy import Policy


@fail_after(3)
async def test_url_normalization_before_rules(nursery):
    """
    Test that URL normalization is applied before URL rules.
    
    This test ensures that session IDs (which should be stripped by normalization)
    do not interfere with URL rule pattern matching.
    
    The test creates a policy that:
    1. Strips the PHPSESSID parameter via URL normalization
    2. Has a URL rule that matches /products/ URLs
    
    With the bug, the URL rule would need to account for the PHPSESSID parameter
    in the regex. After the fix, the normalized URL (without PHPSESSID) is used
    for rule matching, making the regex simpler and more reliable.
    """
    # Create test fixtures.
    job_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    db = Mock()
    db.delete_frontier_item = AsyncMock()
    db.insert_frontier_items = AsyncMock()
    to_extractor, extractor_recv = trio.open_memory_channel(0)
    extractor_send, from_extractor = trio.open_memory_channel(0)
    created_at = datetime(2018, 12, 31, 13, 47, 0)
    
    # Policy that strips PHPSESSID and has URL rules
    policy_doc = {
        'id': 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        'name': 'Test Normalization Order',
        'created_at': created_at,
        'updated_at': created_at,
        'authentication': {
            'enabled': False,
        },
        'limits': {
            'max_cost': 100,
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
            'strip_parameters': ['PHPSESSID', 'sessionid'],
        },
        'url_rules': [
            # This rule should match /products/ URLs after normalization
            # With the bug, the PHPSESSID parameter would interfere
            {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
             'pattern': r'^https://example\.com/products/\w+$'},
            # Everything else gets rejected (cost = 0)
            {'action': 'MULTIPLY', 'amount': 0},
        ],
        'user_agents': [
            {'name': 'Test User Agent'}
        ]
    }
    policy = Policy(policy_doc, '1.0.0', ['https://example.com'])
    downloader = Mock()
    robots_txt_manager = Mock()
    robots_txt_manager.is_allowed = AsyncMock(return_value=True)
    old_urls = set()
    stats_dict = {'frontier_size': 0}
    extractor = CrawlExtractor(job_id, db, extractor_send, extractor_recv,
        policy, downloader, robots_txt_manager, old_urls, stats_dict,
        batch_size=10)
    nursery.start_soon(extractor.run)

    # HTML with URLs that have session IDs
    html_body = \
    b'''<!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><title>Test</title></head>
            <body>
                <a href='https://example.com/products/laptop'>Laptop</a>
                <a href='https://example.com/products/phone?PHPSESSID=abc123'>Phone with session</a>
                <a href='https://example.com/products/tablet?sessionid=xyz789'>Tablet with session</a>
                <a href='https://example.com/about'>About (should be rejected)</a>
            </body>
        </html>'''
    
    response = DownloadResponse(
        frontier_id='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        cost=1.0,
        url='https://example.com',
        canonical_url='https://example.com',
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
    
    # After normalization, all three /products/ URLs should match the pattern
    # and be added to the frontier (the /about URL should be rejected)
    assert db.insert_frontier_items.call_count == 1
    inserted_items = db.insert_frontier_items.call_args[0][0]
    
    # We should have 3 items added: laptop, phone, and tablet
    assert len(inserted_items) == 3
    
    # Verify that the URLs are as expected
    inserted_urls = {item['url'] for item in inserted_items}
    assert 'https://example.com/products/laptop' in inserted_urls
    assert 'https://example.com/products/phone?PHPSESSID=abc123' in inserted_urls
    assert 'https://example.com/products/tablet?sessionid=xyz789' in inserted_urls
    
    # Verify that all three have the same cost (1.0 + 1 = 2.0)
    # because they all matched the first URL rule after normalization
    for item in inserted_items:
        assert item['cost'] == 2.0, f"URL {item['url']} has cost {item['cost']}, expected 2.0"
    
    assert stats_dict['frontier_size'] == 3


@fail_after(3)
async def test_url_normalization_affects_deduplication(nursery):
    """
    Test that URL normalization properly deduplicates URLs.
    
    This test ensures that two URLs that differ only by parameters that should
    be stripped are correctly identified as duplicates after normalization.
    """
    # Create test fixtures.
    job_id = 'cccccccc-cccc-cccc-cccc-cccccccccccc'
    db = Mock()
    db.delete_frontier_item = AsyncMock()
    db.insert_frontier_items = AsyncMock()
    to_extractor, extractor_recv = trio.open_memory_channel(0)
    extractor_send, from_extractor = trio.open_memory_channel(0)
    created_at = datetime(2018, 12, 31, 13, 47, 0)
    
    policy_doc = {
        'id': 'dddddddd-dddd-dddd-dddd-dddddddddddd',
        'name': 'Test Deduplication',
        'created_at': created_at,
        'updated_at': created_at,
        'authentication': {
            'enabled': False,
        },
        'limits': {
            'max_cost': 100,
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
            'strip_parameters': ['utm_source', 'utm_campaign'],
        },
        'url_rules': [
            {'action': 'ADD', 'amount': 1, 'match': 'MATCHES',
             'pattern': r'^https://example\.com/'},
            {'action': 'MULTIPLY', 'amount': 0},
        ],
        'user_agents': [
            {'name': 'Test User Agent'}
        ]
    }
    policy = Policy(policy_doc, '1.0.0', ['https://example.com'])
    downloader = Mock()
    robots_txt_manager = Mock()
    robots_txt_manager.is_allowed = AsyncMock(return_value=True)
    old_urls = set()
    stats_dict = {'frontier_size': 0}
    extractor = CrawlExtractor(job_id, db, extractor_send, extractor_recv,
        policy, downloader, robots_txt_manager, old_urls, stats_dict,
        batch_size=10)
    nursery.start_soon(extractor.run)

    # HTML with the same URL but different tracking parameters
    html_body = \
    b'''<!DOCTYPE html>
        <html>
            <head><meta charset="UTF-8"><title>Test</title></head>
            <body>
                <a href='https://example.com/page'>Page 1</a>
                <a href='https://example.com/page?utm_source=twitter'>Page 2</a>
                <a href='https://example.com/page?utm_campaign=spring'>Page 3</a>
                <a href='https://example.com/page?utm_source=facebook&utm_campaign=spring'>Page 4</a>
            </body>
        </html>'''
    
    response = DownloadResponse(
        frontier_id='dddddddd-dddd-dddd-dddd-dddddddddddd',
        cost=1.0,
        url='https://example.com',
        canonical_url='https://example.com',
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
    
    # After normalization, all four URLs should be the same, so only one
    # should be added to the frontier (the others are duplicates)
    assert db.insert_frontier_items.call_count == 1
    inserted_items = db.insert_frontier_items.call_args[0][0]
    
    # We should have only 1 item added
    assert len(inserted_items) == 1
    
    # The URL that got added first is the one without parameters
    assert inserted_items[0]['url'] == 'https://example.com/page'
    assert inserted_items[0]['cost'] == 2.0
    
    assert stats_dict['frontier_size'] == 1
