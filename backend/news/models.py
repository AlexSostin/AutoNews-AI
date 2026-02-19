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

class Category(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True, help_text="Show this category in public navigation and lists")

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
    title = models.CharField(max_length=500)
    slug = models.SlugField(blank=True, max_length=250, db_index=True)
    summary = models.TextField(blank=True, help_text="Short description for list view")
    content = models.TextField()
    content_original = models.TextField(blank=True, help_text="Original AI-generated content (before manual edits). Used for AI quality metrics.")
    image = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Main featured image (screenshot 1)")
    image_2 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 2 from video")
    image_3 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 3 from video")
    youtube_url = models.URLField(blank=True, help_text="YouTube video URL for AI generation")
    
    # Author / Source Credits
    author_name = models.CharField(max_length=200, blank=True, help_text="Original content creator name")
    author_channel_url = models.URLField(blank=True, help_text="Original creator channel URL")
    
    # Price field (in USD, converted to other currencies on frontend)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Price in USD (AI extracts from video)")
    
    # Categories and Tags (ManyToMany for flexibility)
    categories = models.ManyToManyField(Category, blank=True, related_name='articles')
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
    
    # Visibility toggles (control what's shown on public article page)
    show_source = models.BooleanField(default=True, help_text="Show source/author credit on public page")
    show_youtube = models.BooleanField(default=True, help_text="Show YouTube video embed on public page")
    show_price = models.BooleanField(default=True, help_text="Show price on public page")
    
    generation_metadata = models.JSONField(null=True, blank=True, help_text="AI generation stats: timing, provider, AI Editor diff")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'is_published'], name='article_created_published_idx'),
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
        from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
        
        # Helper for batch optimization — only process genuinely NEW uploads
        def process_img(field_name):
            img = getattr(self, field_name)
            if not img:
                return
            # Skip if not a fresh upload (existing stored images should never be re-optimized)
            img_file = getattr(img, 'file', None)
            if not isinstance(img_file, (InMemoryUploadedFile, TemporaryUploadedFile, BytesIO)):
                return
            img_name = getattr(img, 'name', str(img))
            # Skip optimization for direct URLs (e.g. Cloudinary URLs assigned during approve)
            if img_name.startswith('http'):
                return
            # Skip if already optimized (check substring, not just endswith, for Cloudinary compat)
            if '_optimized' in img_name:
                return
            try:
                optimized_img = optimize_image(img, max_width=1920, max_height=1080, quality=85)
                if optimized_img:
                    setattr(self, field_name, optimized_img)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[{field_name}] optimization failed: {e}")

        from io import BytesIO
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

