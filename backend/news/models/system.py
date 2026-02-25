from django.db import models
from django.utils.text import slugify
from ..image_utils import optimize_image


# Intra-package imports to resolve foreign keys if needed

class SiteSettings(models.Model):
    """Global site settings managed from admin panel"""
    site_name = models.CharField(max_length=100, default="Fresh Motors")
    site_description = models.TextField(default="Your source for automotive news and reviews")
    contact_email = models.EmailField(default="admin@freshmotors.net")
    
    # Maintenance Mode
    maintenance_mode = models.BooleanField(
        default=False, 
        verbose_name="Maintenance Mode",
        help_text="Enable maintenance mode - only admins can access the site"
    )
    maintenance_message = models.TextField(
        default="We're currently performing maintenance to improve your experience. Please check back soon!",
        verbose_name="Maintenance Message",
        help_text="Message shown to visitors during maintenance"
    )
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    facebook_enabled = models.BooleanField(default=False, help_text="Show Facebook link")
    twitter_url = models.URLField(blank=True)
    twitter_enabled = models.BooleanField(default=False, help_text="Show Twitter/X link")
    instagram_url = models.URLField(blank=True)
    instagram_enabled = models.BooleanField(default=False, help_text="Show Instagram link")
    youtube_url = models.URLField(blank=True)
    youtube_enabled = models.BooleanField(default=False, help_text="Show YouTube link")
    linkedin_url = models.URLField(blank=True)
    linkedin_enabled = models.BooleanField(default=False, help_text="Show LinkedIn link")
    tiktok_url = models.URLField(blank=True)
    tiktok_enabled = models.BooleanField(default=False, help_text="Show TikTok link")
    telegram_url = models.URLField(blank=True)
    telegram_enabled = models.BooleanField(default=False, help_text="Show Telegram link")
    
    # SEO
    default_meta_description = models.CharField(max_length=160, blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True, help_text="GA4 Measurement ID")
    google_adsense_id = models.CharField(max_length=50, blank=True, help_text="ca-pub-XXXXXX")
    
    # Hero Section
    use_classic_hero = models.BooleanField(default=False, help_text="Show classic purple background instead of dynamic articles")
    hero_title = models.CharField(max_length=200, default="Welcome to Fresh Motors", help_text="Custom title for Hero section")
    hero_subtitle = models.TextField(default="Your premier source for automotive news, reviews, and insights", help_text="Custom subtitle for Hero section")
    
    # Homepage Sections
    show_browse_by_brand = models.BooleanField(default=True, help_text="Show 'Browse by Brand' section on homepage")
    
    # Footer
    footer_text = models.TextField(default="© 2026 Fresh Motors. All rights reserved.")
    
    # Contact Information
    contact_phone = models.CharField(max_length=50, blank=True, help_text="Phone number to display")
    contact_phone_enabled = models.BooleanField(default=False, help_text="Show phone in contacts")
    contact_address = models.TextField(blank=True, help_text="Office address")
    contact_address_enabled = models.BooleanField(default=False, help_text="Show address in contacts")
    support_email = models.EmailField(blank=True, help_text="Support email address")
    business_email = models.EmailField(blank=True, help_text="Business inquiries email")
    
    # Pages - About
    about_page_title = models.CharField(max_length=200, default="About AutoNews")
    about_page_content = models.TextField(blank=True, help_text="HTML content for About page")
    about_page_enabled = models.BooleanField(default=True, help_text="Show About page in footer")
    
    # Pages - Privacy Policy
    privacy_page_title = models.CharField(max_length=200, default="Privacy Policy")
    privacy_page_content = models.TextField(blank=True, help_text="HTML content for Privacy Policy")
    privacy_page_enabled = models.BooleanField(default=True, help_text="Show Privacy Policy in footer")
    
    # Pages - Terms of Service
    terms_page_title = models.CharField(max_length=200, default="Terms of Service")
    terms_page_content = models.TextField(blank=True, help_text="HTML content for Terms of Service")
    terms_page_enabled = models.BooleanField(default=True, help_text="Show Terms in footer")
    
    # Pages - Contact
    contact_page_title = models.CharField(max_length=200, default="Contact Us")
    contact_page_subtitle = models.CharField(max_length=500, blank=True, default="Have a question, suggestion, or just want to say hello? We'd love to hear from you!")
    contact_page_enabled = models.BooleanField(default=True, help_text="Show Contact page in footer")
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def __str__(self):
        return "Site Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class EmailPreferences(models.Model):
    """User email notification preferences"""
    user = models.OneToOneField(
        'auth.User', on_delete=models.CASCADE, 
        related_name='email_preferences'
    )
    
    # Newsletter preferences
    newsletter_enabled = models.BooleanField(
        default=True, 
        help_text="Receive weekly newsletter with top articles"
    )
    new_articles_enabled = models.BooleanField(
        default=False, 
        help_text="Get notified when new articles are published"
    )
    
    # Interaction notifications
    comment_replies_enabled = models.BooleanField(
        default=True, 
        help_text="Get notified when someone replies to your comment"
    )
    favorite_updates_enabled = models.BooleanField(
        default=False, 
        help_text="Get notified about updates to your favorite articles"
    )
    
    # Marketing
    marketing_enabled = models.BooleanField(
        default=False, 
        help_text="Receive promotional emails and special offers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Email Preferences"
        verbose_name_plural = "Email Preferences"
    
    def __str__(self):
        return f"Email preferences for {self.user.username}"

class Subscriber(models.Model):
    """Email newsletter subscribers"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email

class NewsletterHistory(models.Model):
    """Track all sent newsletters"""
    subject = models.CharField(max_length=255)
    message = models.TextField()
    sent_to_count = models.IntegerField(help_text="Number of subscribers who received this newsletter")
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name_plural = 'Newsletter History'
    
    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"

class AdminNotification(models.Model):
    """Notifications for admin dashboard"""
    NOTIFICATION_TYPES = [
        ('comment', 'New Comment'),
        ('subscriber', 'New Subscriber'),
        ('article', 'New Article'),
        ('video_pending', 'Video Pending Review'),
        ('video_error', 'Video Processing Error'),
        ('ai_error', 'AI Generation Error'),
        ('system', 'System Alert'),
        ('info', 'Information'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    ]
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="Optional link to related item")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Admin Notification"
        verbose_name_plural = "Admin Notifications"
    
    def __str__(self):
        return f"[{self.notification_type}] {self.title}"
    
    @classmethod
    def create_notification(cls, notification_type, title, message, link='', priority='normal'):
        """Helper method to create notifications"""
        return cls.objects.create(
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            priority=priority
        )

class SecurityLog(models.Model):
    """
    Security audit log for tracking important security events.
    Helps detect unauthorized access attempts and monitor account changes.
    """
    ACTION_CHOICES = [
        ('password_changed', 'Password Changed'),
        ('email_changed', 'Email Changed'),
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('password_reset_requested', 'Password Reset Requested'),
        ('password_reset_completed', 'Password Reset Completed'),
        ('account_locked', 'Account Locked'),
    ]
    
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='security_logs',
        null=True,
        blank=True,
        help_text="User who performed the action (null for failed login attempts)"
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text="Browser user agent string")
    
    # Additional context
    old_value = models.CharField(max_length=255, blank=True, help_text="Old value (e.g., old email)")
    new_value = models.CharField(max_length=255, blank=True, help_text="New value (e.g., new email)")
    details = models.TextField(blank=True, help_text="Additional details in JSON format")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Security Log"
        verbose_name_plural = "Security Logs"
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'Unknown'
        return f"{username} - {self.get_action_display()} at {self.created_at}"

class EmailVerification(models.Model):
    """
    Email verification for secure email changes.
    User requests email change, receives 6-digit code, must verify before email updates.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='email_verifications')
    new_email = models.EmailField(help_text="New email address to verify")
    code = models.CharField(max_length=6, help_text="6-digit verification code")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Code expiration time (15 minutes)")
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['code', 'is_used']),
        ]
    
    def is_valid(self):
        """Check if code is still valid (not expired, not used)"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"{self.user.username} - {self.new_email} (expires: {self.expires_at})"

class PasswordResetToken(models.Model):
    """
    Password reset tokens for "Forgot Password" functionality.
    User requests reset, receives email with unique token link, can set new password.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=64, unique=True, help_text="UUID token for password reset")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Token expiration time (1 hour)")
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        indexes = [
            models.Index(fields=['token', 'is_used']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def is_valid(self):
        """Check if token is still valid (not expired, not used)"""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"{self.user.username} - Reset requested at {self.created_at}"

class GSCReport(models.Model):
    """Daily overall site performance from Google Search Console"""
    date = models.DateField(unique=True, db_index=True)
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0.0)
    position = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "GSC Daily Report"
        verbose_name_plural = "GSC Daily Reports"
    
    def __str__(self):
        return f"GSC Report for {self.date}"

class ArticleGSCStats(models.Model):
    """Search performance per article"""
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='search_stats')
    date = models.DateField(db_index=True)
    clicks = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    ctr = models.FloatField(default=0.0)
    position = models.FloatField(default=0.0)
    
    # Store top queries for this article as JSON
    top_queries = models.JSONField(default=list, blank=True)
    
    class Meta:
        unique_together = ('article', 'date')
        ordering = ['-date']
        verbose_name = "Article Search Stat"
        verbose_name_plural = "Article Search Stats"
    
    def __str__(self):
        return f"Stats for {self.article.title} on {self.date}"

