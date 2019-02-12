import logging

from bs4 import BeautifulSoup
import cchardet
import feedparser
import mimeparse
import w3lib.encoding
import yarl


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


class CrawlExtractor:
    ''' Extract URLs from crawled items and add them to the frontier table. '''
    def __init__(self, job_id, receive_channel, policy, old_urls):
        '''
        Constructor.

        :param str job_id: The ID of the job to extract response for.
        :param trio.ReceiveChannel receive_channel: A channel that receives
            DownloadResponse instances.
        :param starbelly.policy.Policy: A policy for computing costs.
        :param old_urls: A set of hashed URLs that this crawl has seen before.
            These URLs will not be added to the crawl frontier a second time.
        '''
        self._job_id = job_id
        self._receive_channel = receive_channel
        self._policy = policy
        self._old_urls = old_urls

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<CrawlJob job_id={}>'.format(self._job_id[:8])

    async def run(self):
        '''
        Read responses from extraction channel and add them to the frontier.

        :returns: This function runs until cancelled.
        '''
        async for response in self._receive_channel:
            try:
                await self._extract(response)
            except Exception as e:
                logger.exception('%r Extractor exception', self)
            finally:
                delete_query = (
                    r.table('frontier')
                     .get(response.frontier_id)
                     .delete()
                )
                async with self._db_pool.connection() as conn:
                    await delete_query.run(conn)

    async def _extract(self, response):
        '''
        Find links in a response body and put them in the frontier.

        :param starbelly.downloader.DownloadReponse:
        '''
        logger.debug('%r Extracting links from %s', self, response.url)
        extracted_urls = await trio.run_sync_in_worker_thread(
            extract_urls, response)

        frontier_items = list()
        insert_items = list()

        for counter, url in enumerate(extracted_urls):
            new_cost = self._policy.url_rules.get_cost(response.cost, url)
            exceeds_max_cost = self._policy.limits.exceeds_max_cost(new_cost)
            if (new_cost > 0 and not exceeds_max_cost):
                frontier_items.append((url, new_cost))

            # Don't monopolize the event loop:
            if counter % 100 == 99:
                await trio.sleep(0)

        for url, new_cost in frontier_items:
            url_can = self.policy.url_normalization.normalize(url)
            hash_ = hashlib.blake2b(url_can.encode('ascii'), digest_size=16)
            url_hash = hash_.digest()

            if url_hash not in self._old_urls:
                logger.debug('%r Adding URL %s (cost=%0.2f)', self, url,
                    new_cost)
                insert_items.append({
                    'cost': frontier_item.cost,
                    'job_id': self.id,
                    'url': frontier_item.url,
                })
                self._old_urls.add(url_hash)

        if len(insert_items) > 0:
            async with self._db_pool.connection() as conn:
                await r.table('frontier').insert(insert_items).run(conn)


def extract_urls(response):
    '''
    Extract URLs from a response body.

    Any relative URLs found in the response body are converted to absolute URLs
    using the original request URL.

    :param starbelly.downloader.DownloadResponse response: A response to
        extract URLs from.
    '''

    extracted_urls = list()
    base_url = response.url
    type_, subtype, parameters = mimeparse.parse_mime_type(
        response.content_type)

    if type_ == 'text' and subtype == 'html' or \
       type_ == 'application' and subtype == 'xhtml+xml':
        extracted_urls = _extract_html(response)
    elif type_ == 'application' and subtype == 'atom+xml' or \
         type_ == 'application' and subtype == 'rss+xml':
        extracted_urls = _extract_feed(response)
    else:
        raise ValueError('Unsupported MIME in extract_urls(): {} (url={})'
            .format(response.content_type, base_url))

    return extracted_urls


def _extract_feed(response):
    '''
    Extract links from Atom or RSS feeds.

    :param starbelly.downloader.DownloadResponse response: An Atom/RSS response
        to extract URLs from.
    '''

    doc = feedparser.parse(response.body)
    return [entry.link for entry in doc.entries]


def _extract_html(response):
    '''
    Extract links from HTML document <a> tags.

    :param starbelly.downloader.DownloadResponse response: An HTML response to
        extract URLs from.
    '''

    encoding, html = w3lib.encoding.html_to_unicode(
        response.content_type,
        response.body,
        auto_detect_fun=chardet
    )

    doc = BeautifulSoup(html, 'lxml')
    base_tag = doc.head.base
    base_url = None

    if base_tag is not None:
        base_href = base_tag.get('href')
        if base_href is not None:
            base_url = yarl.URL(base_href)

    if base_url is None:
        base_url = yarl.URL(response.url)

    extracted_urls = list()

    for anchor in doc.find_all('a', href=True):
        href = anchor.get('href')

        try:
            parsed_href = yarl.URL(href)
        except:
            logger.exception('Rejecting malformed URL base=%s url=%s',
                str(response.url), href)
            continue

        absolute_href = base_url.join(parsed_href)

        if absolute_href.scheme in ('http', 'https'):
            extracted_urls.append(str(absolute_href))

    return extracted_urls
