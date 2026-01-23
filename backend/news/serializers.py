from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import (
    Article, Category, Tag, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber,
    YouTubeChannel, PendingArticle, AutoPublishSchedule, EmailPreferences,
    AdminNotification
)


def validate_image_file(image):
    """Validate image file size and format"""
    if not image:
        return
    
    # Check file size (10MB max)
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10) * 1024 * 1024
    if image.size > max_size:
        raise ValidationError(f'Image file too large. Maximum size is {max_size // (1024*1024)}MB.')
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    import os
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f'Invalid image format. Allowed: {", ".join(allowed_extensions)}')
    
    # Check MIME type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if hasattr(image, 'content_type') and image.content_type not in allowed_types:
        raise ValidationError('Invalid image type.')
    
    return image


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'article_count']
    
    def get_article_count(self, obj):
        return obj.articles.count()


class TagSerializer(serializers.ModelSerializer):
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'article_count']
    
    def get_article_count(self, obj):
        return obj.article_set.count()


class CarSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarSpecification
        fields = ['id', 'make', 'model', 'year', 'horsepower', 'torque', 
                  'zero_to_sixty', 'top_speed', 'created_at']
        read_only_fields = ['created_at']


class ArticleImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ArticleImage
        fields = ['id', 'image', 'image_url', 'caption', 'order', 'created_at']
        read_only_fields = ['created_at']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ArticleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for article lists"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    tag_names = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    image_2_url = serializers.SerializerMethodField()
    image_3_url = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'summary', 'category', 'category_name',
                  'tag_names', 'image', 'thumbnail_url', 'image_2', 'image_2_url',
                  'image_3', 'image_3_url', 'price_usd', 'average_rating', 'views',
                  'rating_count', 'created_at', 'updated_at', 'is_published', 'is_favorited']
    
    def get_tag_names(self, obj):
        return [tag.name for tag in obj.tags.all()]
    
    def get_average_rating(self, obj):
        return obj.average_rating()
    
    def get_rating_count(self, obj):
        return obj.rating_count()
    
    def get_is_favorited(self, obj):
        """Check if current user has favorited this article"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, article=obj).exists()
        return False
    
    def get_thumbnail_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return obj.image.url
        return None
    
    def get_image_2_url(self, obj):
        if obj.image_2 and hasattr(obj.image_2, 'url'):
            return obj.image_2.url
        return None
    
    def get_image_3_url(self, obj):
        if obj.image_3 and hasattr(obj.image_3, 'url'):
            return obj.image_3.url
        return None


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Full serializer with all relations"""
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        source='category', 
        write_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Tag.objects.all(), 
        source='tags', 
        write_only=True,
        required=False
    )
    car_specification = CarSpecificationSerializer(read_only=True)
    images = ArticleImageSerializer(many=True, read_only=True, source='gallery')
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    image_2_url = serializers.SerializerMethodField()
    image_3_url = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'content', 'summary', 'category', 'category_id',
                  'tags', 'tag_ids', 'image', 'thumbnail_url', 'image_2', 'image_2_url',
                  'image_3', 'image_3_url', 'youtube_url', 'price_usd', 'views', 
                  'car_specification', 'images', 'average_rating', 'rating_count',
                  'created_at', 'updated_at', 'is_published', 'is_favorited']
        read_only_fields = ['slug', 'views', 'created_at', 'updated_at']
    
    def validate_image(self, value):
        """Validate main image"""
        return validate_image_file(value)
    
    def validate_image_2(self, value):
        """Validate second image"""
        return validate_image_file(value)
    
    def validate_image_3(self, value):
        """Validate third image"""
        return validate_image_file(value)
    
    def get_average_rating(self, obj):
        return obj.average_rating()
    
    def get_rating_count(self, obj):
        return obj.rating_count()
    
    def get_thumbnail_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return obj.image.url
        return None
    
    def get_image_2_url(self, obj):
        if obj.image_2 and hasattr(obj.image_2, 'url'):
            return obj.image_2.url
        return None
    
    def get_image_3_url(self, obj):
        if obj.image_3 and hasattr(obj.image_3, 'url'):
            return obj.image_3.url
        return None
    
    def get_is_favorited(self, obj):
        """Check if current user has favorited this article"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, article=obj).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)
    article_slug = serializers.CharField(source='article.slug', read_only=True)
    article_image = serializers.SerializerMethodField()
    article_category = serializers.SerializerMethodField()
    approved = serializers.BooleanField(source='is_approved')  # Alias для frontend
    author_name = serializers.CharField(source='name', read_only=True)
    # Email hidden from public API for privacy - only available to staff
    
    class Meta:
        model = Comment
        fields = ['id', 'article', 'article_title', 'article_slug', 'article_image',
                  'article_category', 'name', 'email', 'author_name',
                  'content', 'created_at', 'is_approved', 'approved']
        read_only_fields = ['created_at', 'article_title', 'article_slug', 'article_image',
                           'article_category', 'author_name', 'is_approved', 'approved']
        extra_kwargs = {
            'email': {'write_only': True, 'required': False}  # Email is write-only and optional for authenticated users
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        print(f"=== COMMENT SERIALIZER INIT DEBUG ===")
        print(f"Request: {request}")
        print(f"Request user: {request.user if request else 'No request'}")
        print(f"User authenticated: {request and request.user.is_authenticated}")

        if request and request.user.is_authenticated:
            # For authenticated users, name and email are optional (will be filled from profile)
            self.fields['name'].required = False
            self.fields['email'].required = False
            print("Set name and email as optional for authenticated user")
        else:
            print("User not authenticated - name and email required")
    
    def get_article_image(self, obj):
        if obj.article and obj.article.image and hasattr(obj.article.image, 'url'):
            return obj.article.image.url
        return None
    
    def get_article_category(self, obj):
        if obj.article and obj.article.category:
            return obj.article.category.name
        return None
    
    def validate_name(self, value):
        """Sanitize name to prevent XSS"""
        import html
        import re
        request = self.context.get('request')
        if request and request.user.is_authenticated and not value:
            # For authenticated users, allow empty name (will be filled from profile)
            return value
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters")
        if len(value) > 100:
            raise serializers.ValidationError("Name must be less than 100 characters")
        # Remove HTML tags and escape special characters
        cleaned = re.sub(r'<[^>]+>', '', value)
        return html.escape(cleaned.strip())
    
    def validate_email(self, value):
        """Validate email format"""
        import re
        request = self.context.get('request')
        if request and request.user.is_authenticated and not value:
            # For authenticated users, allow empty email (will be filled from profile)
            return value
        if not value:  # For guest users, email is required
            raise serializers.ValidationError("Email is required")
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("Invalid email format")
        return value.lower().strip()
    
    def validate_content(self, value):
        """Sanitize content to prevent XSS"""
        import html
        import re
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("Comment must be at least 5 characters")
        if len(value) > 2000:
            raise serializers.ValidationError("Comment must be less than 2000 characters")
        # Remove HTML tags and escape special characters
        cleaned = re.sub(r'<[^>]+>', '', value)
        return html.escape(cleaned.strip())
    
    def create(self, validated_data):
        request = self.context.get('request')
        print(f"=== COMMENT SERIALIZER CREATE DEBUG ===")
        print(f"Request user authenticated: {request and request.user.is_authenticated}")
        print(f"Request user: {request.user if request else 'No request'}")
        print(f"Initial validated_data: {validated_data}")

        if request and request.user.is_authenticated:
            print(f"Authenticated user processing...")
            # For authenticated users, use their profile data if fields are empty
            if not validated_data.get('name'):
                # Ensure we have a valid name - use username or fallback to 'User'
                username = request.user.username or request.user.first_name or 'User'
                validated_data['name'] = username.strip() or 'User'
                print(f"Set name from profile: {validated_data['name']}")
            if not validated_data.get('email') and request.user.email:
                validated_data['email'] = request.user.email
                print(f"Set email from profile: {validated_data['email']}")
            # If user has no email in profile, use a placeholder or allow empty
            elif not validated_data.get('email'):
                safe_username = (request.user.username or 'user').replace('@', '_').replace('.', '_')
                validated_data['email'] = f"{safe_username}_{request.user.id}@no-email.local"
                print(f"Generated email placeholder: {validated_data['email']}")

        print(f"Final validated_data: {validated_data}")
        result = super().create(validated_data)
        print(f"Created comment: {result}")
        return result


class RatingSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)
    article_slug = serializers.CharField(source='article.slug', read_only=True)
    article_image = serializers.SerializerMethodField()
    article_category = serializers.SerializerMethodField()
    
    class Meta:
        model = Rating
        fields = ['id', 'article', 'article_title', 'article_slug', 'article_image',
                  'article_category', 'user_ip', 'rating', 'created_at']
        read_only_fields = ['created_at', 'user_ip', 'article_title', 'article_slug', 
                           'article_image', 'article_category']
    
    def get_article_image(self, obj):
        if obj.article and obj.article.image and hasattr(obj.article.image, 'url'):
            return obj.article.image.url
        return None
    
    def get_article_category(self, obj):
        if obj.article and obj.article.category:
            return obj.article.category.name
        return None


class FavoriteSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)
    article_slug = serializers.CharField(source='article.slug', read_only=True)
    article_image = serializers.SerializerMethodField()
    article_summary = serializers.CharField(source='article.summary', read_only=True)
    article_category = serializers.SerializerMethodField()
    
    class Meta:
        model = Favorite
        fields = ['id', 'article', 'article_title', 'article_slug', 'article_image', 
                  'article_summary', 'article_category', 'created_at']
        read_only_fields = ['created_at']
    
    def get_article_image(self, obj):
        if obj.article.image and hasattr(obj.article.image, 'url'):
            return obj.article.image.url
        return None
    
    def get_article_category(self, obj):
        if obj.article.category:
            return obj.article.category.name
        return None


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ['id', 'email', 'is_active', 'created_at']
        read_only_fields = ['is_active', 'created_at']


class YouTubeChannelSerializer(serializers.ModelSerializer):
    pending_count = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = YouTubeChannel
        fields = [
            'id', 'name', 'channel_url', 'channel_id',
            'is_enabled', 'auto_publish', 'default_category', 'category_name',
            'last_checked', 'last_video_id', 'videos_processed',
            'pending_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['channel_id', 'last_checked', 'last_video_id', 'videos_processed', 'created_at', 'updated_at']
    
    def get_pending_count(self, obj):
        return obj.pending_articles.filter(status='pending').count()
    
    def get_category_name(self, obj):
        return obj.default_category.name if obj.default_category else None


class PendingArticleSerializer(serializers.ModelSerializer):
    channel_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PendingArticle
        fields = [
            'id', 'youtube_channel', 'channel_name',
            'video_url', 'video_id', 'video_title',
            'title', 'content', 'excerpt',
            'suggested_category', 'category_name',
            'images', 'featured_image',
            'status', 'published_article',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['reviewed_by', 'reviewed_at', 'published_article', 'created_at', 'updated_at']
    
    def get_channel_name(self, obj):
        return obj.youtube_channel.name if obj.youtube_channel else None
    
    def get_category_name(self, obj):
        return obj.suggested_category.name if obj.suggested_category else None
    
    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.username if obj.reviewed_by else None


class AutoPublishScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoPublishSchedule
        fields = [
            'id', 'is_enabled', 'frequency',
            'scan_time_1', 'scan_time_2', 'scan_time_3', 'scan_time_4',
            'last_scan', 'last_scan_result',
            'total_scans', 'total_articles_generated',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['last_scan', 'last_scan_result', 'total_scans', 'total_articles_generated', 'created_at', 'updated_at']


class EmailPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailPreferences
        fields = [
            'newsletter_enabled', 'new_articles_enabled',
            'comment_replies_enabled', 'favorite_updates_enabled',
            'marketing_enabled', 'updated_at'
        ]
        read_only_fields = ['updated_at']


class AdminNotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminNotification
        fields = [
            'id', 'notification_type', 'type_display', 'title', 'message',
            'link', 'priority', 'priority_display', 'is_read',
            'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_time_ago(self, obj):
        """Return human-readable time difference"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        seconds = diff.total_seconds()
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f'{minutes}m ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours}h ago'
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f'{days}d ago'
        else:
            return obj.created_at.strftime('%b %d')