class NewsletterSubscriber(models.Model):
    """Newsletter email subscribers"""
    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
    
    def __str__(self):
        status = "Active" if self.is_active else "Unsubscribed"
        return f"{self.email} ({status})"

class ArticleEmbedding(models.Model):
    """
    Persistent storage for article embeddings (vector representations)
    Used for hybrid FAISS + PostgreSQL vector search
    """
    article = models.OneToOneField('news.Article',
        on_delete=models.CASCADE,
        related_name='embedding',
        help_text="Article this embedding belongs to"
    )
    embedding_vector = models.JSONField(
        help_text="768-dimensional embedding vector from Gemini (stored as JSON array)"
    )
    model_name = models.CharField(
        max_length=100,
        default="models/gemini-embedding-001",
        help_text="Gemini model used to generate this embedding"
    )
    text_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of indexed text (to detect changes)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'article_embeddings'
        verbose_name = 'Article Embedding'
        verbose_name_plural = 'Article Embeddings'
        indexes = [
            models.Index(fields=['article']),
        ]
    
    def __str__(self):
        return f"Embedding for: {self.article.title[:50]}"
    
    def get_vector_dimension(self):
        """Return dimension of embedding vector"""
        if self.embedding_vector:
            return len(self.embedding_vector)
        return 0

