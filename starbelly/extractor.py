import hashlib
import logging

from bs4 import BeautifulSoup
import cchardet
import feedparser
import mimeparse
import trio
import w3lib.encoding
import yarl


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


class CrawlExtractor:
    ''' Extract URLs from crawled items and add them to the frontier table. '''
    def __init__(self, job_id, db, send_channel, receive_channel, policy,
            robots_txt_manager, old_urls, stats, batch_size=100):
        '''
        Constructor.

        :param str job_id: The ID of the job to extract response for.
        :param starbelly.db.CrawlExtractorDb db: A database layer.
        :param trio.SendChannel send_channel: A channel that sends
            DownloadResponse instances.
        :param trio.ReceiveChannel receive_channel: A channel that receives
            DownloadResponse instances.
        :param starbelly.policy.Policy: A policy for computing costs.
        :param starbelly.robots.RobotsTxtManager: A robots.txt manager.
        :param set old_urls: A set of hashed URLs that this crawl has seen before.
            These URLs will not be added to the crawl frontier a second time.
        :param dict stats: A dictionary of crawl statistics.
        :param int batch_size: The maximum size of inserts to do in a single
            database query. If more items than this are extracted from a
            document, then multiple queries will be issued.
        '''
        self._job_id = job_id
        self._db = db
        self._send_channel = send_channel
        self._receive_channel = receive_channel
        self._policy = policy
        self._robots_txt_manager = robots_txt_manager
        self._old_urls = old_urls
        self._stats = stats
        self._batch_size = batch_size

    def __repr__(self):
        ''' Report crawl job ID. '''
        return '<CrawlExtractor job_id={}>'.format(self._job_id[:8])

    @property
    def old_urls(self):
        return self._old_urls

    async def run(self):
        '''
        Read responses from extraction channel and add them to the frontier.

        :returns: This function runs until cancelled.
        '''
        async for response in self._receive_channel:
            try:
                await self._extract(response)
            except Exception as e:
                logger.exception('%r Extractor exception on %r', self, response)
            finally:
                await self._db.delete_frontier_item(response.frontier_id)
                await self._send_channel.send(response)

    async def _extract(self, response):
        '''
        Find links in a response body and put them in the frontier.

        :param starbelly.downloader.DownloadReponse:
        '''
        logger.debug('%r Extracting links from %s', self, response.url)
        extracted_urls = await trio.run_sync_in_worker_thread(
            extract_urls, response)
        insert_items = list()

        for counter, url in enumerate(extracted_urls):
            # Check if the policy allows us to follow this URL.
            new_cost = self._policy.url_rules.get_cost(response.cost, url)
            exceeds_max_cost = self._policy.limits.exceeds_max_cost(new_cost)
            if new_cost <= 0 or exceeds_max_cost:
                continue
            robots_ok = await self._robots_txt_manager.is_allowed(url)
            if not robots_ok:
                continue

            # Normalize and hash URL.
            url_can = self._policy.url_normalization.normalize(url)
            hash_ = hashlib.blake2b(url_can.encode('ascii'), digest_size=16)
            url_hash = hash_.digest()

            # If we haven't seen this URL before, it should be added to the
            # frontier.
            if url_hash not in self._old_urls:
                logger.debug('%r Adding URL %s (cost=%0.2f)', self, url,
                    new_cost)
                insert_items.append({
                    'cost': new_cost,
                    'job_id': self._job_id,
                    'url': url,
                    'in_flight': False,
                })
                self._old_urls.add(url_hash)

            # Don't monopolize the event loop:
            if counter % self._batch_size == self._batch_size - 1:
                await trio.sleep(0)


        # Insert items in batches
        start = 0
        while start < len(insert_items):
            end = min(start + self._batch_size, len(insert_items))
            self._stats['frontier_size'] += end - start
            await self._db.insert_frontier_items(insert_items[start:end])
            start = end


def extract_urls(response):
    '''
    Extract URLs from a response body.

    Any relative URLs found in the response body are converted to absolute URLs
    using the original request URL.

    :param starbelly.downloader.DownloadResponse response: A response to
        extract URLs from.
    :returns: A list of URLs.
    :rtype: list[str]
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
    :returns: A list of URLs.
    :rtype: list[str]
    '''
    doc = feedparser.parse(response.body)
    return [entry.link for entry in doc.entries]


def _extract_html(response):
    '''
    Extract links from HTML document <a> tags.

    :param starbelly.downloader.DownloadResponse response: An HTML response to
        extract URLs from.
    :returns: A list of URLs.
    :rtype: list[str]
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
