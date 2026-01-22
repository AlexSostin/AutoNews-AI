from django.db import models
from django.utils.text import slugify
from .image_utils import optimize_image

class SiteSettings(models.Model):
    """Global site settings managed from admin panel"""
    site_name = models.CharField(max_length=100, default="Fresh Motors")
    site_description = models.TextField(default="Your source for automotive news and reviews")
    contact_email = models.EmailField(default="admin@freshmotors.net")
    
    # Maintenance Mode
    maintenance_mode = models.BooleanField(default=False, help_text="Enable maintenance mode - only admins can access the site")
    maintenance_message = models.TextField(
        default="We're currently making improvements to bring you a better experience. Please check back soon!",
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

class Tag(models.Model):
    name = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(unique=True, blank=True)

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
    image = models.ImageField(upload_to='articles/', blank=True, null=True, help_text="Main featured image (screenshot 1)")
    image_2 = models.ImageField(upload_to='articles/', blank=True, null=True, help_text="Screenshot 2 from video")
    image_3 = models.ImageField(upload_to='articles/', blank=True, null=True, help_text="Screenshot 3 from video")
    youtube_url = models.URLField(blank=True, help_text="YouTube video URL for AI generation")
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='articles')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # SEO Fields
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True, help_text="Soft delete - allows recreating articles with same slug")
    views = models.PositiveIntegerField(default=0, help_text="Number of times this article has been viewed", db_index=True)
    
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
        # Optimize images before saving (skip if already optimized)
        # Disabled for now as it causes issues with AI-generated screenshots
        # if self.image and hasattr(self.image, 'file') and not self.image.name.endswith('_optimized.webp'):
        #     try:
        #         self.image = optimize_image(self.image, max_width=1920, max_height=1080, quality=85)
        #     except Exception as e:
        #         print(f"Image optimization failed: {e}")
        
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
            self.seo_title = self.title
        if not self.seo_description:
            self.seo_description = self.summary[:160]
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
    model_name = models.CharField(max_length=200, help_text="Specific trim or model")
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
    name = models.CharField(max_length=100, help_text="Your name")
    email = models.EmailField(help_text="Your email (won't be published)")
    content = models.TextField(help_text="Your comment")
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, help_text="Admin must approve", db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', 'is_approved', '-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.article.title}"

class Rating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='ratings')
    ip_address = models.CharField(max_length=255, help_text="User fingerprint (IP+UserAgent hash) for preventing multiple votes")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating 1-5 stars")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('article', 'ip_address')  # One vote per IP per article
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rating}★ for {self.article.title}"

class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='gallery/', help_text="Additional images for gallery")
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