class ArticleTitleVariant(models.Model):
    """A/B testing variants for article titles.
    AI generates 2-3 title variants per article, and the system
    tracks impressions/clicks to determine the best-performing title."""
    
    VARIANT_CHOICES = [
        ('A', 'Variant A (Original)'),
        ('B', 'Variant B'),
        ('C', 'Variant C'),
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='title_variants')
    variant = models.CharField(max_length=1, choices=VARIANT_CHOICES)
    title = models.CharField(max_length=500)
    impressions = models.PositiveIntegerField(default=0, help_text="Number of times shown")
    clicks = models.PositiveIntegerField(default=0, help_text="Number of click-throughs")
    is_winner = models.BooleanField(default=False, help_text="Winning variant (applied as main title)")
    is_active = models.BooleanField(default=True, help_text="Is this test still running?")
    auto_pick_threshold = models.PositiveIntegerField(
        default=100,
        help_text="Minimum impressions per variant before auto-picking winner"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['variant']
        unique_together = ['article', 'variant']
        verbose_name = 'Title A/B Variant'
        verbose_name_plural = 'Title A/B Variants'
    
    @property
    def ctr(self):
        """Click-through rate as percentage"""
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)
    
    def __str__(self):
        return f"[{self.variant}] {self.title[:60]} (CTR: {self.ctr}%)"
    
    @classmethod
    def check_and_pick_winners(cls):
        """Auto-pick winners for tests that have enough data.
        Returns list of (article_id, winning_variant) tuples."""
        import logging
        logger = logging.getLogger(__name__)
        
        winners = []
        # Get articles with active tests
        active_article_ids = cls.objects.filter(
            is_active=True, is_winner=False
        ).values_list('article_id', flat=True).distinct()
        
        for article_id in active_article_ids:
            variants = list(cls.objects.filter(article_id=article_id, is_active=True))
            if len(variants) < 2:
                continue
            
            threshold = variants[0].auto_pick_threshold
            # Check if all variants have enough impressions
            if any(v.impressions < threshold for v in variants):
                continue
            
            # Find the best variant by CTR
            best = max(variants, key=lambda v: v.ctr)
            runner_up = sorted(variants, key=lambda v: v.ctr, reverse=True)[1]
            
            # Require meaningful CTR difference (>= 0.5 percentage points)
            if best.ctr - runner_up.ctr < 0.5:
                continue
            
            # Pick winner
            best.is_winner = True
            best.save(update_fields=['is_winner'])
            
            # Deactivate all variants for this article
            cls.objects.filter(article_id=article_id).update(is_active=False)
            
            # Apply winning title to the article
            article = Article.objects.get(id=article_id)
            article.title = best.title
            article.save(update_fields=['title'])
            
            winners.append((article_id, best.variant))
            logger.info(f"A/B winner picked: Article {article_id} → Variant {best.variant} ({best.ctr}% CTR)")
        
        return winners

