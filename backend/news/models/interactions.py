from django.db import models
from django.utils.text import slugify
from ..image_utils import optimize_image


# Intra-package imports to resolve foreign keys if needed

class Comment(models.Model):
    MODERATION_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('auto_approved', 'Auto-Approved'),
        ('auto_blocked', 'Auto-Blocked'),
        ('admin_approved', 'Admin Approved'),
        ('admin_rejected', 'Admin Rejected'),
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='comments', help_text="Authenticated user (optional)")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', help_text="Parent comment for replies")
    name = models.CharField(max_length=100, help_text="Your name")
    email = models.EmailField(help_text="Your email (won't be published)")
    content = models.TextField(help_text="Your comment")
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False, help_text="Admin must approve", db_index=True)
    moderation_status = models.CharField(
        max_length=20, choices=MODERATION_STATUS_CHOICES, default='pending',
        help_text="Moderation system decision", db_index=True
    )
    moderation_reason = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Why comment was approved/blocked"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', 'is_approved', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.article.title}"

class CommentModerationLog(models.Model):
    """Tracks admin approve/reject decisions for ML training."""
    DECISION_CHOICES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    comment = models.ForeignKey('news.Comment', on_delete=models.CASCADE, related_name='moderation_logs')
    admin_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='moderation_decisions')
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['decision', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.decision} by {self.admin_user} on comment #{self.comment_id}"

class Rating(models.Model):
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='ratings')
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

class Favorite(models.Model):
    """User favorites/bookmarks"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='favorites')
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'article')  # One favorite per user per article
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} → {self.article.title}"

class ArticleFeedback(models.Model):
    """User-reported issues on articles (hallucinations, errors, typos)"""
    CATEGORY_CHOICES = [
        ('factual_error', 'Factual Error'),
        ('typo', 'Typo / Grammar'),
        ('outdated', 'Outdated Information'),
        ('hallucination', 'AI Hallucination'),
        ('other', 'Other'),
    ]
    
    article = models.ForeignKey('news.Article', on_delete=models.CASCADE, related_name='feedback')
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

