import logging
from urllib.parse import urljoin, urlparse

import cchardet
import lxml.html
import mimeparse
import w3lib.encoding


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


def extract_urls(extract_item):
    '''
    Extract URLs from a response body.

    Any relative URLs found in the response body are converted to absolute URLs
    using the original request URL.
    '''

    base_url = extract_item.url
    type_, subtype, parameters = mimeparse.parse_mime_type(
        extract_item.content_type)

    if type_ == 'text' and subtype == 'html':
        extracted_urls = _extract_html(extract_item)
    else:
        logging.error('Unsupported MIME in extract_urls(): %s/%s (params=%r)'
                      ' (url=%s)',
            type_, subtype, parameters, base_url)
        extracted_urls = list()

    return extracted_urls


def _extract_html(extract_item):
    ''' Extract links from HTML document <a> tags. '''

    encoding, html = w3lib.encoding.html_to_unicode(
        extract_item.content_type,
        extract_item.body,
        auto_detect_fun=chardet
    )

    base_url = extract_item.url
    doc = lxml.html.document_fromstring(html)
    extracted_urls = list()

    for anchor in doc.xpath('//a'):
        try:
            absolute_url = urljoin(base_url, anchor.get('href'),
                allow_fragments=False)
            parsed = urlparse(absolute_url)
            # Reject URLs with invalid character encoding.
            absolute_url.encode('ascii')
        except:
            continue

        if parsed.scheme == 'http' or parsed.scheme == 'https':
            extracted_urls.append(absolute_url)

    return extracted_urls
