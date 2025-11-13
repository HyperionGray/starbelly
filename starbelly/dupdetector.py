"""
Duplicate content detection using MaybeDont library.

This module provides functionality to detect and prevent crawling of duplicate
content based on URL patterns and content similarity.
"""
import logging
from bs4 import BeautifulSoup
try:
    import cchardet
    chardet = lambda s: cchardet.detect(s).get('encoding')
except ImportError:
    import chardet as chardet_module
    chardet = lambda s: chardet_module.detect(s).get('encoding')
import mimeparse
import w3lib.encoding

try:
    from maybedont import DupePredictor
    MAYBEDONT_AVAILABLE = True
except ImportError:
    MAYBEDONT_AVAILABLE = False


logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate content during crawling using MaybeDont's DupePredictor.
    
    This detector learns from downloaded pages to predict if new URLs will
    contain duplicate content based on URL patterns.
    """
    
    def __init__(self, enabled=True, jaccard_threshold=0.9, min_confidence=0.5):
        """
        Initialize the duplicate detector.
        
        :param bool enabled: Whether duplicate detection is enabled
        :param float jaccard_threshold: Minimum jaccard similarity for duplicates (0-1)
        :param float min_confidence: Minimum confidence threshold to skip a URL (0-1)
        """
        self._enabled = enabled and MAYBEDONT_AVAILABLE
        self._jaccard_threshold = jaccard_threshold
        self._min_confidence = min_confidence
        self._predictor = None
        
        if self._enabled:
            self._predictor = DupePredictor(
                jaccard_threshold=self._jaccard_threshold,
                texts_sample=None  # Will be updated as we crawl
            )
            logger.info('Duplicate detector initialized (threshold=%0.2f, confidence=%0.2f)',
                       jaccard_threshold, min_confidence)
        elif enabled and not MAYBEDONT_AVAILABLE:
            logger.warning('Duplicate detection requested but MaybeDont is not installed')
        else:
            logger.info('Duplicate detector disabled')
    
    @property
    def enabled(self):
        """Return True if duplicate detection is enabled."""
        return self._enabled
    
    def should_skip_url(self, url):
        """
        Check if a URL should be skipped based on duplicate probability.
        
        :param str url: The URL to check
        :returns: True if the URL should be skipped (likely duplicate)
        :rtype: bool
        """
        if not self._enabled:
            return False
        
        try:
            dupe_prob = self._predictor.get_dupe_prob(url)
            should_skip = dupe_prob >= self._min_confidence
            
            if should_skip:
                logger.debug('Skipping likely duplicate URL %s (prob=%0.2f)', 
                           url, dupe_prob)
            
            return should_skip
        except Exception:
            logger.exception('Error checking duplicate probability for %s', url)
            return False
    
    def update_model(self, response):
        """
        Update the duplicate detection model with a downloaded page.
        
        :param starbelly.downloader.DownloadResponse response: A successful response
        """
        if not self._enabled or not response.is_success:
            return
        
        try:
            # Extract text content from the response
            text = self._extract_text(response)
            if text:
                url = str(response.url)
                self._predictor.update_model(url, text)
                logger.debug('Updated duplicate detector model with %s', url)
        except Exception:
            logger.exception('Error updating duplicate detector model for %s', 
                           response.url)
    
    def _extract_text(self, response):
        """
        Extract text content from a response for duplicate detection.
        
        :param starbelly.downloader.DownloadResponse response: A response
        :returns: Extracted text content or None
        :rtype: str or None
        """
        type_, subtype, _ = mimeparse.parse_mime_type(response.content_type)
        
        # Only process HTML content for now
        if not (type_ == 'text' and subtype == 'html'):
            return None
        
        try:
            # Detect encoding
            encoding = w3lib.encoding.html_to_unicode(
                response.content_type, 
                response.body, 
                auto_detect_fun=chardet
            )[0]
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.body, 'lxml', from_encoding=encoding)
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            return text
        except Exception:
            logger.exception('Error extracting text from %s', response.url)
            return None
