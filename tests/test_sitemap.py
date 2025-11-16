'''
Tests for sitemap parsing functionality.
'''
import pytest

from starbelly.sitemap import parse_sitemap, parse_sitemap_text


def test_parse_regular_sitemap():
    '''Parse a regular sitemap with URL entries.'''
    sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2023-01-01</lastmod>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
  </url>
  <url>
    <loc>https://example.com/page3</loc>
  </url>
</urlset>'''
    
    urls = parse_sitemap(sitemap_xml)
    assert len(urls) == 3
    assert 'https://example.com/page1' in urls
    assert 'https://example.com/page2' in urls
    assert 'https://example.com/page3' in urls


def test_parse_sitemap_index():
    '''Parse a sitemap index file with nested sitemap references.'''
    sitemap_index_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap1.xml</loc>
    <lastmod>2023-01-01</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap2.xml</loc>
  </sitemap>
</sitemapindex>'''
    
    urls = parse_sitemap(sitemap_index_xml)
    assert len(urls) == 2
    assert 'https://example.com/sitemap1.xml' in urls
    assert 'https://example.com/sitemap2.xml' in urls


def test_parse_sitemap_no_namespace():
    '''Parse a sitemap without namespace declaration.'''
    sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url>
    <loc>https://example.com/page1</loc>
  </url>
</urlset>'''
    
    urls = parse_sitemap(sitemap_xml)
    assert len(urls) == 1
    assert 'https://example.com/page1' in urls


def test_parse_empty_sitemap():
    '''Parse an empty sitemap.'''
    sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>'''
    
    urls = parse_sitemap(sitemap_xml)
    assert len(urls) == 0


def test_parse_invalid_xml():
    '''Parsing invalid XML should return empty list.'''
    invalid_xml = b'This is not XML'
    urls = parse_sitemap(invalid_xml)
    assert len(urls) == 0


def test_parse_sitemap_with_whitespace():
    '''Parse a sitemap with whitespace in URLs.'''
    sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>  https://example.com/page1  </loc>
  </url>
</urlset>'''
    
    urls = parse_sitemap(sitemap_xml)
    assert len(urls) == 1
    assert urls[0] == 'https://example.com/page1'


def test_parse_sitemap_text():
    '''Parse a sitemap from text content.'''
    sitemap_text = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
  </url>
</urlset>'''
    
    urls = parse_sitemap_text(sitemap_text)
    assert len(urls) == 1
    assert 'https://example.com/page1' in urls
