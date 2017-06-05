import logging
from urllib.parse import urljoin

import lxml.html
import mimeparse


logger = logging.getLogger(__name__)


def extract_urls(download_response):
    '''
    Extract URLs from a download response.

    Any relative URLs found in the response body are converted to absolute URLs
    using the original request URL.
    '''

    base_url = download_response.url
    type_, subtype, parameters = mimeparse.parse_mime_type(
        download_response.content_type)

    if type_ == 'text' and subtype == 'html':
        extracted_urls = _extract_html(base_url, download_response.body)
    else:
        logging.error('Unsupported MIME in extract_urls(): %s/%s (params=%r)'
                      ' (url=%s)',
            type_, subtype, parameters, base_url)
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