class Brand(models.Model):
    """
    Managed brand entity for the car catalog.
    
    Unlike the auto-aggregated brands from CarSpecification.make,
    this model gives admins full control: rename, reorder, merge,
    hide/show brands, upload logos, group sub-brands under parents.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Display name")
    slug = models.SlugField(max_length=120, unique=True, help_text="URL slug")
    logo = models.ImageField(upload_to='brands/', blank=True, help_text="Brand logo")
    country = models.CharField(max_length=50, blank=True, help_text="Country of origin")
    description = models.TextField(blank=True, help_text="Short brand description")
    sort_order = models.IntegerField(default=0, help_text="Manual sort order (0=auto by article count)")
    is_visible = models.BooleanField(default=True, help_text="Show in public catalog")
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sub_brands',
        help_text="Parent brand (e.g. DongFeng for VOYAH)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sort_order', 'name']
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name

    def get_article_count(self):
        """Count articles for this brand (and sub-brands)."""
        from django.db.models import Q
        names = [self.name]
        for sub in self.sub_brands.all():
            names.append(sub.name)
        return CarSpecification.objects.filter(
            make__in=names, article__is_published=True
        ).values('article').distinct().count()

    def get_model_count(self):
        """Count unique models for this brand (and sub-brands)."""
        names = [self.name]
        for sub in self.sub_brands.all():
            names.append(sub.name)
        return CarSpecification.objects.filter(
            make__in=names
        ).exclude(model='').exclude(model='Not specified').values('model').distinct().count()

class BrandAlias(models.Model):
    """Maps brand name variations to a canonical name.
    
    When AI extracts 'DongFeng VOYAH', this table maps it → 'VOYAH'.
    Used automatically during VehicleSpecs → CarSpecification sync.
    """
    alias = models.CharField(
        max_length=100, unique=True,
        help_text="The name variation (what AI might produce, e.g. 'DongFeng VOYAH')"
    )
    canonical_name = models.CharField(
        max_length=100,
        help_text="The correct brand name (e.g. 'VOYAH')"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Brand Aliases"
        ordering = ['canonical_name', 'alias']

    def __str__(self):
        return f"{self.alias} → {self.canonical_name}"

    @classmethod
    def resolve(cls, make):
        """Resolve a make name through aliases. Returns canonical name or original."""
        if not make:
            return make
        try:
            alias = cls.objects.get(alias__iexact=make)
            return alias.canonical_name
        except cls.DoesNotExist:
            return make

class CarSpecification(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name='specs')
    model_name = models.CharField(max_length=200, help_text="Specific trim or model (Legacy)")
    make = models.CharField(max_length=100, blank=True, db_index=True, help_text="Car Brand")
    model = models.CharField(max_length=100, blank=True, db_index=True, help_text="Base Model")
    trim = models.CharField(max_length=100, blank=True, help_text="Trim or Version")
    engine = models.CharField(max_length=200, blank=True)
    horsepower = models.CharField(max_length=50, blank=True)
    torque = models.CharField(max_length=50, blank=True)
    zero_to_sixty = models.CharField(max_length=50, blank=True, help_text="0-60 mph time")
    top_speed = models.CharField(max_length=50, blank=True)
    drivetrain = models.CharField(max_length=50, blank=True, help_text="AWD, FWD, RWD, 4WD")
    price = models.CharField(max_length=100, blank=True)
    release_date = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Manually verified by editor")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When specs were verified")
    
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


class RSSFeed(models.Model):
    """RSS feeds from automotive brands and news sources"""
    SOURCE_TYPES = [
        ('brand', 'Automotive Brand'),
        ('media', 'Automotive Media'),
        ('blog', 'Industry Blog'),
    ]
    
    name = models.CharField(max_length=200, help_text="Feed name for display (e.g., 'Mercedes-Benz Press')")
    feed_url = models.URLField(unique=True, help_text="RSS/Atom feed URL")
    website_url = models.URLField(blank=True, help_text="Main website URL")
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
    logo_url = models.URLField(blank=True, help_text="Brand/source logo URL")
    description = models.TextField(blank=True)
    
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
    
    rss_feed = models.ForeignKey(
        RSSFeed, on_delete=models.CASCADE,
        related_name='news_items'
    )
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True, help_text="Raw HTML content from RSS")
    excerpt = models.TextField(blank=True, help_text="Plain text snippet for preview")
    source_url = models.URLField(blank=True, help_text="Link to original article")
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


class PendingArticle(models.Model):
    """Articles waiting for review before publishing"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
    ]
    
    # Source info (YouTube OR RSS)
    youtube_channel = models.ForeignKey(
        YouTubeChannel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_articles'
    )
    rss_feed = models.ForeignKey(
        RSSFeed, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_articles'
    )
    
    # YouTube-specific fields (optional)
    video_url = models.URLField(blank=True, help_text="Source YouTube video URL")
    video_id = models.CharField(max_length=50, blank=True)
    video_title = models.CharField(max_length=500, blank=True)
    
    # RSS-specific fields (optional)
    source_url = models.URLField(blank=True, help_text="Original article/press release URL")
    content_hash = models.CharField(max_length=64, blank=True, db_index=True, help_text="SHA256 hash for deduplication")
    
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
    quality_score = models.IntegerField(
        default=0,
        help_text="Auto-assessed quality 1-10 (used for auto-publish threshold)"
    )
    
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


