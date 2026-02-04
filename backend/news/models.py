from django.db import models
from django.utils.text import slugify
from .image_utils import optimize_image

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

class Category(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['name']),
        ]

class TagGroup(models.Model):
    """
    Groups for tags (e.g., 'Manufacturers', 'Body Types', 'Features', 'Years')
    Allows organizing the large list of tags into manageable categories.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Tag Group"
        verbose_name_plural = "Tag Groups"
        
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    group = models.ForeignKey(TagGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='tags', help_text="Category group for this tag")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, max_length=250, db_index=True)
    summary = models.TextField(blank=True, help_text="Short description for list view")
    content = models.TextField()
    image = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Main featured image (screenshot 1)")
    image_2 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 2 from video")
    image_3 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 3 from video")
    youtube_url = models.URLField(blank=True, help_text="YouTube video URL for AI generation")
    
    # Author / Source Credits
    author_name = models.CharField(max_length=200, blank=True, help_text="Original content creator name")
    author_channel_url = models.URLField(blank=True, help_text="Original creator channel URL")
    
    # Price field (in USD, converted to other currencies on frontend)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Price in USD (AI extracts from video)")
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='articles')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # SEO Fields
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.TextField(blank=True, help_text="Comma-separated SEO keywords")
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True, help_text="Soft delete - allows recreating articles with same slug")
    views = models.PositiveIntegerField(default=0, help_text="Number of times this article has been viewed", db_index=True)
    is_hero = models.BooleanField(default=False, db_index=True, help_text="Show in Home page Hero section")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'is_published'], name='article_created_published_idx'),
            models.Index(fields=['category', '-created_at'], name='article_category_created_idx'),
            models.Index(fields=['-views'], name='article_views_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_deleted=False),
                name='unique_slug_when_not_deleted'
            )
        ]
    
    def save(self, *args, **kwargs):
        # Optimize images before saving
        from .image_utils import optimize_image
        
        # Helper for batch optimization
        def process_img(field_name):
            img = getattr(self, field_name)
            if img and hasattr(img, 'file') and not img.name.endswith('_optimized.webp'):
                try:
                    optimized_img = optimize_image(img, max_width=1920, max_height=1080, quality=85)
                    if optimized_img:
                        setattr(self, field_name, optimized_img)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"[{field_name}] optimization failed: {e}")

        process_img('image')
        process_img('image_2')
        process_img('image_3')
        
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # Ensure unique slug among non-deleted articles
            while Article.objects.filter(slug=slug, is_deleted=False).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.seo_title:
            self.seo_title = self.title[:200]
        if not self.seo_description:
            summary_text = self.summary or ""
            self.seo_description = summary_text[:160]
        super().save(*args, **kwargs)
    
    def average_rating(self):
        """Calculate average rating (1-5 stars)"""
        from django.db.models import Avg
        avg = self.ratings.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    
    def rating_count(self):
        """Count total ratings"""
        return self.ratings.count()

    def __str__(self):
        return self.title

class CarSpecification(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name='specs')
    model_name = models.CharField(max_length=200, help_text="Specific trim or model (Legacy)")
    make = models.CharField(max_length=100, blank=True, help_text="Car Brand")
    model = models.CharField(max_length=100, blank=True, help_text="Base Model")
    trim = models.CharField(max_length=100, blank=True, help_text="Trim or Version")
    engine = models.CharField(max_length=200, blank=True)
    horsepower = models.CharField(max_length=50, blank=True)
    torque = models.CharField(max_length=50, blank=True)
    zero_to_sixty = models.CharField(max_length=50, blank=True, help_text="0-60 mph time")
    top_speed = models.CharField(max_length=50, blank=True)
    price = models.CharField(max_length=100, blank=True)
    release_date = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"Specs for {self.article.title}"

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='comments', help_text="Authenticated user (optional)")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', help_text="Parent comment for replies")
    name = models.CharField(max_length=100, help_text="Your name")
    email = models.EmailField(help_text="Your email (won't be published)")
    content = models.TextField(help_text="Your comment")
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, help_text="Admin must approve", db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', 'is_approved', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.article.title}"

class Rating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings', help_text="Authenticated user (optional)")
    ip_address = models.CharField(max_length=255, help_text="User fingerprint (IP+UserAgent hash) for preventing multiple votes")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating 1-5 stars")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('article', 'ip_address')  # One vote per IP per article
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.rating}★ for {self.article.title}"

class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='gallery/', max_length=255, help_text="Additional images for gallery")
    caption = models.CharField(max_length=200, blank=True, help_text="Image caption/description")
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Optimize gallery images before saving
        if self.image and hasattr(self.image, 'file'):
            try:
                self.image = optimize_image(self.image, max_width=1920, max_height=1080, quality=85)
            except Exception as e:
                print(f"Gallery image optimization failed: {e}")
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"Image for {self.article.title}"


class Favorite(models.Model):
    """User favorites/bookmarks"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='favorites')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'article')  # One favorite per user per article
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} → {self.article.title}"


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


class YouTubeChannel(models.Model):
    """YouTube channels to monitor for new videos"""
    name = models.CharField(max_length=200, help_text="Channel name for display")
    channel_url = models.URLField(help_text="YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)")
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


class PendingArticle(models.Model):
    """Articles waiting for review before publishing"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
    ]
    
    # Source info
    youtube_channel = models.ForeignKey(
        YouTubeChannel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_articles'
    )
    video_url = models.URLField(help_text="Source YouTube video URL")
    video_id = models.CharField(max_length=50)
    video_title = models.CharField(max_length=500)
    
    # Generated content
    title = models.CharField(max_length=500)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    suggested_category = models.ForeignKey(
        'Category', on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # Images (stored as JSON array of URLs)
    images = models.JSONField(default=list, blank=True)
    featured_image = models.URLField(blank=True)
    
    # Structured Data for Draft Safety
    specs = models.JSONField(default=dict, blank=True, help_text="Car specifications (Make, Model, Year, etc.)")
    tags = models.JSONField(default=list, blank=True, help_text="Suggested tags list")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # If published, link to the article
    published_article = models.ForeignKey(
        'Article', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='source_pending'
    )
    
    # Review
    reviewed_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pending Article"
        verbose_name_plural = "Pending Articles"
    
    def __str__(self):
        return f"[{self.status}] {self.title[:50]}"


class AutoPublishSchedule(models.Model):
    """Settings for automatic YouTube scanning schedule"""
    FREQUENCY_CHOICES = [
        ('once', 'Once a day'),
        ('twice', 'Twice a day'),
        ('four', 'Four times a day'),
        ('manual', 'Manual only'),
    ]
    
    is_enabled = models.BooleanField(default=False, help_text="Enable automatic scanning")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='twice')
    
    # Specific times (24h format)
    scan_time_1 = models.TimeField(default='09:00', help_text="First scan time")
    scan_time_2 = models.TimeField(default='18:00', help_text="Second scan time")
    scan_time_3 = models.TimeField(null=True, blank=True, help_text="Third scan time")
    scan_time_4 = models.TimeField(null=True, blank=True, help_text="Fourth scan time")
    
    # Stats
    last_scan = models.DateTimeField(null=True, blank=True)
    last_scan_result = models.TextField(blank=True)
    total_scans = models.IntegerField(default=0)
    total_articles_generated = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Auto-Publish Schedule"
        verbose_name_plural = "Auto-Publish Schedule"
    
    def __str__(self):
        return f"Schedule: {self.frequency} - {'Enabled' if self.is_enabled else 'Disabled'}"


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
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='search_stats')
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
