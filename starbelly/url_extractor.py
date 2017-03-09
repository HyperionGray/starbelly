from urllib.parse import urljoin

import lxml.html
import mimeparse


def extract_urls(crawl_item):
    '''
    Extract URLs from a crawl item.

    Any relative URLs found in the item's body are resolved relative to
    ``crawl_item.url``.
    '''

    #TODO expand content_type system.
    extracted = list()

    base_url = crawl_item.url
    content_type = crawl_item.headers.get('content-type',
        'application/octet-stream')
    type_, subtype, parameters = mimeparse.parse_mime_type(content_type)

    if type_ == 'text' and subtype == 'html':
        doc = lxml.html.document_fromstring(crawl_item.body)
        doc.make_links_absolute(base_url, resolve_base_href=True)
        for el, attr, url, pos in doc.iterlinks():
            #TODO
            if el.tag == 'a' and url.startswith('http') and 'markhaa.se' in url and url.endswith('.html'):
            # if el.tag == 'a' and url.startswith('http'):
                extracted.append(url)

    return extracted
