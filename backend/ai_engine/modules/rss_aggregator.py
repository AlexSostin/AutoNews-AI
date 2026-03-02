"""
RSS Feed Aggregator Module

Fetches and processes RSS/Atom feeds from automotive sources.
"""
import feedparser
import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Optional, List, Dict
from django.utils import timezone
from news.models import RSSFeed, PendingArticle, Article

logger = logging.getLogger(__name__)


def _retry_ai_call(func, *args, max_retries=3, **kwargs):
    """
    Retry wrapper for AI API calls with exponential backoff.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            wait_time = (2 ** attempt) + 1  # 1s, 3s, 5s
            logger.warning(f"AI call failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
    raise last_error


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
    
    def is_duplicate(self, title: str, content: str, source_url: str = '', days_back: int = 30) -> bool:
        """
        Check if article is a duplicate based on title similarity, content hash,
        or source URL. Checks RSSNewsItem, PendingArticle AND published Article tables.
        
        Args:
            title: Article title
            content: Article content
            source_url: Original source URL
            days_back: Number of days to check for duplicates
            
        Returns:
            True if duplicate found, False otherwise
        """
        from news.models import RSSNewsItem
        
        content_hash = self.calculate_content_hash(content)
        
        # 0. Check content hash and source URL in RSSNewsItem
        if RSSNewsItem.objects.filter(content_hash=content_hash).exists():
            logger.info(f"Duplicate found by content hash (news item): {title[:50]}")
            return True
        if source_url and RSSNewsItem.objects.filter(source_url=source_url).exists():
            logger.info(f"Duplicate found by source URL (news item): {title[:50]}")
            return True
        
        # 1. Check content hash in PendingArticle (exact content match)
        if PendingArticle.objects.filter(content_hash=content_hash).exists():
            logger.info(f"Duplicate found by content hash (pending): {title[:50]}")
            return True
        
        # 2. Check source URL in both tables
        if source_url:
            if PendingArticle.objects.filter(source_url=source_url).exists():
                logger.info(f"Duplicate found by source URL (pending): {title[:50]}")
                return True
            # Article model may not have source_url field
            try:
                if Article.objects.filter(source_url=source_url, is_deleted=False).exists():
                    logger.info(f"Duplicate found by source URL (published): {title[:50]}")
                    return True
            except Exception:
                pass  # Article model doesn't have source_url field
        
        # 3. Check title similarity in recent RSSNewsItems
        cutoff_date = timezone.now() - timedelta(days=days_back)
        recent_news_items = RSSNewsItem.objects.filter(
            created_at__gte=cutoff_date
        ).values_list('title', flat=True)
        
        for existing_title in recent_news_items:
            similarity = self.calculate_title_similarity(title, existing_title)
            if similarity >= self.SIMILARITY_THRESHOLD:
                logger.info(f"Duplicate found by title similarity (news item, {similarity:.2%}): {title[:50]}")
                return True
        
        # 4. Check title similarity in recent PendingArticles
        recent_pending = PendingArticle.objects.filter(
            created_at__gte=cutoff_date
        ).values_list('title', flat=True)
        
        for existing_title in recent_pending:
            similarity = self.calculate_title_similarity(title, existing_title)
            if similarity >= self.SIMILARITY_THRESHOLD:
                logger.info(f"Duplicate found by title similarity (pending, {similarity:.2%}): {title[:50]}")
                return True
        
        # 5. Check title similarity in published Articles
        recent_articles = Article.objects.filter(
            created_at__gte=cutoff_date,
            is_deleted=False
        ).values_list('title', flat=True)
        
        for existing_title in recent_articles:
            similarity = self.calculate_title_similarity(title, existing_title)
            if similarity >= self.SIMILARITY_THRESHOLD:
                logger.info(f"Duplicate found by title similarity (published, {similarity:.2%}): {title[:50]}")
                return True
    
        # 6. ML content similarity — catches same-topic articles with different titles
        try:
            from ai_engine.modules.content_recommender import is_available, _load_model, _clean_text
            if is_available() and content and len(content) > 100:
                model = _load_model()
                if model:
                    query_text = _clean_text(f"{title} {content[:2000]}")
                    query_vec = model['vectorizer'].transform([query_text])
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarities = cosine_similarity(query_vec, model['tfidf_matrix']).flatten()
                    max_sim = float(similarities.max()) if len(similarities) > 0 else 0
                    if max_sim > 0.65:
                        best_idx = int(similarities.argmax())
                        similar_id = model['article_ids'][best_idx]
                        logger.info(f"Duplicate found by ML content similarity ({max_sim:.2%}, article {similar_id}): {title[:50]}")
                        return True
        except Exception as e:
            logger.debug(f"ML content similarity check skipped: {e}")
        
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
    
    def extract_og_image(self, url: str) -> Optional[str]:
        """
        Scrape og:image or twitter:image from an article's source page.
        
        Most news sites include Open Graph meta tags with article images.
        This provides real article images rather than stock photos.
        
        Args:
            url: Source article URL
            
        Returns:
            Image URL or None
        """
        if not url:
            return None
            
        try:
            import requests as req
            from bs4 import BeautifulSoup
            
            resp = req.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; AutoNewsBot/1.0)'
            })
            
            if resp.status_code not in (200, 404):  # Some sites return 404 but still have og:image
                if resp.status_code >= 400:
                    logger.debug(f"Failed to fetch {url}: status {resp.status_code}")
                    return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Try og:image first (most common)
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                img_url = og['content']
                # Skip generic/placeholder images
                if not any(skip in img_url.lower() for skip in ['placeholder', 'default', 'logo', 'favicon', '1x1']):
                    logger.info(f"Found og:image for {url[:60]}: {img_url[:80]}")
                    return img_url
            
            # Try twitter:image
            tw = soup.find('meta', attrs={'name': 'twitter:image'})
            if tw and tw.get('content'):
                img_url = tw['content']
                if not any(skip in img_url.lower() for skip in ['placeholder', 'default', 'logo', 'favicon', '1x1']):
                    logger.info(f"Found twitter:image for {url[:60]}: {img_url[:80]}")
                    return img_url
            
            # Try first large content image
            for img in soup.find_all('img', src=True):
                src = img['src']
                if src.startswith('data:') or 'logo' in src.lower() or 'icon' in src.lower():
                    continue
                # Make relative URLs absolute
                if src.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                if src.startswith('http'):
                    logger.info(f"Found content image for {url[:60]}: {src[:80]}")
                    return src
            
            logger.debug(f"No images found on page: {url[:60]}")
            return None
            
        except Exception as e:
            logger.warning(f"Error scraping og:image from {url[:60]}: {e}")
            return None
    
    def convert_plain_text_to_html(self, text: str) -> str:
        """
        Convert plain text to HTML with proper formatting.
        
        - Decodes HTML entities (e.g., &nbsp;, &#8217;)
        - Splits text into paragraphs (double newlines)
        - Wraps each paragraph in <p> tags
        - Converts URLs to clickable links
        - Preserves single newlines as <br>
        
        Args:
            text: Plain text content
            
        Returns:
            HTML-formatted content
        """
        import re
        import html
        
        # Decode HTML entities first (e.g., &nbsp; -> space, &#8217; -> ')
        text = html.unescape(text)
        
        # Split by double newlines to get paragraphs
        paragraphs = re.split(r'\n\s*\n', text.strip())
        
        html_parts = []
        for para in paragraphs:
            if not para.strip():
                continue
            
            # Convert URLs to links
            para = re.sub(
                r'(https?://[^\s<>"]+)',
                r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
                para
            )
            
            # Replace single newlines with <br>
            para = para.replace('\n', '<br>\n')
            
            # Wrap in paragraph tag
            html_parts.append(f'<p>{para}</p>')
        
        return '\n'.join(html_parts)
    
    def clean_publisher_mentions(self, text: str) -> str:
        """
        Remove publisher self-references from RSS content.
        
        Args:
            text: Plain text content
            
        Returns:
            Cleaned text without publisher mentions
        """
        import re
        
        # Common patterns for publisher mentions
        patterns = [
            # WordPress-style "appeared first on" pattern
            r'The post .+ appeared first on .+\.',
            r'The post .+ appeared first on .+',
            
            # Generic publisher mentions
            r'First published by https?://[^\s]+',
            r'Originally published (?:on|at|by) [^\n]+',
            r'Read more at https?://[^\s]+',
            r'Continue reading at https?://[^\s]+',
            r'Full article at https?://[^\s]+',
            r'\[Continue reading.*?\]',
            
            # Source attribution blocks (multiple variations)
            r'Source: [^\n]+\s*View original article',
            r'Source: [^\n]+\.\s*View original article',
            
            # Learn more / visit links at end
            r'To learn more about .+, visit .+\.',
            r'For more information, visit .+\.',
            
            # Standalone "View original article"
            r'View original article',
        ]
        
        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove multiple blank lines
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def extract_plain_text(self, entry: Dict) -> str:
        """
        Extract plain text content from RSS entry (for excerpts).
        
        Args:
            entry: RSS feed entry
            
        Returns:
            Plain text content (no HTML)
        """
        import re
        import html
        
        # Try content first, then summary, then description
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                content = getattr(entry, field)
                if isinstance(content, list):
                    content = content[0].get('value', '')
                
                if content:
                    # Remove HTML tags
                    text = re.sub(r'<[^>]+>', '', str(content))
                    # Decode HTML entities
                    text = html.unescape(text)
                    text = text.strip()
                    
                    # Clean publisher self-references
                    text = self.clean_publisher_mentions(text)
                    
                    return text
        
        return ""
    
    def extract_content(self, entry: Dict) -> str:
        """
        Extract text content from RSS entry and convert to HTML.
        
        Args:
            entry: RSS feed entry
            
        Returns:
            HTML-formatted content
        """
        # Get plain text first
        text = self.extract_plain_text(entry)
        
        if text:
            # Convert plain text to HTML with paragraphs and links
            html_content = self.convert_plain_text_to_html(text)
            return html_content
        
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
    
    def create_pending_with_ai(self, rss_feed: RSSFeed, entry: Dict, content: str, 
                                images: List[str], content_hash: str) -> Optional[PendingArticle]:
        """
        Create PendingArticle with AI-expanded content from press release.
        
        Args:
            rss_feed: RSSFeed instance
            entry: RSS entry dict
            content: Original press release content
            images: List of image URLs
            content_hash: Content hash for deduplication
            
        Returns:
            Created PendingArticle or None if error
        """
        try:
            from ai_engine.modules.article_generator import expand_press_release
            from ai_engine.main import extract_title, validate_title, _is_generic_header, _contains_non_latin
            
            title = entry.get('title', 'Untitled')
            source_url = entry.get('link', '')
            
            # Check if original title is non-English
            is_non_english_title = _contains_non_latin(title)
            if is_non_english_title:
                logger.info(f"[RSS] Non-English title detected, will force AI title: {title[:50]}")
            
            logger.info(f"Expanding press release with AI: {title[:50]}")
            
            # Expand press release with AI (with retry logic)
            expanded_content = _retry_ai_call(
                expand_press_release,
                press_release_text=content,
                source_url=source_url,
                provider='gemini'
            )
            
            # Extract title from AI-generated content using shared extract_title
            ai_title = extract_title(expanded_content)
            
            # Only fall back to RSS title if AI title failed AND original is in English
            if not ai_title or _is_generic_header(ai_title):
                if is_non_english_title:
                    logger.warning(f"[RSS] AI title extraction failed and original is non-English, using validate_title fallback")
                    ai_title = None  # Force validate_title to construct from specs
                else:
                    ai_title = title  # Use original RSS title (it's English)
            
            # Final validation  
            ai_title = validate_title(ai_title)
            
            # Convert markdown to HTML if AI returned markdown instead of HTML
            if '###' in expanded_content and '<h2>' not in expanded_content:
                try:
                    import markdown
                    logger.info("AI returned markdown instead of HTML, converting...")
                    expanded_content = markdown.markdown(expanded_content, extensions=['fenced_code', 'tables'])
                except Exception as e:
                    logger.warning(f"Markdown conversion failed: {e}, keeping as-is")
            
            # Content quality check: minimum word count
            word_count = len(re.sub(r'<[^>]+>', '', expanded_content).split())
            if word_count < 200:
                logger.warning(f"AI content too short ({word_count} words), falling back to basic")
                return None
            
            # Create PendingArticle with expanded content
            pending = PendingArticle.objects.create(
                rss_feed=rss_feed,
                source_url=source_url,
                content_hash=content_hash,
                title=ai_title,
                content=expanded_content,
                excerpt=content[:500] if len(content) > 500 else content,
                images=images,
                featured_image=images[0] if images else '',
                suggested_category=rss_feed.default_category,
                status='pending'
            )
            
            logger.info(f"✓ Created AI-enhanced PendingArticle: {ai_title[:50]} ({word_count} words)")
            return pending
            
        except Exception as e:
            logger.error(f"Error creating AI-enhanced article: {e}")
            logger.info("Falling back to basic article creation")
            return None
    
    def process_feed(self, rss_feed: RSSFeed, limit: int = 10, use_ai: bool = True) -> int:
        """
        Process RSS feed and create RSSNewsItem entries for manual review.
        
        No AI is called during scanning — items are saved raw.
        AI article generation happens on-demand when user clicks "Generate Article".
        
        Args:
            rss_feed: RSSFeed model instance
            limit: Maximum number of entries to process
            use_ai: Ignored (kept for API compatibility)
            
        Returns:
            Number of news items created
        """
        from news.models import RSSNewsItem
        
        feed_data = self.fetch_feed(rss_feed.feed_url)
        if not feed_data:
            return 0
        
        created_count = 0
        
        for entry in feed_data.entries[:limit]:
            try:
                title = entry.get('title', 'Untitled')
                source_url = entry.get('link', '')
                
                # Skip articles with generic/template titles (use shared checker)
                from ai_engine.main import _is_generic_header
                if not title.strip() or _is_generic_header(title):
                    logger.debug(f"Skipping entry with generic title: {title}")
                    continue
                
                plain_text = self.extract_plain_text(entry)  # For excerpt
                content = self.extract_content(entry)  # HTML version
                
                # Skip if no content or too short (minimum 100 chars — lowered since no AI needed)
                if not plain_text or len(plain_text) < 100:
                    logger.debug(f"Skipping entry with insufficient content ({len(plain_text) if plain_text else 0} chars): {title[:50]}")
                    continue
                
                # Check for duplicates (checks RSSNewsItem, PendingArticle AND Article)
                if self.is_duplicate(title, plain_text, source_url=source_url):
                    logger.debug(f"Skipping duplicate: {title[:50]}")
                    continue
                
                # Extract images
                images = self.extract_images(entry)
                
                # Fallback 1: Scrape og:image from article source page
                if not images and source_url:
                    og_image = self.extract_og_image(source_url)
                    if og_image:
                        images = [og_image]
                        logger.info(f'Added og:image for: {title[:50]}')
                
                # Fallback 2: RSS feed logo
                if not images and rss_feed.logo_url:
                    images = [rss_feed.logo_url]
                    logger.info(f'Using RSS feed logo as fallback for: {title[:50]}')
                
                featured_image = images[0] if images else ''
                
                # Calculate content hash (use plain text)
                content_hash = self.calculate_content_hash(plain_text)
                
                # Get publication date
                pub_date = self.parse_entry_date(entry)
                
                # Defensive truncation to prevent varchar overflow
                title = title[:500] if title else ''
                source_url = source_url[:2000] if source_url else ''
                featured_image = featured_image[:1000] if featured_image else ''
                
                # Create RSSNewsItem (raw, no AI processing)
                RSSNewsItem.objects.create(
                    rss_feed=rss_feed,
                    title=title,
                    content=content,
                    excerpt=plain_text[:500] if len(plain_text) > 500 else plain_text,
                    source_url=source_url,
                    image_url=featured_image,
                    content_hash=content_hash,
                    published_at=pub_date,
                    status='new'
                )
                logger.info(f"Saved RSS news item: {title[:50]}")
                
                created_count += 1
                
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
        
        logger.info(f"Processed {created_count} new RSS news items from {rss_feed.name}")
        return created_count

