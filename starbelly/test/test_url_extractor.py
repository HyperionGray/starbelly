import unittest

from ..crawl import ExtractItem
from ..url_extractor import extract_urls


_html1 = b'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Test document</title>
</head>
<body>
<p>
    <a href='./netbooks/'>Netbooks</a>
    <a href='../desktops/'>Desktops</a>
</p>
<p>
    <a href='http://partner.computer.com'>Partners</a>
</p>
</body>
</html>
'''

class TestUrlExtractor(unittest.TestCase):
    def test_html(self):
        ''' Parse links from HTML. '''
        item = ExtractItem(
            'http://computer.com/laptops/',
            1.0,
            'text/html',
            _html1
        )
        expected_links = [
            'http://computer.com/laptops/netbooks/',
            'http://computer.com/desktops/',
            'http://partner.computer.com',
        ]
        actual_links = extract_urls(item)
        self.assertEqual(expected_links, actual_links)
