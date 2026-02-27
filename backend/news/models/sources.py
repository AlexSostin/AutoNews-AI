from django.db import models
from django.utils.text import slugify
from ..image_utils import optimize_image


# Intra-package imports to resolve foreign keys if needed

class YouTubeChannel(models.Model):
    """YouTube channels to monitor for new videos"""
    name = models.CharField(max_length=200, help_text="Channel name for display")
    channel_url = models.URLField(max_length=2000, help_text="YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)")
    channel_id = models.CharField(max_length=100, blank=True, help_text="YouTube channel ID (auto-extracted)")
    
    # Settings
    is_enabled = models.BooleanField(default=True, help_text="Enable monitoring for this channel")
    auto_publish = models.BooleanField(default=False, help_text="Automatically publish articles (skip review)")
    default_category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Default category for articles from this channel"
    )
    
    # Tracking
    last_checked = models.DateTimeField(null=True, blank=True)
    last_video_id = models.CharField(max_length=50, blank=True, help_text="Last processed video ID")
    videos_processed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "YouTube Channel"
        verbose_name_plural = "YouTube Channels"
    
    def __str__(self):
        return self.name

class RSSFeed(models.Model):
    """RSS feeds from automotive brands and news sources"""
    SOURCE_TYPES = [
        ('brand', 'Automotive Brand'),
        ('media', 'Automotive Media'),
        ('blog', 'Industry Blog'),
    ]
    
    name = models.CharField(max_length=200, help_text="Feed name for display (e.g., 'Mercedes-Benz Press')")
    feed_url = models.URLField(max_length=2000, unique=True, help_text="RSS/Atom feed URL")
    website_url = models.URLField(max_length=2000, blank=True, help_text="Main website URL")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default='brand')
    
    # Settings
    is_enabled = models.BooleanField(default=True, help_text="Enable monitoring for this feed")
    auto_publish = models.BooleanField(default=False, help_text="Automatically publish articles (skip review)")
    default_category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Default category for articles from this feed"
    )
    
    # Tracking
    last_checked = models.DateTimeField(null=True, blank=True)
    last_entry_date = models.DateTimeField(null=True, blank=True, help_text="Publication date of last processed entry")
    entries_processed = models.IntegerField(default=0)
    
    # Metadata
    logo_url = models.URLField(max_length=2000, blank=True, help_text="Brand/source logo URL")
    description = models.TextField(blank=True)
    
    # Content License Status
    LICENSE_STATUS_CHOICES = [
        ('unchecked', 'Not Checked'),
        ('green', 'Free to Use'),
        ('yellow', 'Use with Caution'),
        ('red', 'Restricted'),
    ]
    license_status = models.CharField(
        max_length=20, choices=LICENSE_STATUS_CHOICES, default='unchecked',
        help_text="Content license status based on robots.txt and Terms of Use analysis"
    )
    license_details = models.TextField(blank=True, help_text="AI analysis of the site's content licensing terms")
    license_checked_at = models.DateTimeField(null=True, blank=True)
    
    # Safety Check Results (per-step breakdown)
    safety_checks = models.JSONField(
        default=dict, blank=True,
        help_text="Step-by-step safety evaluation: robots_txt, press_portal, tos_analysis, image_rights"
    )
    
    # Image Policy
    IMAGE_POLICY_CHOICES = [
        ('original', 'Use Original Images'),          # Press portals — images are for media
        ('pexels_only', 'Use Pexels Only'),            # Media sites — replace all images with stock
        ('pexels_fallback', 'Original + Pexels Fallback'),  # Use original if available, else Pexels
    ]
    image_policy = models.CharField(
        max_length=20, choices=IMAGE_POLICY_CHOICES, default='pexels_fallback',
        help_text="How to source images: original (press), pexels_only (media), or fallback"
    )
    
    @property
    def safety_score(self):
        """Computed safety for automation: safe / review / unsafe"""
        if self.license_status == 'red':
            return 'unsafe'
        
        checks = self.safety_checks or {}
        if not checks:
            # No checks performed yet
            return 'review'
        
        passed = sum(1 for c in checks.values() if isinstance(c, dict) and c.get('passed'))
        total = len([c for c in checks.values() if isinstance(c, dict)])
        
        if total == 0:
            return 'review'
        
        # All checks passed = safe, any failed = review
        if passed == total and self.license_status == 'green':
            return 'safe'
        elif passed >= total - 1 and self.license_status == 'green':
            # One failed check but still green overall
            return 'review'
        return 'review'
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "RSS Feed"
        verbose_name_plural = "RSS Feeds"
    
    def __str__(self):
        return self.name

class RSSNewsItem(models.Model):
    """Raw RSS news items stored without AI processing.
    
    These are the original RSS entries that the user can browse
    in the admin panel and selectively send to AI for article generation.
    """
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('generating', 'Generating Article'),
        ('generated', 'Article Generated'),
        ('dismissed', 'Dismissed'),
    ]
    
    rss_feed = models.ForeignKey('news.RSSFeed', on_delete=models.CASCADE,
        related_name='news_items'
    )
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, help_text="Raw HTML content from RSS")
    excerpt = models.TextField(blank=True, help_text="Plain text snippet for preview")
    source_url = models.URLField(max_length=2000, blank=True, help_text="Link to original article")
    image_url = models.URLField(blank=True, max_length=1000, help_text="Featured image URL")
    content_hash = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="SHA256 hash for deduplication"
    )
    published_at = models.DateTimeField(null=True, blank=True, help_text="Original publication date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Link to generated article (if any)
    pending_article = models.ForeignKey(
        'PendingArticle', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='source_news_item'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "RSS News Item"
        verbose_name_plural = "RSS News Items"
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['rss_feed', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.get_status_display()}] {self.title[:80]}"

