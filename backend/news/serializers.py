from rest_framework import serializers
from .models import Article, Category, Tag, Comment, Rating, CarSpecification, ArticleImage, SiteSettings


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
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'summary', 'category', 'category_name',
                  'tag_names', 'image', 'thumbnail_url', 'average_rating', 
                  'rating_count', 'created_at', 'updated_at', 'is_published']
    
    def get_tag_names(self, obj):
        return [tag.name for tag in obj.tags.all()]
    
    def get_average_rating(self, obj):
        return obj.average_rating()
    
    def get_rating_count(self, obj):
        return obj.rating_count()
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
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
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'content', 'summary', 'category', 'category_id',
                  'tags', 'tag_ids', 'image', 'thumbnail_url', 'youtube_url', 'views', 
                  'car_specification', 'images', 'average_rating', 'rating_count',
                  'created_at', 'updated_at', 'is_published']
        read_only_fields = ['slug', 'views', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        return obj.average_rating()
    
    def get_rating_count(self, obj):
        return obj.rating_count()
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CommentSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'article', 'article_title', 'name', 'email', 'content', 
                  'created_at', 'is_approved']
        read_only_fields = ['created_at']


class RatingSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source='article.title', read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'article', 'article_title', 'user_ip', 'rating', 'created_at']
        read_only_fields = ['created_at', 'user_ip']
