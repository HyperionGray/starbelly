import unittest

from ..crawl import ExtractItem
from ..url_extractor import extract_urls


_html1 = '''<!DOCTYPE html>
<html>
    <head><meta charset="UTF-8"><title>Test document</title></head>
    <body>
        <p>
            <a href='./netbooks/'>Netbooks</a>
            <a href="../desktops/">Desktops</a>
        </p>
        <p>
            <a href='http://partner.computer.com'>Partners</a>
        </p>
    </body>
</html>
'''.encode('utf8')


class TestUrlExtractor(unittest.TestCase):
    def test_html(self):
        '''
        Parse links from HTML anchor tags.

        Skip links containing non-ASCII characters.
        '''
        base_href = 'http://computer.com/laptops/'
        item = ExtractItem(base_href, 1.0, 'text/html', _html1)
        expected_links = set([
            'http://computer.com/laptops/netbooks/',
            'http://computer.com/desktops/',
            'http://partner.computer.com',
        ])
        actual_links = set(extract_urls(item))
        self.assertEqual(actual_links, expected_links)