class AdPlacement(models.Model):
    """Advertising placement managed from admin panel."""
    
    POSITION_CHOICES = [
        ('header', 'Header Banner'),
        ('sidebar', 'Sidebar'),
        ('between_articles', 'Between Articles (List)'),
        ('after_content', 'After Article Content'),
        ('footer', 'Footer'),
    ]
    
    TYPE_CHOICES = [
        ('banner', 'Banner (Image + Link)'),
        ('html_code', 'HTML/JS Code (AdSense, etc)'),
        ('sponsored', 'Sponsored Content (Text + Image)'),
    ]
    
    name = models.CharField(max_length=200, help_text="Internal name for this ad placement")
    position = models.CharField(max_length=30, choices=POSITION_CHOICES, db_index=True)
    ad_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='banner')
    
    # Banner fields
    image = models.ImageField(upload_to='ads/', blank=True, null=True, help_text="Banner image")
    link = models.URLField(max_length=500, blank=True, help_text="Click-through URL")
    alt_text = models.CharField(max_length=200, blank=True, help_text="Image alt text")
    
    # HTML code fields (for AdSense, etc)
    html_code = models.TextField(blank=True, help_text="Raw HTML/JS code to embed")
    
    # Sponsored content fields
    sponsor_name = models.CharField(max_length=200, blank=True, help_text="Sponsor/advertiser name")
    sponsor_text = models.TextField(blank=True, help_text="Sponsored message text")
    
    # Scheduling
    is_active = models.BooleanField(default=True, db_index=True, help_text="Enable/disable this ad")
    start_date = models.DateTimeField(null=True, blank=True, help_text="Start showing (empty = immediately)")
    end_date = models.DateTimeField(null=True, blank=True, help_text="Stop showing (empty = forever)")
    duration_preset = models.CharField(
        max_length=20, blank=True, default='unlimited',
        help_text="Duration preset used when creating"
    )
    
    # Display
    priority = models.IntegerField(default=0, help_text="Higher = shown first")
    target_pages = models.CharField(
        max_length=200, blank=True, default='all',
        help_text="Where to show: all, articles, home, cars"
    )
    
    # Analytics
    impressions = models.PositiveIntegerField(default=0, help_text="Times displayed")
    clicks = models.PositiveIntegerField(default=0, help_text="Times clicked")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = 'Ad Placement'
        verbose_name_plural = 'Ad Placements'
    
    @property
    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)
    
    @property
    def is_currently_active(self):
        """Check if ad should be shown right now (active + within date range)."""
        if not self.is_active:
            return False
        from django.utils import timezone
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
    
    def __str__(self):
        status = "✅" if self.is_currently_active else "⏸️"
        return f"{status} {self.name} ({self.get_position_display()}) — {self.impressions} views, {self.clicks} clicks"