class VehicleSpecs(models.Model):
    """
    AI-extracted vehicle specifications from articles.
    Supports multiple trim variants per car model.
    """
    article = models.ForeignKey(
        Article,
        on_delete=models.SET_NULL,
        related_name='vehicle_specs_set',
        null=True, blank=True,
        help_text="Source article (optional)"
    )
    
    # Car identification — used to group trims on /cars/ pages
    make = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Car brand (e.g. Zeekr, BMW, Tesla)"
    )
    model_name = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Model name (e.g. 007 GT, iX3, Model 3)"
    )
    trim_name = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Trim variant (e.g. AWD 100 kWh, Long Range, Performance)"
    )
    
    # Drivetrain
    DRIVETRAIN_CHOICES = [
        ('FWD', 'Front-Wheel Drive'),
        ('RWD', 'Rear-Wheel Drive'),
        ('AWD', 'All-Wheel Drive'),
        ('4WD', 'Four-Wheel Drive'),
    ]
    drivetrain = models.CharField(
        max_length=10,
        choices=DRIVETRAIN_CHOICES,
        null=True, blank=True,
        help_text="Drive configuration"
    )
    motor_count = models.IntegerField(
        null=True, blank=True,
        help_text="Number of electric motors"
    )
    motor_placement = models.CharField(
        max_length=50,
        null=True, blank=True,
        help_text="Motor location (e.g., 'front', 'rear', 'front+rear')"
    )
    
    # Performance
    power_hp = models.IntegerField(
        null=True, blank=True,
        help_text="Power in horsepower"
    )
    power_kw = models.IntegerField(
        null=True, blank=True,
        help_text="Power in kilowatts"
    )
    torque_nm = models.IntegerField(
        null=True, blank=True,
        help_text="Torque in Newton-meters"
    )
    acceleration_0_100 = models.FloatField(
        null=True, blank=True,
        help_text="0-100 km/h acceleration time in seconds"
    )
    top_speed_kmh = models.IntegerField(
        null=True, blank=True,
        help_text="Top speed in km/h"
    )
    
    # EV Specifications
    battery_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Battery capacity in kWh"
    )
    range_km = models.IntegerField(
        null=True, blank=True,
        help_text="Range in kilometers (general)"
    )
    range_wltp = models.IntegerField(
        null=True, blank=True,
        help_text="WLTP range in kilometers"
    )
    range_epa = models.IntegerField(
        null=True, blank=True,
        help_text="EPA range in kilometers"
    )
    range_cltc = models.IntegerField(
        null=True, blank=True,
        help_text="CLTC range in kilometers (Chinese standard)"
    )
    combined_range_km = models.IntegerField(
        null=True, blank=True,
        help_text="Total combined range for PHEVs (gas+electric) in km"
    )
    
    # Charging
    charging_time_fast = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Fast charging time (e.g., '30 min to 80%')"
    )
    charging_time_slow = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Slow/AC charging time"
    )
    charging_power_max_kw = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum charging power in kW"
    )
    
    # Transmission
    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('CVT', 'CVT'),
        ('single-speed', 'Single-Speed'),
        ('dual-clutch', 'Dual-Clutch'),
    ]
    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        null=True, blank=True,
        help_text="Transmission type"
    )
    transmission_gears = models.IntegerField(
        null=True, blank=True,
        help_text="Number of gears"
    )
    
    # General Vehicle Info
    BODY_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('coupe', 'Coupe'),
        ('truck', 'Truck'),
        ('crossover', 'Crossover'),
        ('wagon', 'Wagon'),
        ('shooting_brake', 'Shooting Brake'),
        ('van', 'Van'),
        ('convertible', 'Convertible'),
        ('pickup', 'Pickup'),
        ('liftback', 'Liftback'),
        ('fastback', 'Fastback'),
        ('MPV', 'MPV / Minivan'),
        ('roadster', 'Roadster'),
        ('cabriolet', 'Cabriolet'),
        ('targa', 'Targa'),
        ('limousine', 'Limousine'),
    ]
    body_type = models.CharField(
        max_length=20,
        choices=BODY_TYPE_CHOICES,
        null=True, blank=True,
        help_text="Body style"
    )
    
    FUEL_TYPE_CHOICES = [
        ('EV', 'Electric Vehicle'),
        ('Hybrid', 'Hybrid'),
        ('PHEV', 'Plug-in Hybrid'),
        ('Gas', 'Gasoline'),
        ('Diesel', 'Diesel'),
        ('Hydrogen', 'Hydrogen'),
    ]
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        null=True, blank=True,
        help_text="Fuel/power source type"
    )
    
    seats = models.IntegerField(
        null=True, blank=True,
        help_text="Number of seats"
    )
    
    # Dimensions
    length_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Length in millimeters"
    )
    width_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Width in millimeters"
    )
    height_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Height in millimeters"
    )
    wheelbase_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Wheelbase in millimeters"
    )
    weight_kg = models.IntegerField(
        null=True, blank=True,
        help_text="Curb weight in kilograms"
    )
    cargo_liters = models.IntegerField(
        null=True, blank=True,
        help_text="Cargo/trunk capacity in liters"
    )
    cargo_liters_max = models.IntegerField(
        null=True, blank=True,
        help_text="Max cargo with seats folded in liters"
    )
    ground_clearance_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Ground clearance in millimeters"
    )
    towing_capacity_kg = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum towing capacity in kg"
    )
    
    # Pricing
    price_from = models.IntegerField(
        null=True, blank=True,
        help_text="Starting price"
    )
    price_to = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum price"
    )
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('CNY', 'Chinese Yuan'),
        ('RUB', 'Russian Ruble'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Price currency"
    )
    price_usd_from = models.IntegerField(
        null=True, blank=True,
        help_text="Price in USD (auto-converted from original currency)"
    )
    price_usd_to = models.IntegerField(
        null=True, blank=True,
        help_text="Max price in USD (auto-converted)"
    )
    price_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When price/exchange rate was last updated"
    )
    
    # Additional Info
    year = models.IntegerField(
        null=True, blank=True,
        help_text="Release year"
    )
    model_year = models.IntegerField(
        null=True, blank=True,
        help_text="Model year"
    )
    country_of_origin = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Country where manufactured"
    )
    
    # Technical Details
    platform = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Vehicle platform (e.g., SEA, MEB, E-GMP, TNGA)"
    )
    voltage_architecture = models.IntegerField(
        null=True, blank=True,
        help_text="Electrical architecture voltage (400, 800, 900)"
    )
    suspension_type = models.CharField(
        max_length=200,
        null=True, blank=True,
        help_text="Suspension type (e.g., air suspension, adaptive, McPherson)"
    )
    
    # Flexible extra specs (no migrations needed for new fields)
    extra_specs = models.JSONField(
        default=dict, blank=True,
        help_text="Additional specs as key-value pairs (e.g., {'panoramic_roof': true, 'lidar': 'Hesai ATX'})"
    )
    
    # Metadata
    extracted_at = models.DateTimeField(
        auto_now=True,
        help_text="When specs were last extracted/updated"
    )
    confidence_score = models.FloatField(
        default=0.0,
        help_text="AI extraction confidence (0.0-1.0)"
    )
    
    class Meta:
        verbose_name = "Vehicle Specification"
        verbose_name_plural = "Vehicle Specifications"
        ordering = ['make', 'model_name', 'trim_name']
        unique_together = [('make', 'model_name', 'trim_name')]
    
    def __str__(self):
        parts = [self.make, self.model_name, self.trim_name]
        label = ' '.join(p for p in parts if p)
        if not label and self.article:
            label = self.article.title[:50]
        return f"Specs: {label or 'Unnamed'}"
    
    def get_power_display(self):
        """Return formatted power string"""
        if self.power_hp and self.power_kw:
            return f"{self.power_hp} HP / {self.power_kw} kW"
        elif self.power_hp:
            return f"{self.power_hp} HP"
        elif self.power_kw:
            return f"{self.power_kw} kW"
        return "N/A"
    
    def get_range_display(self):
        """Return formatted range string"""
        if self.range_wltp:
            return f"{self.range_wltp} km (WLTP)"
        elif self.range_epa:
            return f"{self.range_epa} km (EPA)"
        elif self.range_km:
            return f"{self.range_km} km"
        return "N/A"
    
    def get_price_display(self):
        """Return formatted price with USD equivalent for non-USD currencies."""
        if not self.price_from:
            return "N/A"
        
        symbols = {'CNY': '¥', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'RUB': '₽'}
        sym = symbols.get(self.currency, self.currency + ' ')
        
        if self.currency == 'USD':
            if self.price_to:
                return f"${self.price_from:,} – ${self.price_to:,}"
            return f"From ${self.price_from:,}"
        
        # Non-USD: show original + USD equivalent
        if self.price_to:
            main = f"{sym}{self.price_from:,} – {sym}{self.price_to:,}"
        else:
            main = f"From {sym}{self.price_from:,}"
        
        if self.price_usd_from:
            return f"{main} (~${self.price_usd_from:,} USD)"
        
        return main


