'''
Parse XML sitemaps and extract URLs.

This module provides functionality to parse sitemap files (both regular sitemaps
and sitemap index files) and extract the URLs they contain.
'''
import logging
from xml.etree import ElementTree as ET
from typing import List

logger = logging.getLogger(__name__)

# XML namespaces used in sitemaps
SITEMAP_NAMESPACES = {
    'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
    '': 'http://www.sitemaps.org/schemas/sitemap/0.9',
}


def parse_sitemap(content: bytes) -> List[str]:
    '''
    Parse a sitemap XML file and extract all URLs.
    
    Handles both regular sitemaps (with <url> tags) and sitemap index files
    (with <sitemap> tags).
    
    :param bytes content: The XML content of the sitemap
    :returns: List of URLs found in the sitemap
    :rtype: list[str]
    '''
    urls = []
    
    try:
        # Parse the XML content
        root = ET.fromstring(content)
        
        # Check if this is a sitemap index (contains <sitemap> tags)
        # or a regular sitemap (contains <url> tags)
        
        # Try to find sitemap entries (for sitemap index files)
        sitemap_locs = []
        for namespace in ['', 'sm']:
            ns_prefix = f'{{{SITEMAP_NAMESPACES[namespace]}}}' if namespace else ''
            sitemap_locs.extend(root.findall(f'.//{ns_prefix}sitemap/{ns_prefix}loc'))
        
        if sitemap_locs:
            # This is a sitemap index file
            logger.debug('Found sitemap index with %d sitemaps', len(sitemap_locs))
            for loc in sitemap_locs:
                if loc.text:
                    urls.append(loc.text.strip())
        else:
            # Try to find URL entries (for regular sitemap files)
            url_locs = []
            for namespace in ['', 'sm']:
                ns_prefix = f'{{{SITEMAP_NAMESPACES[namespace]}}}' if namespace else ''
                url_locs.extend(root.findall(f'.//{ns_prefix}url/{ns_prefix}loc'))
            
            if url_locs:
                logger.debug('Found regular sitemap with %d URLs', len(url_locs))
                for loc in url_locs:
                    if loc.text:
                        urls.append(loc.text.strip())
            else:
                logger.warning('Sitemap contains neither <url> nor <sitemap> tags')
    
    except ET.ParseError as e:
        logger.error('Failed to parse sitemap XML: %s', e)
    except Exception as e:
        logger.error('Unexpected error parsing sitemap: %s', e)
    
    return urls


def parse_sitemap_text(content: str) -> List[str]:
    '''
    Parse a sitemap from text content.
    
    :param str content: The text content of the sitemap
    :returns: List of URLs found in the sitemap
    :rtype: list[str]
    '''
    return parse_sitemap(content.encode('utf-8'))
