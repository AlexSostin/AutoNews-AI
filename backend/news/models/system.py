from django.db import models
from django.utils.text import slugify


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
    reddit_url = models.URLField(blank=True)
    reddit_enabled = models.BooleanField(default=False, help_text="Show Reddit link")
    
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
    
    # Article Reading Experience
    infinite_scroll_enabled = models.BooleanField(default=True, help_text="Enable infinite article loading on scroll")
    
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
    """Email newsletter subscribers.
    
    NOTE: Legacy model — consider migrating to NewsletterSubscriber (line ~372)
    which has additional fields (ip_address, subscribed_at naming).
    Both tables are actively used in the codebase:
      - Subscriber: signals.py, search_analytics_views.py, system_graph.py
      - NewsletterSubscriber: subscribers.py API, newsletter sending
    A data migration should unify them in the future.
    """
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
        ordering = ['-date']
        verbose_name = "Article Search Stat"
        verbose_name_plural = "Article Search Stats"
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'date'],
                name='unique_article_gsc_per_date',
            ),
        ]
    
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
        default="models/gemini-embedding-2-preview",
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

    # === Winner tracking (for ML training data) ===
    selected_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this variant was selected as winner (admin or auto)"
    )
    selection_source = models.CharField(
        max_length=10, blank=True, default='',
        choices=[
            ('admin', 'Admin picked manually'),
            ('auto', 'Auto-picked by CTR'),
            ('ai', 'AI-recommended'),
        ],
        help_text="How the winner was selected — for ML training signal"
    )
    # Extracted title patterns — pre-computed for future ML analysis
    # e.g. {"has_numbers": true, "word_count": 9, "has_question": false, "has_brand": true}
    title_pattern = models.JSONField(
        null=True, blank=True,
        help_text="Pre-extracted title features for future ML pattern analysis"
    )

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
        from django.utils import timezone
        logger = logging.getLogger(__name__)

        now = timezone.now()
        winners = []
        # Get articles with active tests
        active_article_ids = cls.objects.filter(
            is_active=True, is_winner=False
        ).values_list('article_id', flat=True).distinct()

        for article_id in active_article_ids:
            variants = list(cls.objects.filter(article_id=article_id, is_active=True).order_by('-impressions'))
            if len(variants) < 2:
                continue

            # Check if all active variants crossed threshold
            if all(v.impressions >= v.auto_pick_threshold for v in variants):
                # Pick winner (highest CTR)
                winner = max(variants, key=lambda x: x.ctr)

                # Mark winner with selection metadata
                winner.is_winner = True
                winner.is_active = False
                winner.selected_at = now
                winner.selection_source = 'auto'
                winner.save(update_fields=['is_winner', 'is_active', 'selected_at', 'selection_source'])

                # Mark others as inactive
                cls.objects.filter(article_id=article_id).exclude(id=winner.id).update(
                    is_active=False, is_winner=False
                )

                # Update actual article title
                from .content import Article
                Article.objects.filter(id=article_id).update(title=winner.title)

                winners.append((article_id, winner.variant))
                logger.info(f"A/B winner picked: Article {article_id} → Variant {winner.variant} ({winner.ctr}% CTR)")

        return winners