class ArticleEmbedding(models.Model):
    """
    Persistent storage for article embeddings (vector representations)
    Used for hybrid FAISS + PostgreSQL vector search
    """
    article = models.OneToOneField(
        Article,
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


class ArticleFeedback(models.Model):
    """User-reported issues on articles (hallucinations, errors, typos)"""
    CATEGORY_CHOICES = [
        ('factual_error', 'Factual Error'),
        ('typo', 'Typo / Grammar'),
        ('outdated', 'Outdated Information'),
        ('hallucination', 'AI Hallucination'),
        ('other', 'Other'),
    ]
    
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='feedback')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    message = models.TextField(max_length=1000, help_text="User's description of the issue")
    
    # Anti-spam
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    
    # Moderation
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Article Feedback'
        verbose_name_plural = 'Article Feedback'
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.article.title[:40]} — {self.message[:50]}"


class ArticleTitleVariant(models.Model):
    """A/B testing variants for article titles.
    AI generates 2-3 title variants per article, and the system
    tracks impressions/clicks to determine the best-performing title."""
    
    VARIANT_CHOICES = [
        ('A', 'Variant A (Original)'),
        ('B', 'Variant B'),
        ('C', 'Variant C'),
    ]
    
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='title_variants')
    variant = models.CharField(max_length=1, choices=VARIANT_CHOICES)
    title = models.CharField(max_length=500)
    impressions = models.PositiveIntegerField(default=0, help_text="Number of times shown")
    clicks = models.PositiveIntegerField(default=0, help_text="Number of click-throughs")
    is_winner = models.BooleanField(default=False, help_text="Winning variant (applied as main title)")
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
    auto_publish_today_date = models.DateField(
        null=True, blank=True, help_text="Date for today's counter"
    )
    auto_publish_last_run = models.DateTimeField(
        null=True, blank=True, help_text="When auto-publish last checked"
    )
    
    # === Google Indexing ===
    google_indexing_enabled = models.BooleanField(
        default=True, help_text="Auto-submit published articles to Google Indexing API"
    )
    
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
            self.auto_publish_today_date = today
            self.rss_articles_today = 0
            self.youtube_articles_today = 0
            self.counters_reset_date = today
            self.save(update_fields=[
                'auto_publish_today_count', 'auto_publish_today_date',
                'rss_articles_today', 'youtube_articles_today',
                'counters_reset_date'
            ])
