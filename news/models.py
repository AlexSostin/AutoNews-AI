from django.db import models
from django.utils.text import slugify

class SiteSettings(models.Model):
    """Global site settings managed from admin panel"""
    site_name = models.CharField(max_length=100, default="AutoNews")
    site_description = models.TextField(default="Your source for automotive news and reviews")
    contact_email = models.EmailField(default="admin@autonews.com")
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    
    # SEO
    default_meta_description = models.CharField(max_length=160, blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True, help_text="GA4 Measurement ID")
    google_adsense_id = models.CharField(max_length=50, blank=True, help_text="ca-pub-XXXXXX")
    
    # Footer
    footer_text = models.TextField(default="© 2026 AutoNews. All rights reserved.")
    
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
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=250)
    summary = models.TextField(blank=True, help_text="Short description for list view")
    content = models.TextField()
    image = models.ImageField(upload_to='articles/', blank=True, null=True)
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='articles')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # SEO Fields
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
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
    is_approved = models.BooleanField(default=False, help_text="Admin must approve")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.name} on {self.article.title}"

class Rating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='ratings')
    ip_address = models.GenericIPAddressField(help_text="User IP for preventing multiple votes")
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
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"Image for {self.article.title}"
