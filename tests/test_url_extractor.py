import pytest

from starbelly.crawl import ExtractItem
from starbelly.url_extractor import extract_urls


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
    item = ExtractItem(base_href, 1.0, 'application/atom+xml', atom_src)
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
    item = ExtractItem(base_href, 1.0, 'text/html', html_src)
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
    item = ExtractItem(base_href, 1.0, 'text/html', html_base_src)
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
    item = ExtractItem(base_href, 1.0, 'application/rss+xml', rss_src)
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
    item = ExtractItem(base_href, 1.0, 'application/xhtml+xml', xhtml_src)
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
    item = ExtractItem(base_href, 1.0, 'bogus/mime', b'')
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
    item = ExtractItem(base_href, 1.0, 'text/html', html_src)
    expected_links = set([
        'http://partner.computer.com',
    ])
    actual_links = set(extract_urls(item))
    assert actual_links == expected_links

