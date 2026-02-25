from rest_framework import viewsets, status, filters
from django.db.models import Avg, Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission, AllowAny, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from ..models import (
    Article, Category, Tag, TagGroup, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber, NewsletterHistory,
    YouTubeChannel, RSSFeed, RSSNewsItem, PendingArticle, AdminNotification,
    VehicleSpecs, NewsletterSubscriber, BrandAlias, AutomationSettings
)
from ..serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, TagGroupSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer, SubscriberSerializer, NewsletterHistorySerializer,
    YouTubeChannelSerializer, RSSFeedSerializer, RSSNewsItemSerializer, PendingArticleSerializer,
    AdminNotificationSerializer, VehicleSpecsSerializer, BrandAliasSerializer,
    AutomationSettingsSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)



class GenerateAIImageView(APIView):
    """Generate AI car photo using Gemini Image API and save to article."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return available scene styles."""
        from ai_engine.modules.image_generator import get_available_styles
        return Response({'styles': get_available_styles()})
    
    @method_decorator(ratelimit(key='user', rate='10/d', method='POST', block=True))
    def post(self, request, identifier=None):
        """Generate AI image for an article."""
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=403)
        
        try:
            # Support both numeric pk and slug
            if identifier and identifier.isdigit():
                article = Article.objects.get(pk=int(identifier), is_deleted=False)
            else:
                article = Article.objects.get(slug=identifier, is_deleted=False)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        
        style = request.data.get('style', 'scenic_road')
        image_slot = int(request.data.get('image_slot', 1))
        custom_prompt = request.data.get('custom_prompt', '').strip()
        
        # Get reference image URL
        image_url = None
        if article.image:
            try:
                image_url = article.image.url  # Cloudinary returns full https:// URL
            except Exception:
                img_str = str(article.image)
                if img_str.startswith('http'):
                    image_url = img_str
                else:
                    image_url = request.build_absolute_uri(f'/media/{img_str}')
        
        if not image_url:
            return Response({'error': 'No reference image found on this article. Upload an image first.'}, status=400)
        
        # Get car name from CarSpecification or title
        car_name = article.title
        try:
            spec = article.car_specification
            if spec and spec.make and spec.model:
                year = spec.year or ''
                car_name = f"{year} {spec.make} {spec.model}".strip()
        except Exception:
            pass
        
        # Generate AI image
        from ai_engine.modules.image_generator import generate_car_image
        result = generate_car_image(image_url, car_name, style, custom_prompt=custom_prompt)
        
        if not result['success']:
            return Response({'error': result['error']}, status=500)
        
        # Save the generated image to the article
        import base64
        from django.core.files.base import ContentFile
        
        image_bytes = base64.b64decode(result['image_data'])
        ext = 'png' if 'png' in result.get('mime_type', '') else 'jpg'
        filename = f"ai_generated_{article.id}_{style}.{ext}"
        image_file = ContentFile(image_bytes, name=filename)
        
        # Save to the correct image slot
        if image_slot == 1:
            article.image.save(filename, image_file, save=True)
        elif image_slot == 2:
            article.image_2.save(filename, image_file, save=True)
        elif image_slot == 3:
            article.image_3.save(filename, image_file, save=True)
        
        # Get the saved URL for response
        article.refresh_from_db()
        saved_field = getattr(article, f'image{"" if image_slot == 1 else f"_{image_slot}"}')
        if saved_field:
            try:
                saved_url = saved_field.url
            except Exception:
                saved_url = str(saved_field)
                if saved_url and not saved_url.startswith('http'):
                    saved_url = request.build_absolute_uri(f'/media/{saved_url}')
        else:
            saved_url = ''
        
        return Response({
            'success': True,
            'image_url': saved_url,
            'image_slot': image_slot,
            'style': style,
        })