class AutomationSettings(models.Model):
    """Automation control panel — singleton config for all automated tasks.
    
    All modules default to OFF for safe rollout.
    User enables them one by one from /admin/automation.
    """
    
    # === Site Theme ===
    THEME_CHOICES = [
        ('default', 'Default (Indigo/Purple)'),
        ('midnight-green', 'Midnight Green (Emerald)'),
        ('deep-ocean', 'Deep Ocean (Blue)'),
    ]
    site_theme = models.CharField(
        max_length=30, choices=THEME_CHOICES, default='default',
        help_text="Site-wide color theme"
    )
    
    # === RSS Scanning ===
    rss_scan_enabled = models.BooleanField(
        default=False, help_text="Enable automatic RSS feed scanning"
    )
    rss_scan_interval_minutes = models.IntegerField(
        default=30, help_text="Minutes between RSS scans (15, 30, 60, 120)"
    )
    rss_max_articles_per_scan = models.IntegerField(
        default=10, help_text="Max articles to process per scan cycle"
    )
    rss_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When RSS scan last ran"
    )
    rss_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last scan result message"
    )
    rss_articles_today = models.IntegerField(default=0)
    
    # === YouTube Scanning ===
    youtube_scan_enabled = models.BooleanField(
        default=False, help_text="Enable automatic YouTube channel scanning"
    )
    youtube_scan_interval_minutes = models.IntegerField(
        default=120, help_text="Minutes between YouTube scans (60, 120, 240)"
    )
    youtube_max_videos_per_scan = models.IntegerField(
        default=3, help_text="Max videos to process per scan cycle"
    )
    youtube_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When YouTube scan last ran"
    )
    youtube_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last scan result message"
    )
    youtube_articles_today = models.IntegerField(default=0)
    
    # === Auto-Publish ===
    auto_publish_enabled = models.BooleanField(
        default=False, help_text="Enable automatic publishing of high-quality pending articles"
    )
    auto_publish_min_quality = models.IntegerField(
        default=7, help_text="Minimum quality score (1-10) required for auto-publish"
    )
    auto_publish_max_per_hour = models.IntegerField(
        default=3, help_text="Maximum articles to auto-publish per hour"
    )
    auto_publish_max_per_day = models.IntegerField(
        default=20, help_text="Maximum articles to auto-publish per day"
    )
    auto_publish_require_image = models.BooleanField(
        default=True, help_text="Require featured image before auto-publishing"
    )
    auto_publish_today_count = models.IntegerField(
        default=0, help_text="Counter: articles auto-published today"
    )
    auto_publish_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When auto-publish last checked"
    )
    auto_publish_require_safe_feed = models.BooleanField(
        default=True, help_text="Only auto-publish articles from feeds with safety_score != 'unsafe'"
    )
    auto_publish_as_draft = models.BooleanField(
        default=True, help_text="Create articles as drafts (requires manual approval) instead of publishing directly"
    )
    
    # === Auto-Image ===
    AUTO_IMAGE_CHOICES = [
        ('off', 'Off — no auto image'),
        ('search_first', 'Find reference → AI generate'),
    ]
    auto_image_mode = models.CharField(
        max_length=20, choices=AUTO_IMAGE_CHOICES, default='off',
        help_text="Find a reference photo online, then generate AI image from it"
    )
    auto_image_prefer_press = models.BooleanField(
        default=True, help_text="Prefer editorial/press photos (green-highlighted) over others"
    )
    
    # === Google Indexing ===
    google_indexing_enabled = models.BooleanField(
        default=True, help_text="Auto-submit published articles to Google Indexing API"
    )
    google_indexing_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When Google Indexing last submitted"
    )
    google_indexing_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last indexing result"
    )
    google_indexing_today_count = models.IntegerField(
        default=0, help_text="Articles indexed today"
    )
    
    # === Auto-Image tracking ===
    auto_image_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When auto-image last ran"
    )
    auto_image_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last auto-image result"
    )
    auto_image_today_count = models.IntegerField(
        default=0, help_text="Images generated today"
    )
    
    # === Deep Specs / VehicleSpecs Auto-Backfill ===
    deep_specs_enabled = models.BooleanField(
        default=True, help_text="Auto-generate VehicleSpecs cards for published articles"
    )
    deep_specs_interval_hours = models.IntegerField(
        default=6, help_text="Hours between deep specs backfill runs (4, 6, 12, 24)"
    )
    deep_specs_max_per_cycle = models.IntegerField(
        default=3, help_text="Max articles to process per cycle"
    )
    deep_specs_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When deep specs backfill last ran"
    )
    deep_specs_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last backfill result"
    )
    deep_specs_today_count = models.IntegerField(
        default=0, help_text="VehicleSpecs cards created today"
    )
    
    # === Task Locks (prevent concurrent execution) ===
    rss_lock = models.BooleanField(default=False)
    rss_lock_at = models.DateTimeField(null=True, blank=True)
    youtube_lock = models.BooleanField(default=False)
    youtube_lock_at = models.DateTimeField(null=True, blank=True)
    auto_publish_lock = models.BooleanField(default=False)
    auto_publish_lock_at = models.DateTimeField(null=True, blank=True)
    score_lock = models.BooleanField(default=False)
    score_lock_at = models.DateTimeField(null=True, blank=True)
    deep_specs_lock = models.BooleanField(default=False)
    deep_specs_lock_at = models.DateTimeField(null=True, blank=True)
    
    LOCK_STALE_MINUTES = 10  # Release lock if older than this
    
    # === Counters reset tracking ===
    counters_reset_date = models.DateField(
        null=True, blank=True, help_text="Last date counters were reset"
    )
    
    class Meta:
        verbose_name = 'Automation Settings'
        verbose_name_plural = 'Automation Settings'
    
    def __str__(self):
        modules = []
        if self.rss_scan_enabled:
            modules.append('RSS')
        if self.youtube_scan_enabled:
            modules.append('YouTube')
        if self.auto_publish_enabled:
            modules.append('Auto-Publish')
        active = ', '.join(modules) if modules else 'All OFF'
        return f"Automation Settings ({active})"
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    
    def reset_daily_counters(self):
        """Reset daily counters if it's a new day."""
        from django.utils import timezone
        today = timezone.now().date()
        if self.counters_reset_date != today:
            self.auto_publish_today_count = 0
            self.rss_articles_today = 0
            self.youtube_articles_today = 0
            self.auto_image_today_count = 0
            self.google_indexing_today_count = 0
            self.counters_reset_date = today
            self.save(update_fields=[
                'auto_publish_today_count',
                'rss_articles_today', 'youtube_articles_today',
                'auto_image_today_count', 'google_indexing_today_count',
                'counters_reset_date'
            ])
    
    @classmethod
    def acquire_lock(cls, task_name: str) -> bool:
        """
        Atomically acquire a task lock. Returns True if acquired.
        Auto-releases stale locks older than LOCK_STALE_MINUTES.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        lock_field = f'{task_name}_lock'
        lock_at_field = f'{task_name}_lock_at'
        now = timezone.now()
        stale_cutoff = now - timedelta(minutes=cls.LOCK_STALE_MINUTES)
        
        # Try to acquire: only succeed if lock is False OR lock is stale
        from django.db.models import Q
        updated = cls.objects.filter(
            Q(pk=1) & (
                Q(**{lock_field: False}) |
                Q(**{lock_at_field + '__lt': stale_cutoff})
            )
        ).update(**{lock_field: True, lock_at_field: now})
        
        return updated > 0
    
    @classmethod
    def release_lock(cls, task_name: str):
        """Release a task lock."""
        lock_field = f'{task_name}_lock'
        lock_at_field = f'{task_name}_lock_at'
        cls.objects.filter(pk=1).update(**{lock_field: False, lock_at_field: None})

class AutoPublishLog(models.Model):
    """Logs every auto-publish decision for transparency and ML training data."""
    DECISION_CHOICES = [
        ('published', 'Published'),
        ('drafted', 'Drafted (Awaiting Review)'),
        ('human_approved', 'Human Approved'),
        ('human_rejected', 'Human Rejected'),
        ('skipped_quality', 'Skipped: Low Quality'),
        ('skipped_safety', 'Skipped: Feed Unsafe'),
        ('skipped_no_image', 'Skipped: No Image'),
        ('skipped_limit', 'Skipped: Rate Limit'),
        ('failed', 'Failed: Error'),
    ]
    
    pending_article = models.ForeignKey('news.PendingArticle', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='publish_logs'
    )
    published_article = models.ForeignKey(
        'Article', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='publish_logs'
    )
    
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES)
    reason = models.TextField(help_text="Human-readable explanation")
    
    # Snapshot of scores at decision time
    quality_score = models.IntegerField(default=0)
    safety_score = models.CharField(max_length=20, blank=True, default='')
    image_policy = models.CharField(max_length=20, blank=True, default='')
    
    # Source info
    feed_name = models.CharField(max_length=300, blank=True, default='')
    source_type = models.CharField(max_length=20, blank=True, default='')
    article_title = models.CharField(max_length=500, blank=True, default='')
    
    # ML training features
    content_length = models.IntegerField(default=0, help_text="Article content length in chars")
    has_image = models.BooleanField(default=False)
    has_specs = models.BooleanField(default=False)
    tag_count = models.IntegerField(default=0)
    category_name = models.CharField(max_length=100, blank=True, default='')
    source_is_youtube = models.BooleanField(default=False)
    
    # Human review learning signal
    review_time_seconds = models.IntegerField(
        null=True, blank=True,
        help_text="How long the human spent reviewing (seconds) — faster = more confident"
    )
    reviewer_notes = models.TextField(
        blank=True, default='',
        help_text="Why the reviewer approved/rejected — ML training data"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Auto-Publish Log'
        verbose_name_plural = 'Auto-Publish Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['decision']),
        ]
    
    def __str__(self):
        return f"{self.decision}: {self.article_title[:50]}"

class TagLearningLog(models.Model):
    """Stores title_keywords → final_tags mappings for tag suggestion learning.
    
    When a user publishes or edits tags on an article, we record:
    - Extracted keywords from the title
    - The final set of tags the user chose
    
    Over time, this builds a labeled dataset that the tag_suggester uses
    to recommend tags for new articles based on keyword similarity.
    """
    article = models.OneToOneField('news.Article', on_delete=models.CASCADE,
        related_name='tag_learning_log'
    )
    title = models.CharField(max_length=500)
    title_keywords = models.JSONField(
        default=list,
        help_text="Extracted keywords from title (lowercase)"
    )
    final_tags = models.JSONField(
        default=list,
        help_text="Tag names the user approved for this article"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tag Learning Log'
        verbose_name_plural = 'Tag Learning Logs'
        indexes = [
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.title[:50]} → {self.final_tags}"

class ThemeAnalytics(models.Model):
    """Tracks which color theme visitors choose — anonymous analytics."""
    theme = models.CharField(max_length=30, db_index=True, help_text="Theme ID e.g. 'default', 'midnight-green', 'deep-ocean'")
    session_hash = models.CharField(max_length=64, blank=True, default='', help_text="Anonymized session identifier")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['theme', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.theme} at {self.created_at}"

class AdminActionLog(models.Model):
    """
    Tracks admin actions on articles for analytics and quality insights.
    Every AI button press, edit save, image change, and publish/unpublish is logged.
    """
    ACTION_CHOICES = [
        ('reformat', '✨ Reformat with AI'),
        ('re_enrich', '⚡ Re-enrich Specs'),
        ('regenerate', '🔄 Regenerate'),
        ('edit_save', '💾 Article Saved'),
        ('image_change', '🖼️ Image Changed'),
        ('publish', '📢 Published'),
        ('unpublish', '📝 Unpublished'),
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE,
        related_name='admin_action_logs'
    )
    user = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admin_action_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    success = models.BooleanField(default=True)
    details = models.JSONField(
        null=True, blank=True,
        help_text="Action-specific data: lengths, field changes, provider info, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['article', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} on #{self.article_id} by {self.user} at {self.created_at}"
    
    @classmethod
    def log(cls, article, user, action, success=True, details=None):
        """Convenience method to create a log entry."""
        return cls.objects.create(
            article=article,
            user=user if user and user.is_authenticated else None,
            action=action,
            success=success,
            details=details,
        )

