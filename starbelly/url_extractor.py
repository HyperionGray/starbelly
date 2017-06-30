import logging
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import mimeparse


logger = logging.getLogger(__name__)


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
        charset = parameters.get('charset', 'utf8')
        extracted_urls = _extract_html(base_url, charset, extract_item.body)
    else:
        logging.error('Unsupported MIME in extract_urls(): %s/%s (params=%r)'
                      ' (url=%s)',
            type_, subtype, parameters, base_url)
        extracted_urls = list()

    return extracted_urls


def _extract_html(base_url, charset, body):
    ''' Extract links from HTML document <a> tags. '''
    doc = BeautifulSoup(body, 'lxml')
    extracted_urls = list()

    for anchor in doc.find_all('a', href=True):
        absolute_url = urljoin(base_url, anchor['href'], allow_fragments=False)

        try:
            parsed = urlparse(absolute_url)
        except:
            continue

        if parsed.scheme == 'http' or parsed.scheme == 'https':
            extracted_urls.append(absolute_url)

    return extracted_urls