class SearchPhotosView(APIView):
    """Search for car press photos online using DuckDuckGo Image Search."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, identifier=None):
        """Search for press photos for an article's car."""
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=403)
        
        # Look up article
        try:
            if identifier and identifier.isdigit():
                article = Article.objects.get(pk=int(identifier), is_deleted=False)
            else:
                article = Article.objects.get(slug=identifier, is_deleted=False)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        
        # Build search query from CarSpecification or title
        custom_query = request.query_params.get('q', '').strip()
        if custom_query:
            query = custom_query
        else:
            car_name = article.title
            try:
                spec = article.car_specification
                if spec and spec.make and spec.model:
                    year = spec.year or ''
                    car_name = f"{year} {spec.make} {spec.model}".strip()
            except Exception:
                # Clean up title: remove noise words for better search
                import re
                # Remove common noise terms from car article titles
                noise_words = ['EV', 'PHEV', 'BEV', 'SUV', 'Review', 'Test', 'Drive', 
                             'Range', 'Specs', 'Price', 'vs', 'and', 'the', 'new', 'all-new']
                cleaned = car_name
                for word in noise_words:
                    cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
                # Remove numbers with units (725km, 300hp, etc) but keep year numbers
                cleaned = re.sub(r'\b\d{2,4}(km|hp|kw|ps|mph|kph|kwh|mi)\b', '', cleaned, flags=re.IGNORECASE)
                # Clean up extra whitespace
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if len(cleaned) > 5:
                    car_name = cleaned
            query = f"{car_name} press photo official"
        
        from ai_engine.modules.searcher import search_car_images
        results = search_car_images(query, max_results=20)
        
        return Response({
            'query': query,
            'results': results,
            'count': len(results),
        })

class SaveExternalImageView(APIView):
    """Download an external image URL and save it to an article's image slot."""
    permission_classes = [IsAuthenticated]
    
    @method_decorator(ratelimit(key='user', rate='10/d', method='POST', block=True))
    def post(self, request, identifier=None):
        """Save an external image to an article."""
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=403)
        
        # Look up article
        try:
            if identifier and identifier.isdigit():
                article = Article.objects.get(pk=int(identifier), is_deleted=False)
            else:
                article = Article.objects.get(slug=identifier, is_deleted=False)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        
        image_url = request.data.get('image_url', '').strip()
        image_slot = int(request.data.get('image_slot', 1))
        
        if not image_url:
            return Response({'error': 'image_url is required'}, status=400)
        
        if image_slot not in (1, 2, 3):
            return Response({'error': 'image_slot must be 1, 2, or 3'}, status=400)
        
        # Download the image
        import requests as http_requests
        try:
            resp = http_requests.get(image_url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/*,*/*;q=0.8',
            })
            resp.raise_for_status()
            
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            if 'image' not in content_type:
                return Response({'error': f'URL does not point to an image (Content-Type: {content_type})'}, status=400)
            
        except http_requests.RequestException as e:
            return Response({'error': f'Failed to download image: {str(e)}'}, status=400)
        
        # Determine file extension
        from django.core.files.base import ContentFile
        ext = 'jpg'
        if 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'
        
        # Build filename from article slug
        slug_short = article.slug[:60] if article.slug else f'article_{article.id}'
        filename = f"{slug_short}_{image_slot}.{ext}"
        image_file = ContentFile(resp.content, name=filename)
        
        # Save to the correct image slot
        if image_slot == 1:
            article.image.save(filename, image_file, save=True)
        elif image_slot == 2:
            article.image_2.save(filename, image_file, save=True)
        elif image_slot == 3:
            article.image_3.save(filename, image_file, save=True)
        
        # Get the saved URL for response
        article.refresh_from_db()
        saved_field = getattr(article, f'image{"" if image_slot == 1 else f"_{image_slot}"}')
        if saved_field:
            try:
                saved_url = saved_field.url  # Cloudinary returns full https:// URL
            except Exception:
                saved_url = str(saved_field)
                if saved_url and not saved_url.startswith('http'):
                    saved_url = request.build_absolute_uri(f'/media/{saved_url}')
        else:
            saved_url = ''
        
        return Response({
            'success': True,
            'image_url': saved_url,
            'image_slot': image_slot,
        })

