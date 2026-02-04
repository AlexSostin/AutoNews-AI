"""
RSS Feed Aggregator Module

Fetches and processes RSS/Atom feeds from automotive sources.
"""
import feedparser
import hashlib
import logging
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional, List, Dict
from django.utils import timezone
from news.models import RSSFeed, PendingArticle

logger = logging.getLogger(__name__)


class RSSAggregator:
    """
    Handles RSS feed fetching, parsing, and deduplication.
    """
    
    SIMILARITY_THRESHOLD = 0.80  # 80% title similarity = duplicate
    
    def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Parse RSS/Atom feed and return parsed data.
        
        Args:
            feed_url: URL of the RSS/Atom feed
            
        Returns:
            Parsed feed data or None if error
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return None
            
            logger.info(f"Successfully fetched {len(feed.entries)} entries from {feed_url}")
            return feed
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return None
    
    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA256 hash of content for deduplication.
        
        Args:
            content: Text content to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity ratio between two titles.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
    
    def is_duplicate(self, title: str, content: str, days_back: int = 30) -> bool:
        """
        Check if article is a duplicate based on title similarity or content hash.
        
        Args:
            title: Article title
            content: Article content
            days_back: Number of days to check for duplicates
            
        Returns:
            True if duplicate found, False otherwise
        """
        content_hash = self.calculate_content_hash(content)
        
        # Check content hash first (exact match)
        if PendingArticle.objects.filter(content_hash=content_hash).exists():
            logger.info(f"Duplicate found by content hash: {title[:50]}")
            return True
        
        # Check title similarity in recent articles
        cutoff_date = timezone.now() - timedelta(days=days_back)
        recent_articles = PendingArticle.objects.filter(
            created_at__gte=cutoff_date
        ).values_list('title', flat=True)
        
        for existing_title in recent_articles:
            similarity = self.calculate_title_similarity(title, existing_title)
            if similarity >= self.SIMILARITY_THRESHOLD:
                logger.info(f"Duplicate found by title similarity ({similarity:.2%}): {title[:50]}")
                return True
        
        return False
    
    def extract_images(self, entry: Dict) -> List[str]:
        """
        Extract image URLs from RSS entry.
        
        Checks multiple possible locations:
        - media:content
        - enclosure
        - content (HTML parsing)
        - description (HTML parsing)
        
        Args:
            entry: RSS feed entry
            
        Returns:
            List of image URLs
        """
        images = []
        
        # Check media:content (common in RSS 2.0)
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                    images.append(media.get('url'))
        
        # Check media:thumbnail
        if hasattr(entry, 'media_thumbnail'):
            for thumb in entry.media_thumbnail:
                images.append(thumb.get('url'))
        
        # Check enclosure
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('image/'):
                    images.append(enclosure.get('href'))
        
        # Check for images in content/description (basic extraction)
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                content = getattr(entry, field)
                if isinstance(content, list):
                    content = content[0].get('value', '')
                
                # Simple image URL extraction (can be improved with BeautifulSoup)
                import re
                img_urls = re.findall(r'<img[^>]+src="([^"]+)"', str(content))
                images.extend(img_urls)
        
        # Remove duplicates and empty strings
        images = list(filter(None, dict.fromkeys(images)))
        
        logger.debug(f"Extracted {len(images)} images from entry")
        return images
    
    def extract_content(self, entry: Dict) -> str:
        """
        Extract text content from RSS entry.
        
        Args:
            entry: RSS feed entry
            
        Returns:
            Cleaned text content
        """
        # Try content first, then summary, then description
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                content = getattr(entry, field)
                if isinstance(content, list):
                    content = content[0].get('value', '')
                
                if content:
                    # Basic HTML tag removal (can be improved)
                    import re
                    text = re.sub(r'<[^>]+>', '', str(content))
                    text = text.strip()
                    return text
        
        return ""
    
    def parse_entry_date(self, entry: Dict) -> Optional[datetime]:
        """
        Extract publication date from RSS entry.
        
        Args:
            entry: RSS feed entry
            
        Returns:
            Datetime object or None
        """
        for field in ['published_parsed', 'updated_parsed']:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        dt = datetime(*time_struct[:6])
                        return timezone.make_aware(dt)
                    except:
                        pass
        
        return None
    
    def process_feed(self, rss_feed: RSSFeed, limit: int = 10) -> int:
        """
        Process RSS feed and create PendingArticles.
        
        Args:
            rss_feed: RSSFeed model instance
            limit: Maximum number of entries to process
            
        Returns:
            Number of articles created
        """
        feed_data = self.fetch_feed(rss_feed.feed_url)
        if not feed_data:
            return 0
        
        created_count = 0
        
        for entry in feed_data.entries[:limit]:
            try:
                title = entry.get('title', 'Untitled')
                content = self.extract_content(entry)
                source_url = entry.get('link', '')
                
                # Skip if no content
                if not content or len(content) < 100:
                    logger.debug(f"Skipping entry with insufficient content: {title[:50]}")
                    continue
                
                # Check for duplicates
                if self.is_duplicate(title, content):
                    logger.debug(f"Skipping duplicate: {title[:50]}")
                    continue
                
                # Extract images
                images = self.extract_images(entry)
                featured_image = images[0] if images else ''
                
                # Calculate content hash
                content_hash = self.calculate_content_hash(content)
                
                # Get publication date
                pub_date = self.parse_entry_date(entry)
                
                # Create PendingArticle (will be enhanced by AI later)
                pending = PendingArticle.objects.create(
                    rss_feed=rss_feed,
                    source_url=source_url,
                    content_hash=content_hash,
                    title=title,
                    content=content,  # Will be expanded by AI
                    excerpt=content[:500] if len(content) > 500 else content,
                    images=images,
                    featured_image=featured_image,
                    suggested_category=rss_feed.default_category,
                    status='pending'
                )
                
                created_count += 1
                logger.info(f"Created PendingArticle: {title[:50]}")
                
                # Update last_entry_date if this entry is newer
                if pub_date and (not rss_feed.last_entry_date or pub_date > rss_feed.last_entry_date):
                    rss_feed.last_entry_date = pub_date
                
            except Exception as e:
                logger.error(f"Error processing RSS entry: {e}")
                continue
        
        # Update feed tracking
        rss_feed.last_checked = timezone.now()
        rss_feed.entries_processed += created_count
        rss_feed.save()
        
        logger.info(f"Processed {created_count} new articles from {rss_feed.name}")
        return created_count
