from django.db import models
from django.utils.text import slugify
from ..image_utils import optimize_image


# Intra-package imports to resolve foreign keys if needed

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
    group = models.ForeignKey('news.TagGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='tags', help_text="Category group for this tag")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

IMAGE_SOURCE_CHOICES = [
    ('youtube', 'YouTube Thumbnail'),
    ('rss_original', 'RSS / Press Release Original'),
    ('pexels', 'Pexels Stock Photo'),
    ('uploaded', 'Manual Upload'),
    ('unknown', 'Unknown'),
]

class Article(models.Model):
    title = models.CharField(max_length=500)
    slug = models.SlugField(blank=True, max_length=250, db_index=True)
    summary = models.TextField(blank=True, help_text="Short description for list view")
    content = models.TextField()
    content_original = models.TextField(blank=True, help_text="Original AI-generated content (before manual edits). Used for AI quality metrics.")
    image = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Main featured image (screenshot 1)")
    image_2 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 2 from video")
    image_3 = models.ImageField(upload_to='articles/', blank=True, null=True, max_length=255, help_text="Screenshot 3 from video")
    youtube_url = models.URLField(max_length=2000, blank=True, help_text="YouTube video URL for AI generation")
    
    # Author / Source Credits
    author_name = models.CharField(max_length=200, blank=True, help_text="Original content creator name")
    author_channel_url = models.URLField(max_length=2000, blank=True, help_text="Original creator channel URL")
    
    # Price field (in USD, converted to other currencies on frontend)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Price in USD (AI extracts from video)")
    
    # Categories and Tags (ManyToMany for flexibility)
    categories = models.ManyToManyField('news.Category', blank=True, related_name='articles')
    tags = models.ManyToManyField('news.Tag', blank=True)
    
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
    
    # ML Engagement Score — combines reader signals into one metric
    engagement_score = models.FloatField(
        default=0.0, db_index=True,
        help_text="Reader engagement score (0-10). Computed from scroll depth, dwell time, ratings, comments."
    )
    engagement_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the engagement score was last recalculated"
    )
    
    image_source = models.CharField(
        max_length=20, choices=IMAGE_SOURCE_CHOICES, default='unknown',
        help_text="Where the article images came from (youtube, rss_original, pexels, uploaded)"
    )
    
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
        from ..image_utils import optimize_image
        from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
        
        # Helper for batch optimization — only process genuinely NEW uploads
        def process_img(field_name):
            img = getattr(self, field_name)
            if not img:
                return
            img_name = getattr(img, 'name', str(img))
            
            # Skip Cloudinary/external URLs/already prefixed paths
            if (img_name.startswith('http') or 
                'cloudinary' in img_name or 
                img_name.startswith('articles/') or 
                img_name.startswith('media/articles/')):
                return
                
            # Skip if already optimized
            if '_optimized' in img_name:
                return
                
            # Now safe to check if it's a fresh upload
            try:
                # In-memory or temporary files are from user uploads/manual approve
                from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
                img_file = getattr(img, 'file', None)
                if not isinstance(img_file, (InMemoryUploadedFile, TemporaryUploadedFile, BytesIO)):
                    return
            except (IOError, OSError, AttributeError):
                return

            try:
                optimized_img = optimize_image(img, max_width=1920, max_height=1080, quality=85)
                if optimized_img:
                    # By now optimize_image returns just a basename filename
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

class ArticleImage(models.Model):
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='gallery')
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

class PendingArticle(models.Model):
    """Articles waiting for review before publishing"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
        ('auto_failed', 'Auto-Publish Failed'),  # Circuit breaker: too many failures
    ]
    
    # Source info (YouTube OR RSS)
    youtube_channel = models.ForeignKey('news.YouTubeChannel', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_articles'
    )
    rss_feed = models.ForeignKey('news.RSSFeed', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_articles'
    )
    
    # YouTube-specific fields (optional)
    video_url = models.URLField(max_length=2000, blank=True, help_text="Source YouTube video URL")
    video_id = models.CharField(max_length=50, blank=True, db_index=True)
    video_title = models.CharField(max_length=500, blank=True)
    
    # Author / Source Credits (preserved from generation)
    author_name = models.CharField(max_length=200, blank=True, help_text="Original content creator name")
    author_channel_url = models.URLField(max_length=2000, blank=True, help_text="Original creator channel URL")
    
    # RSS-specific fields (optional)
    source_url = models.URLField(max_length=2000, blank=True, help_text="Original article/press release URL")
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
    featured_image = models.URLField(max_length=2000, blank=True)
    image_source = models.CharField(
        max_length=20, choices=IMAGE_SOURCE_CHOICES, default='unknown',
        help_text="Where the images came from (youtube, rss_original, pexels, uploaded)"
    )
    
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
    is_auto_published = models.BooleanField(
        default=False, help_text="Was this article auto-published (vs manually reviewed)"
    )
    
    # Circuit breaker — prevent infinite retry loops
    auto_publish_attempts = models.IntegerField(default=0, help_text="Number of auto-publish attempts")
    auto_publish_last_error = models.TextField(blank=True, help_text="Last auto-publish error for debugging")
    auto_publish_last_attempt = models.DateTimeField(null=True, blank=True, help_text="When last auto-publish was attempted")
    
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
        constraints = [
            models.UniqueConstraint(
                fields=['video_id'],
                condition=~models.Q(video_id='') & ~models.Q(status='rejected'),
                name='unique_active_video_id',
            ),
        ]
    
    def __str__(self):
        return f"[{self.status}] {self.title[:50]}"

