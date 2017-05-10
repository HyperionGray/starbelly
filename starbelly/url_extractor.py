import logging
from urllib.parse import urljoin

import lxml.html
import mimeparse


logger = logging.getLogger(__name__)


def extract_urls(crawl_item):
    '''
    Extract URLs from a crawl item.

    Any relative URLs found in the item's body are resolved relative to
    ``crawl_item.url``.
    '''

    base_url = crawl_item.url
    type_, subtype, parameters = mimeparse.parse_mime_type(
        crawl_item.content_type)

    if type_ == 'text' and subtype == 'html':
        extracted_urls = _extract_html(base_url, crawl_item.body)
    else:
        logging.error('Unsupported MIME in extract_urls(): %s/%s (%r)',
            type_, subtype, parameters)
        extracted_urls = list()

    return extracted_urls


def _extract_html(base_url, body):
    ''' Extract links from HTML document <a> tags. '''
    doc = lxml.html.document_fromstring(body)
    doc.make_links_absolute(base_url, resolve_base_href=True)
    extracted_urls = list()

    for el, attr, url, pos in doc.iterlinks():
        if el.tag == 'a' and \
            (url.startswith('http:') or url.startswith('https:')):

            extracted_urls.append(url)

    return extracted_urls
