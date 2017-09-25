import logging

from bs4 import BeautifulSoup
import cchardet
import feedparser
import mimeparse
import w3lib.encoding
import yarl


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


def extract_urls(extract_item):
    '''
    Extract URLs from a response body.

    Any relative URLs found in the response body are converted to absolute URLs
    using the original request URL.
    '''

    extracted_urls = list()
    base_url = extract_item.url
    type_, subtype, parameters = mimeparse.parse_mime_type(
        extract_item.content_type)

    try:
        if type_ == 'text' and subtype == 'html' or \
           type_ == 'application' and subtype == 'xhtml+xml':
            extracted_urls = _extract_html(extract_item)
        elif type_ == 'application' and subtype == 'atom+xml' or \
             type_ == 'application' and subtype == 'rss+xml':
            extracted_urls = _extract_feed(extract_item)
        else:
            logging.error(
                'Unsupported MIME in extract_urls(): %s (url=%s)',
                extract_item.content_type, base_url)
    except:
        logger.exception('Cannot extract URLs from %s', base_url)

    return extracted_urls


def _extract_feed(extract_item):
    ''' Extract links from Atom or RSS feeds. '''

    doc = feedparser.parse(extract_item.body)
    return [entry.link for entry in doc.entries]


def _extract_html(extract_item):
    ''' Extract links from HTML document <a> tags. '''

    encoding, html = w3lib.encoding.html_to_unicode(
        extract_item.content_type,
        extract_item.body,
        auto_detect_fun=chardet
    )

    base_url = yarl.URL(extract_item.url)
    doc = BeautifulSoup(html, 'lxml')
    extracted_urls = list()

    for anchor in doc.find_all('a', href=True):
        href = anchor.get('href')

        try:
            parsed_href = yarl.URL(href)
        except:
            logger.exception('Rejecting malformed URL base=%s url=%s',
                str(extract_item.url), href)
            continue

        absolute_href = base_url.join(parsed_href)

        if absolute_href.scheme in ('http', 'https'):
            extracted_urls.append(str(absolute_href))

    return extracted_urls