class ArticleImageVariant(models.Model):
    """A/B testing variants for article images (thumbnails).
    Tracks impressions/clicks to determine the best-performing image source."""
    
    VARIANT_CHOICES = [
        ('A', 'Variant A (Original)'),
        ('B', 'Variant B'),
        ('C', 'Variant C'),
    ]

    IMAGE_SOURCE_CHOICES = [
        ('youtube', 'YouTube Thumbnail'),
        ('rss_original', 'Original Source'),
        ('pexels', 'Pexels'),
        ('ai_generated', 'AI Generated'),
        ('uploaded', 'Manual Upload'),
        ('unknown', 'Unknown')
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='image_variants')
    variant = models.CharField(max_length=1, choices=VARIANT_CHOICES)
    image_url = models.CharField(max_length=1000, help_text="URL or Cloudinary path to the image")
    image_source = models.CharField(max_length=20, choices=IMAGE_SOURCE_CHOICES, default='unknown')
    impressions = models.PositiveIntegerField(default=0, help_text="Number of times shown")
    clicks = models.PositiveIntegerField(default=0, help_text="Number of click-throughs")
    is_winner = models.BooleanField(default=False, help_text="Winning variant (applied as main image)")
    is_active = models.BooleanField(default=True, help_text="Is this test still running?")
    auto_pick_threshold = models.PositiveIntegerField(
        default=500,
        help_text="Minimum impressions per variant before auto-picking winner"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['variant']
        unique_together = ['article', 'variant']
        verbose_name = 'Image A/B Variant'
        verbose_name_plural = 'Image A/B Variants'
    
    @property
    def ctr(self):
        """Click-through rate as percentage"""
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)
    
    def __str__(self):
        return f"[{self.variant}] {self.image_source} (CTR: {self.ctr}%)"
    
    @classmethod
    def check_and_pick_winners(cls):
        """Auto-pick winners for tests that have enough data."""
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
            
            # Apply winning image to the article
            from .content import Article
            Article.objects.filter(id=article_id).update(
                featured_image=best.image_url
            )
            
            winners.append((article_id, best.variant))
            logger.info(f"Image A/B winner: Article {article_id} → Variant {best.variant} ({best.ctr}% CTR, src={best.image_source})")
        
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
    
    # === Telegram Publishing ===
    telegram_enabled = models.BooleanField(
        default=False, help_text="Auto-post new articles to Telegram channel"
    )
    telegram_channel_id = models.CharField(
        max_length=100, blank=True, default='@freshmotors_news',
        help_text="Telegram channel username or numeric chat_id"
    )
    telegram_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When last Telegram post was sent"
    )
    telegram_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last post result"
    )
    telegram_today_count = models.IntegerField(
        default=0, help_text="Posts sent today"
    )
    telegram_post_with_image = models.BooleanField(
        default=True, help_text="Try to attach article image to Telegram post"
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
    
    # === YouTube Daytime-Only Mode ===
    # YouTube scans trigger AI article generation (expensive). Restrict to daytime hours
    # so articles are generated when the admin is awake to review them.
    youtube_daytime_only = models.BooleanField(
        default=True, help_text="Only run YouTube scans during active hours (saves API costs at night)"
    )
    youtube_active_hours_start = models.IntegerField(
        default=7, help_text="Hour to START YouTube scans (Israel time, 0-23). Default: 7 AM"
    )
    youtube_active_hours_end = models.IntegerField(
        default=22, help_text="Hour to STOP YouTube scans (Israel time, 0-23). Default: 10 PM"
    )
    
    # === Auto-Publish Safety ===
    auto_publish_skip_with_warnings = models.BooleanField(
        default=True,
        help_text="Skip articles with ⚠️ AI Fact-Check Warning banners — require manual review"
    )
    
    # === Bulk Enrichment Report ===
    # Stored in DB so it survives Railway/Docker redeploys (unlike filesystem)
    enrichment_report = models.JSONField(
        null=True, blank=True,
        help_text="Last bulk_enrich run summary: last_run, articles_processed, tags_created, etc."
    )

    # === Comparison Articles Auto-Generation ===
    comparison_enabled = models.BooleanField(
        default=False, help_text="Auto-generate 'X vs Y' comparison articles weekly"
    )
    comparison_max_per_week = models.IntegerField(
        default=2, help_text="Max comparison articles to generate per week (2-5)"
    )
    comparison_provider = models.CharField(
        max_length=20, default='gemini',
        help_text="AI provider for comparison generation: gemini or groq"
    )
    comparison_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When comparison auto-generation last ran"
    )
    comparison_last_status = models.CharField(
        max_length=500, blank=True, default='', help_text="Last comparison generation result"
    )
    comparison_this_week_count = models.IntegerField(
        default=0, help_text="Comparisons generated this week"
    )
    comparison_week_start = models.DateField(
        null=True, blank=True, help_text="Start of current comparison week (for weekly reset)"
    )
    comparison_lock = models.BooleanField(default=False)
    comparison_lock_at = models.DateTimeField(null=True, blank=True)

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
        if self.telegram_enabled:
            modules.append('Telegram')
        if self.deep_specs_enabled:
            modules.append('DeepSpecs')
        if self.google_indexing_enabled:
            modules.append('Indexing')
        if self.comparison_enabled:
            modules.append('Comparisons')
        if self.auto_image_mode != 'off':
            modules.append('AutoImage')
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
            self.telegram_today_count = 0
            self.deep_specs_today_count = 0
            self.counters_reset_date = today
            self.save(update_fields=[
                'auto_publish_today_count',
                'rss_articles_today', 'youtube_articles_today',
                'auto_image_today_count', 'google_indexing_today_count',
                'telegram_today_count', 'deep_specs_today_count',
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
        ('skipped_warnings', 'Skipped: Fact-Check Warning'),
        ('skipped_limit', 'Skipped: Rate Limit'),
        ('skipped_duplicate', 'Skipped: Too Similar'),
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


class CuratorDecisionLog(models.Model):
    """Records admin decisions on curated RSS items for ML training.

    Every time an admin uses the Smart Curator and clicks Generate / Skip /
    Merge / Save-Later, a row is created here.  Over time the ML preference
    scorer uses these rows to learn what kinds of articles the admin prefers.
    """
    DECISION_CHOICES = [
        ('generate', 'Generated Article'),
        ('merge', 'Merged into Roundup'),
        ('skip', 'Skipped'),
        ('save_later', 'Saved for Later'),
    ]

    news_item = models.ForeignKey(
        'news.RSSNewsItem', on_delete=models.CASCADE,
        related_name='curator_decisions',
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    curator_score = models.IntegerField(
        default=0, help_text="FreshMotors relevance score at decision time"
    )
    cluster_id = models.CharField(
        max_length=50, blank=True, default='',
        help_text="Cluster identifier from curator run",
    )

    # Feature snapshot for ML (frozen at decision time)
    brand = models.CharField(max_length=100, blank=True, default='')
    has_specs_data = models.BooleanField(default=False)
    source_count = models.IntegerField(default=1)
    llm_score = models.IntegerField(null=True, blank=True)
    title_text = models.CharField(
        max_length=500, blank=True, default='',
        help_text="Title snapshot — avoids JOIN for ML training queries",
    )

    # Result tracking
    generated_article = models.ForeignKey(
        'Article', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='curator_decisions',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Curator Decision Log'
        verbose_name_plural = 'Curator Decision Logs'
        indexes = [
            models.Index(fields=['decision', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.decision}] {self.title_text[:60]}"


class SocialPost(models.Model):
    """Tracks social media posts (Telegram, Twitter, etc.) for audit trail and queue.
    
    Created when an article is published. Status tracks the post lifecycle:
    - pending: queued for posting (manual approval mode)
    - sent: successfully posted
    - failed: post attempt failed
    - skipped: skipped (auto-post disabled, etc.)
    """
    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('twitter', 'Twitter/X'),
        ('reddit', 'Reddit'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='social_posts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_text = models.TextField(blank=True, help_text="Formatted post text")
    external_id = models.CharField(max_length=100, blank=True, default='', help_text="Telegram message_id, tweet_id, etc.")
    channel_id = models.CharField(max_length=100, blank=True, default='', help_text="Target channel/account")
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Social Post'
        verbose_name_plural = 'Social Posts'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['platform', 'status']),
        ]
    
    def __str__(self):
        icon = {'telegram': '📱', 'twitter': '🐦', 'reddit': '🔴'}.get(self.platform, '📡')
        status_icon = {'sent': '✅', 'failed': '❌', 'pending': '⏳', 'skipped': '⏩'}.get(self.status, '❓')
        title = self.article.title[:40] if self.article_id else '?'
        return f"{icon}{status_icon} {title}"

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


class TrainingPair(models.Model):
    """Stores input→output pairs for Gemini fine-tuning.
    
    Captured automatically via signals:
    - 'generation': PendingArticle content → final Article content
    - 'title_ab': losing title → winning A/B title
    
    Export with: python manage.py export_training_data
    """
    PAIR_TYPE_CHOICES = [
        ('generation', 'Article Generation (source → final)'),
        ('title_ab', 'Title A/B Winner'),
    ]
    SOURCE_TYPE_CHOICES = [
        ('rss', 'RSS Feed'),
        ('youtube', 'YouTube'),
        ('manual', 'Manual'),
    ]

    article = models.ForeignKey('news.Article', on_delete=models.CASCADE,
        related_name='training_pairs'
    )
    pair_type = models.CharField(max_length=20, choices=PAIR_TYPE_CHOICES)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='rss')

    # Input/Output for fine-tuning
    input_title = models.CharField(max_length=500, blank=True)
    output_title = models.CharField(max_length=500, blank=True)
    input_text = models.TextField(help_text="Source content (pending article / original AI)")
    output_text = models.TextField(help_text="Final content after admin edits")

    # Quality signals — enriched over time by capsule feedback
    quality_signals = models.JSONField(
        default=dict, blank=True,
        help_text="Reader quality data: capsule_score, engagement_score, views, etc."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Training Pair'
        verbose_name_plural = 'Training Pairs'
        indexes = [
            models.Index(fields=['pair_type', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'pair_type'],
                name='unique_training_pair_per_article',
            ),
        ]

    def __str__(self):
        return f"[{self.pair_type}] {self.output_title[:50]}"

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
        ('delete', '🗑️ Deleted'),
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


class FrontendEventLog(models.Model):
    """
    Telemetry log for Next.js frontend errors and anomalies.
    Captures unhandled exceptions, 404s, and failed rendering states.
    """
    ERROR_TYPES = [
        ('js_error', 'JavaScript Error'),
        ('network', 'Network / API Failure'),
        ('hydration', 'React Hydration Mismatch'),
        ('resource_404', 'Missing Resource (404)'),
        ('performance', 'Performance Violation'),
        ('react_crash', 'React Component Crash'),
        ('api_4xx', 'API Client Error (4xx)'),
        ('api_5xx', 'API Server Error (5xx)'),
        ('unhandled_rejection', 'Unhandled Promise Rejection'),
        ('caught_error', 'Caught Error (try/catch)'),
        ('other', 'Other'),
    ]

    error_type = models.CharField(max_length=50, choices=ERROR_TYPES, default='other')
    message = models.TextField(help_text="Primary error message")
    stack_trace = models.TextField(blank=True, help_text="Component stack or JS stack trace")
    url = models.URLField(max_length=1000, help_text="Page URL where the error occurred")
    user_agent = models.TextField(blank=True)
    
    # Tracking volume
    occurrence_count = models.IntegerField(default=1, help_text="Number of times this similar error was caught")
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Resolution state
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-last_seen']
        verbose_name = "Frontend Event Log"
        verbose_name_plural = "Frontend Event Logs"
        indexes = [
            models.Index(fields=['-last_seen']),
            models.Index(fields=['resolved']),
            models.Index(fields=['error_type']),
        ]

    def __str__(self):
        status = "✅" if self.resolved else "🚨"
        return f"{status} [{self.get_error_type_display()}] {self.message[:60]}"


class PageAnalyticsEvent(models.Model):
    """
    Universal analytics event store for page-level engagement tracking.
    Captures scroll depth, CTR, filter usage, recommended effectiveness, etc.
    """
    EVENT_TYPES = [
        ('page_view', 'Page View'),
        ('page_leave', 'Page Leave (dwell + scroll)'),
        ('card_click', 'Article Card Click'),
        ('search', 'Search Query'),
        ('filter_use', 'Filter Applied'),
        ('recommended_impression', 'Recommended Section Shown'),
        ('recommended_click', 'Recommended Article Clicked'),
        ('compare_use', 'Compare Tool Used'),
        ('infinite_scroll', 'Infinite Scroll Load'),
        ('ad_impression', 'Ad Banner Shown'),
        ('ad_click', 'Ad Banner Clicked'),
    ]
    
    PAGE_TYPES = [
        ('home', 'Home Page'),
        ('articles', 'Articles Listing'),
        ('article_detail', 'Article Detail'),
        ('trending', 'Trending Page'),
        ('cars', 'Cars Listing'),
        ('car_detail', 'Car Detail'),
        ('compare', 'Compare Page'),
        ('categories', 'Categories Page'),
        ('category_detail', 'Category Detail'),
        ('other', 'Other'),
    ]
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    page_type = models.CharField(max_length=30, choices=PAGE_TYPES, default='other')
    page_url = models.CharField(max_length=500, blank=True, default='')
    
    # Flexible metrics payload (varies by event_type)
    # Examples:
    #   page_leave: {"dwell_seconds": 45, "scroll_depth_pct": 78, "infinite_loads": 3}
    #   card_click: {"article_id": 123, "card_position": 5, "card_type": "grid"}
    #   search: {"query": "tesla", "results_count": 12}
    #   filter_use: {"filter_type": "category", "filter_value": "ev-news"}
    #   recommended_click: {"article_id": 45, "position": 2, "source_tags": ["SUV"]}
    metrics = models.JSONField(default=dict, blank=True)
    
    # Discovery path — how user found this page
    referrer_page = models.CharField(max_length=200, blank=True, default='',
        help_text="Internal referrer: home, articles, recommended, search, direct")
    
    # Device info
    device_type = models.CharField(max_length=10, blank=True, default='',
        help_text="desktop, tablet, mobile")
    viewport_width = models.PositiveIntegerField(null=True, blank=True)
    
    # Anonymous identification
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_hash = models.CharField(max_length=64, blank=True, default='',
        help_text="Anonymized session fingerprint")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Page Analytics Event'
        verbose_name_plural = 'Page Analytics Events'
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['page_type', '-created_at']),
            models.Index(fields=['session_hash', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.event_type}] {self.page_type} — {self.created_at:%H:%M:%S}"


class BackendErrorLog(models.Model):
    """
    Captures backend API 500 errors and scheduler task failures.
    Deduplicates by error_class + message + request_path within 1 hour.
    """
    ERROR_SOURCES = [
        ('api', 'API Request (500)'),
        ('scheduler', 'Scheduler Task'),
        ('middleware', 'Middleware'),
    ]
    SEVERITY_LEVELS = [
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    source = models.CharField(max_length=20, choices=ERROR_SOURCES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='error')
    error_class = models.CharField(max_length=255, help_text="Exception class name, e.g. ValueError")
    message = models.TextField(help_text="Error message")
    traceback = models.TextField(blank=True, help_text="Full traceback")

    # Request context (for API errors)
    request_method = models.CharField(max_length=10, blank=True, default='')
    request_path = models.CharField(max_length=500, blank=True, default='')
    request_user = models.CharField(max_length=150, blank=True, default='')
    request_ip = models.GenericIPAddressField(null=True, blank=True)

    # Scheduler context
    task_name = models.CharField(max_length=100, blank=True, default='',
        help_text="Scheduler task name, e.g. rss_scan, youtube_scan")

    # Tracking
    occurrence_count = models.IntegerField(default=1)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-last_seen']
        verbose_name = 'Backend Error Log'
        verbose_name_plural = 'Backend Error Logs'
        indexes = [
            models.Index(fields=['-last_seen']),
            models.Index(fields=['resolved']),
            models.Index(fields=['source', '-last_seen']),
            models.Index(fields=['severity', '-last_seen']),
        ]

    def __str__(self):
        status = "✅" if self.resolved else "🚨"
        return f"{status} [{self.get_source_display()}] {self.error_class}: {self.message[:60]}"


class CompetitorPairLog(models.Model):
    """
    ML learning log for competitor comparisons used in article generation.

    Every time AI generates an article with a "How It Compares" section,
    we record which competitor cars were shown alongside the subject car.

    A nightly job (`score_competitor_pairs` management command) fills in
    `engagement_score_at_log` from the linked article's engagement_score.

    Over time, `get_competitor_context()` in competitor_lookup.py uses
    average engagement scores to rank competitor candidates — pairs that
    historically produced high-engagement articles float to the top.
    """

    # The article that was generated
    article = models.ForeignKey(
        'news.Article', on_delete=models.CASCADE,
        related_name='competitor_pair_logs',
        help_text="Article that included these competitor comparisons"
    )

    # Subject car (the car the article is ABOUT)
    subject_make = models.CharField(max_length=100, db_index=True)
    subject_model = models.CharField(max_length=100, db_index=True)

    # Competitor car (one record per competitor per article)
    competitor_make = models.CharField(max_length=100, db_index=True)
    competitor_model = models.CharField(max_length=100, db_index=True)
    competitor_trim = models.CharField(max_length=100, blank=True, default='')

    # Specs snapshot at time of generation (for debugging / drift detection)
    competitor_power_hp = models.IntegerField(null=True, blank=True)
    competitor_range_km = models.IntegerField(null=True, blank=True)
    competitor_price_usd = models.IntegerField(null=True, blank=True)

    # ML feedback signal: filled in by `score_competitor_pairs` command
    # after the article has been live for 48+ hours
    engagement_score_at_log = models.FloatField(
        null=True, blank=True,
        help_text="article.engagement_score captured 48h+ after publication"
    )
    engagement_scored_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When engagement_score_at_log was last updated"
    )

    # Scoring metadata
    match_score = models.FloatField(
        default=0.0,
        help_text="How well this competitor matched at selection time (0-1)"
    )
    selection_method = models.CharField(
        max_length=20, default='rule_based',
        choices=[
            ('rule_based', 'Rule-Based (fuel+body+price)'),
            ('ml_ranked', 'ML-Ranked (engagement history)'),
        ],
        help_text="How this competitor was selected"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Competitor Pair Log'
        verbose_name_plural = 'Competitor Pair Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject_make', 'subject_model']),
            models.Index(fields=['competitor_make', 'competitor_model']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['engagement_score_at_log']),
        ]

    def __str__(self):
        score_str = f" | eng={self.engagement_score_at_log:.1f}" if self.engagement_score_at_log is not None else ""
        return (
            f"{self.subject_make} {self.subject_model} vs "
            f"{self.competitor_make} {self.competitor_model}"
            f"{score_str}"
        )


class TOTPDevice(models.Model):
    """
    TOTP 2FA device for admin accounts.
    Stores the shared secret for time-based one-time passwords.
    """
    user = models.OneToOneField(
        'auth.User', on_delete=models.CASCADE,
        related_name='totp_device'
    )
    secret = models.CharField(
        max_length=64,
        help_text="Base32-encoded TOTP secret"
    )
    is_confirmed = models.BooleanField(
        default=False,
        help_text="True after user verifies their first code"
    )
    backup_codes = models.JSONField(
        default=list, blank=True,
        help_text="One-time backup codes (hashed)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "TOTP Device"
        verbose_name_plural = "TOTP Devices"

    def __str__(self):
        status = "✅ Confirmed" if self.is_confirmed else "⏳ Pending"
        return f"2FA for {self.user.username} ({status})"

    def verify_code(self, code):
        """Verify a TOTP code with ±1 window tolerance."""
        import pyotp
        totp = pyotp.TOTP(self.secret)
        return totp.verify(code, valid_window=1)

    def verify_backup_code(self, code):
        """Verify and consume a one-time backup code."""
        import hashlib
        code_hash = hashlib.sha256(code.strip().encode()).hexdigest()
        if code_hash in self.backup_codes:
            self.backup_codes.remove(code_hash)
            self.save(update_fields=['backup_codes'])
            return True
        return False

    @staticmethod
    def generate_backup_codes(count=8):
        """Generate one-time backup codes and return (plaintext, hashed) lists."""
        import secrets
        import hashlib
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        hashed = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
        return codes, hashed


class WebAuthnCredential(models.Model):
    """
    Stores a WebAuthn / Passkey credential for a user.
    One user can have multiple passkeys (different devices).

    credential_id  — bytes, unique per device
    public_key     — COSE-encoded public key bytes
    sign_count     — monotonic counter against replay attacks
    transports     — ['internal', 'hybrid'] etc.
    device_name    — user-friendly label ("iPhone 15", "Pixel 8")
    """
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='webauthn_credentials',
    )
    credential_id = models.BinaryField(unique=True)
    public_key    = models.BinaryField()
    sign_count    = models.PositiveBigIntegerField(default=0)
    transports    = models.JSONField(default=list, blank=True)
    device_name   = models.CharField(max_length=100, default='Passkey')
    created_at    = models.DateTimeField(auto_now_add=True)
    last_used     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WebAuthn Credential'
        verbose_name_plural = 'WebAuthn Credentials'

    def __str__(self):
        return f'{self.user.username} — {self.device_name} ({self.created_at:%Y-%m-%d})'
