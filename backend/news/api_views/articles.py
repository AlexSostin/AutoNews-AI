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


# Added inter-module imports




def invalidate_article_cache(article_id=None, slug=None):
    """
    Selectively invalidate cache keys related to articles.
    Much faster than cache.clear() which deletes EVERYTHING.
    
    Args:
        article_id: Article ID to invalidate specific article cache
        slug: Article slug to invalidate specific article cache
    """
    keys_to_delete = []
    
    # Specific article keys
    if article_id:
        keys_to_delete.append(f'article_{article_id}')
    if slug:
        keys_to_delete.append(f'article_slug_{slug}')
    
    # Pattern-based keys (need to scan Redis)
    patterns_to_delete = [
        'article_list_*',     # Article list pages
        'articles_page_*',    # Paginated lists
        'category_*',         # Category views (article counts changed)
        'homepage_*',         # Homepage caches
        'trending_*',         # Trending articles
        'latest_*',           # Latest articles
        'featured_*',         # Featured articles
        'views.decorators.cache.cache_*',  # Django @cache_page keys
        ':1:views.decorators.cache.cache_page*',  # Django cache_page with prefix
    ]
    
    # Delete simple keys first
    if keys_to_delete:
        cache.delete_many(keys_to_delete)
    
    # Delete pattern-matched keys
    try:
        from django.core.cache.backends.redis import RedisCache
        if isinstance(cache, RedisCache) or hasattr(cache, '_cache'):
            # Use Redis SCAN for pattern matching (safe for large datasets)
            redis_client = cache._cache.get_client() if hasattr(cache._cache, 'get_client') else cache._cache
            
            for pattern in patterns_to_delete:
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        # Decode bytes to strings if needed
                        str_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
                        cache.delete_many(str_keys)
                    if cursor == 0:
                        break
            
            logger.info(f"Selectively invalidated article cache (article_id={article_id}, slug={slug})")
        else:
            # Fallback for non-Redis backends - still better than clearing everything
            logger.warning("Non-Redis cache backend - pattern matching not supported")
            cache.delete_many(keys_to_delete)
    except Exception as e:
        logger.warning(f"Failed to invalidate pattern cache keys: {e}")
        # Still better to continue than fail

    # Trigger Next.js on-demand revalidation (non-blocking)
    trigger_nextjs_revalidation()

def trigger_nextjs_revalidation(paths=None):
    """
    Tell Next.js to revalidate its ISR cache immediately.
    Runs in a background thread so it doesn't slow down the API response.
    """
    import threading

    def _revalidate():
        import requests as http_requests
        frontend_url = os.environ.get(
            'FRONTEND_URL',
            'http://frontend:3000' if os.environ.get('RUNNING_IN_DOCKER') else 'http://localhost:3000'
        )
        secret = os.environ.get('REVALIDATION_SECRET', 'freshmotors-revalidate-2026')
        try:
            resp = http_requests.post(
                f'{frontend_url}/api/revalidate',
                json={
                    'secret': secret,
                    'paths': paths or ['/', '/articles', '/trending'],
                },
                timeout=5,
            )
            if resp.ok:
                logger.info(f"Next.js revalidation triggered: {resp.json()}")
            else:
                logger.warning(f"Next.js revalidation failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"Next.js revalidation skipped (frontend may not be running): {e}")

    threading.Thread(target=_revalidate, daemon=True).start()

class IsStaffOrReadOnly(BasePermission):
    """
    Custom permission to only allow staff users to edit objects.
    Read-only for everyone else. Logs unauthorized access attempts.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Write permissions only for staff
        is_allowed = request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
        
        # Log unauthorized write attempts
        if not is_allowed and request.user and request.user.is_authenticated:
            logger.warning(
                f"Unauthorized write attempt: user={request.user.username}, "
                f"method={request.method}, path={request.path}"
            )
        
        return is_allowed

def is_valid_youtube_url(url):
    """Validate YouTube URL to prevent malicious input"""
    if not url or not isinstance(url, str):
        return False
    youtube_regex = r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9_-]{11})(&.*)?$'
    return bool(re.match(youtube_regex, url))


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.filter(is_deleted=False).select_related('specs').prefetch_related('categories', 'tags', 'gallery').annotate(
        avg_rating=Avg('ratings__rating'),
        num_ratings=Count('ratings'),
    )
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['created_at', 'views', 'title']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Allow anyone to rate articles and check their rating,
        but require staff for other write operations
        """
        if self.action in ['rate', 'get_user_rating', 'increment_views']:
            return [AllowAny()]
        return super().get_permissions()
    
    def get_object(self):
        """Support lookup by both slug and ID"""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        # Try to get by slug first, then by ID if slug fails
        try:
            if lookup_value.isdigit():
                # If it's a number, try ID lookup
                obj = queryset.get(id=lookup_value)
            else:
                # Otherwise use slug
                obj = queryset.get(slug=lookup_value)
        except Article.DoesNotExist:
            # Fallback to original lookup
            filter_kwargs = {self.lookup_field: lookup_value}
            obj = get_object_or_404(queryset, **filter_kwargs)
        
        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category', None)
        tag = self.request.query_params.get('tag', None)
        is_published = self.request.query_params.get('is_published', None)
        # Support both 'published' and 'is_published' for backward compatibility
        if is_published is None:
            is_published = self.request.query_params.get('published', None)
        
        # For non-authenticated users, show only published articles
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_published=True)
        
        if category:
            queryset = queryset.filter(categories__slug=category)
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if is_published is not None:
            queryset = queryset.filter(is_published=(is_published.lower() == 'true'))
        
        # Annotate is_favorited for authenticated users (avoids N+1 per-article query)
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                _is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user,
                        article=OuterRef('pk')
                    )
                )
            )
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Don't cache for authenticated users (admins need to see fresh data)
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        # Cache for anonymous users only
        return self._cached_list(request, *args, **kwargs)
    
    @method_decorator(cache_page(300))  # Cache for 5 minutes — cache_signals handles invalidation on changes
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        # Don't cache for authenticated users
        if request.user.is_authenticated:
            return super().retrieve(request, *args, **kwargs)
        return self._cached_retrieve(request, *args, **kwargs)
    
    @method_decorator(cache_page(60))  # Cache for 1 minute (was 5 min)
    def _cached_retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete article and immediately clear ALL cache (delete is rare, reliability > speed)"""
        instance = self.get_object()
        article_id = instance.id
        slug = instance.slug
        instance.delete()
        cache.clear()  # Full clear for delete - reliable, and delete is rare
        logger.info(f"Article deleted and all cache cleared: id={article_id}, slug={slug}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='toggle-publish')
    def toggle_publish(self, request, slug=None):
        """
        Lightning-fast publish/draft toggle — no serializer overhead.
        POST /api/v1/articles/{slug}/toggle-publish/
        Returns: { is_published: true/false }
        """
        article = self.get_object()
        new_status = not article.is_published
        
        # Direct DB update using save() to trigger signals (unlike .update())
        article.is_published = new_status
        article.save(update_fields=['is_published'])
        
        # Lightweight cache invalidation
        try:
            invalidate_article_cache(article_id=article.id, slug=article.slug)
        except Exception:
            pass
        
        # Log the action
        try:
            from news.models import AdminActionLog
            action_type = 'publish' if new_status else 'unpublish'
            AdminActionLog.log(article, request.user, action_type)
        except Exception:
            pass
        
        return Response({
            'success': True,
            'is_published': new_status,
            'message': 'Published' if new_status else 'Moved to drafts',
        })
    
    def update(self, request, *args, **kwargs):
        """Handle article update with special handling for FormData (multipart)"""
        import json
        
        # If this is multipart/form-data, we need to process tag_ids specially
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Don't use .copy() on request.data - it tries to deepcopy file objects which fails
            # Instead, create a new QueryDict and manually copy non-file fields
            from django.http import QueryDict
            
            # Parse tag_ids from JSON string to list
            tag_ids_raw = request.data.get('tag_ids')
            if tag_ids_raw and isinstance(tag_ids_raw, str):
                try:
                    parsed_tags = json.loads(tag_ids_raw)
                    if isinstance(parsed_tags, list):
                        # Modify request.data directly (make it mutable first)
                        if hasattr(request.data, '_mutable'):
                            request.data._mutable = True
                        request.data.setlist('tag_ids', [str(t) for t in parsed_tags])
                        if hasattr(request.data, '_mutable'):
                            request.data._mutable = False
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse tag_ids in ArticleViewSet: {e}")
                    pass
        
        # Helper to check for boolean flags in form data (which come as strings 'true'/'false')
        def is_true(key):
            val = request.data.get(key)
            return val and str(val).lower() == 'true'

        # Perform update in atomic transaction (M2M category updates do DELETE+INSERT,
        # wrapping in transaction prevents lock contention — was causing 41s max query time)
        try:
            from django.db import transaction
            with transaction.atomic():
                response = super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in ArticleViewSet.update super().update: {e}")
            raise
        
        # Then handle deletions if successful
        if response.status_code == 200:
            try:
                instance = self.get_object()
                changed = False
                
                if is_true('delete_image'):
                    instance.image = None
                    changed = True
                if is_true('delete_image_2'):
                    instance.image_2 = None
                    changed = True
                if is_true('delete_image_3'):
                    instance.image_3 = None
                    changed = True
                    
                if changed:
                    instance.save()
                    serializer = self.get_serializer(instance)
                    response = Response(serializer.data)
                
                # Selectively invalidate cache (MUCH faster than cache.clear())
                try:
                    invalidate_article_cache(
                        article_id=instance.id,
                        slug=instance.slug
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to invalidate article cache: {cache_err}")
                
                # Log admin action
                try:
                    from news.models import AdminActionLog
                    AdminActionLog.log(instance, request.user, 'edit_save', details={
                        'image_source': request.data.get('image_source', ''),
                        'has_new_image': bool(request.data.get('image')),
                    })
                except Exception:
                    pass
                    
            except Exception as inner_err:
                logger.error(f"Error in ArticleViewSet.update post-processing: {inner_err}")
                # Don't return 500 if update was already successful
                
        return response


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def generate_from_youtube(self, request):
        """Generate article from YouTube URL with WebSocket progress"""
        import uuid
        
        youtube_url = request.data.get('youtube_url')
        task_id = request.data.get('task_id') or str(uuid.uuid4())[:8]
        
        if not youtube_url:
            return Response(
                {'error': 'youtube_url is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate YouTube URL
        if not is_valid_youtube_url(youtube_url):
            return Response(
                {'error': 'Invalid YouTube URL format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import AI engine
        import traceback
        
        # Add both backend and ai_engine paths for proper imports
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
        
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        if ai_engine_dir not in sys.path:
            sys.path.insert(0, ai_engine_dir)
        
        try:
            from ai_engine.main import generate_article_from_youtube
            from ai_engine.modules.youtube_client import YouTubeClient
        except Exception as import_error:
            print(f"Import error: {import_error}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Failed to import AI engine: {str(import_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get AI provider from request (default to 'gemini')
        provider = request.data.get('provider', 'gemini')
        if provider not in ['groq', 'gemini']:
            return Response(
                {'error': 'Provider must be either "groq" or "gemini"'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Generate article with task_id for WebSocket progress and selected provider
        # Now supporting Draft Safety: is_published=False
        try:
            result = generate_article_from_youtube(
                youtube_url, 
                task_id=task_id, 
                provider=provider,
                is_published=False  # Save as Draft!
            )
        except Exception as gen_error:
            import traceback
            print(f"Generation error: {gen_error}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Article generation failed: {str(gen_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if result.get('success'):
            article_id = result['article_id']
            print(f"[generate_from_youtube] Draft Article created with ID: {article_id}")
            
            # Invalidate cache so new article appears immediately
            from django.core.cache import cache
            invalidate_article_cache(article_id=article_id)
            
            # Fetch the article to verify
            try:
                article = Article.objects.get(id=article_id)
                serializer = self.get_serializer(article)
                return Response({
                    'success': True,
                    'message': 'Article generated successfully (Draft)',
                    'article': serializer.data
                })
            except Article.DoesNotExist:
                return Response(
                    {'error': f'Article was created but cannot be found (ID: {article_id})'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(
                {'error': result.get('error', 'Unknown error')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='translate-enhance')
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def translate_enhance(self, request):
        """Translate Russian text to English and generate a formatted HTML article."""
        russian_text = request.data.get('russian_text', '').strip()
        if not russian_text:
            return Response(
                {'error': 'russian_text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(russian_text) < 20:
            return Response(
                {'error': 'Text is too short. Please provide at least a few sentences.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = request.data.get('category', 'News')
        target_length = request.data.get('target_length', 'medium')
        tone = request.data.get('tone', 'professional')
        seo_keywords = request.data.get('seo_keywords', '')
        provider = request.data.get('provider', 'gemini')

        if target_length not in ('short', 'medium', 'long'):
            target_length = 'medium'
        if tone not in ('professional', 'casual', 'technical'):
            tone = 'professional'
        if provider not in ('groq', 'gemini'):
            provider = 'gemini'

        try:
            from ai_engine.modules.translator import translate_and_enhance
            result = translate_and_enhance(
                russian_text=russian_text,
                category=category,
                target_length=target_length,
                tone=tone,
                seo_keywords=seo_keywords,
                provider=provider,
            )
        except Exception as e:
            logger.error(f'Translation error: {e}')
            return Response(
                {'error': f'Translation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Optionally save (as draft or published)
        save_as_draft = request.data.get('save_as_draft', False)
        save_and_publish = request.data.get('save_and_publish', False)
        should_save = (save_as_draft or save_and_publish) and result.get('title') and result.get('content')

        if should_save:
            try:
                from django.utils.text import slugify
                slug = slugify(result.get('suggested_slug') or result['title'])[:80]
                
                # Make sure slug is unique
                base_slug = slug
                counter = 1
                while Article.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1

                article = Article.objects.create(
                    title=result['title'],
                    slug=slug,
                    content=result['content'],
                    content_original=result.get('content', ''),
                    summary=result.get('summary', ''),
                    seo_description=result.get('meta_description', '')[:160],
                    meta_keywords=', '.join(result.get('seo_keywords', [])),
                    generation_metadata=result.get('generation_metadata'),
                    is_published=save_and_publish,
                )

                # Assign categories
                suggested = result.get('suggested_categories', [])
                if suggested:
                    for cat_name in suggested:
                        cat = Category.objects.filter(name__iexact=cat_name).first()
                        if cat:
                            article.categories.add(cat)
                
                # Fall back to the user-selected category
                if article.categories.count() == 0:
                    cat = Category.objects.filter(name__iexact=category).first()
                    if cat:
                        article.categories.add(cat)

                # --- Auto-assign tags from seo_keywords + smart matching ---
                tags_assigned = []
                try:
                    all_tags = list(Tag.objects.select_related('group').all())
                    title_lower = result['title'].lower()
                    content_lower = result.get('content', '').lower()
                    combined_text = f"{title_lower} {content_lower}"
                    seo_kw_list = result.get('seo_keywords', [])
                    keywords_text = ' '.join(kw.lower() for kw in seo_kw_list)

                    # Tags too generic for content matching (only match via exact keyword)
                    GENERIC_TAGS = {'technology', 'navigation', 'advanced', 'performance', 'budget', 'luxury'}

                    for tag in all_tags:
                        tag_lower = tag.name.lower()
                        matched = False

                        # Skip year tags (e.g. "2025") from fuzzy matching — too many false positives
                        if tag_lower.isdigit():
                            if any(kw.strip().lower() == tag_lower for kw in seo_kw_list):
                                matched = True
                        # 1. Exact keyword match
                        elif any(kw.strip().lower() == tag_lower for kw in seo_kw_list):
                            matched = True
                        # 2. Keyword contains tag name (e.g. "electric vehicle" contains "Electric")
                        elif len(tag_lower) >= 3 and tag_lower not in GENERIC_TAGS and tag_lower in keywords_text:
                            matched = True
                        # 3. Tag name appears in title (e.g. "BYD" in "2026 BYD Seal Review")
                        elif len(tag_lower) >= 2 and (f' {tag_lower} ' in f' {title_lower} ' or title_lower.startswith(f'{tag_lower} ')):
                            matched = True
                        # 4. Brand/body/fuel tags — check content too (not generic ones)
                        elif tag.group and tag.group.name in ('Manufacturers', 'Brands', 'Body Types', 'Fuel Types', 'Segments'):
                            if tag_lower not in GENERIC_TAGS and f' {tag_lower} ' in f' {combined_text} ':
                                matched = True
                        # 5. Special fuel type matching
                        elif tag_lower in ('ev', 'electric') and ('electric' in combined_text or ' ev ' in f' {combined_text} ' or 'bev' in combined_text):
                            matched = True
                        elif tag_lower == 'phev' and 'phev' in combined_text:
                            matched = True
                        elif tag_lower == 'hybrid' and 'hybrid' in combined_text:
                            matched = True

                        if matched and tag.name not in tags_assigned:
                            article.tags.add(tag)
                            tags_assigned.append(tag.name)

                except Exception as tag_err:
                    logger.warning(f'Auto-tag assignment failed: {tag_err}')

                # --- Handle image upload ---
                image_file = request.FILES.get('image')
                if image_file:
                    try:
                        article.image = image_file
                        article.save(update_fields=['image'])
                    except Exception as img_err:
                        logger.warning(f'Image upload failed: {img_err}')

                # --- Auto-create CarSpecification ---
                enrichment_results = {}
                specs_dict = None
                try:
                    # Try to extract make/model/year from title
                    import re as regex
                    title = result['title']
                    year_match = regex.match(
                        r'(\d{4})\s+(.+?)(?:\s+(?:Review|First|Walk|Test|Preview|Deep|Comparison|Gets|Launches|Unveiled|Revealed|Announced))',
                        title, regex.IGNORECASE
                    )
                    if year_match:
                        remaining = year_match.group(2).strip()
                        parts = remaining.split(' ', 1)
                        if len(parts) >= 2:
                            specs_dict = {
                                'make': parts[0],
                                'model': parts[1],
                                'year': int(year_match.group(1)),
                            }
                            # Create CarSpecification (no 'year' field in model)
                            from news.models import CarSpecification
                            CarSpecification.objects.update_or_create(
                                article=article,
                                defaults={
                                    'make': specs_dict['make'],
                                    'model': specs_dict['model'],
                                }
                            )
                            enrichment_results['car_spec'] = {
                                'success': True,
                                'make': specs_dict['make'],
                                'model': specs_dict['model'],
                            }
                except Exception as spec_err:
                    logger.warning(f'Auto CarSpecification failed: {spec_err}')
                    enrichment_results['car_spec'] = {'success': False, 'error': str(spec_err)}

                # --- Run Deep Specs Enrichment (Gemini) ---
                try:
                    from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                    web_context = ''
                    if specs_dict:
                        try:
                            from ai_engine.modules.searcher import get_web_context
                            web_context = get_web_context(specs_dict)
                        except Exception:
                            pass
                    
                    vehicle_specs = generate_deep_vehicle_specs(
                        article,
                        specs=specs_dict,
                        web_context=web_context,
                        provider='gemini'
                    )
                    if vehicle_specs:
                        enrichment_results['deep_specs'] = {
                            'success': True,
                            'make': vehicle_specs.make,
                            'model': vehicle_specs.model_name,
                            'fields_filled': sum(1 for f in vehicle_specs._meta.fields if getattr(vehicle_specs, f.name) is not None),
                        }
                    else:
                        enrichment_results['deep_specs'] = {'success': False, 'error': 'No specs generated'}
                except Exception as ds_err:
                    logger.warning(f'Deep specs enrichment failed: {ds_err}')
                    enrichment_results['deep_specs'] = {'success': False, 'error': str(ds_err)}

                # --- Run A/B Title Variants (Gemini) ---
                try:
                    from ai_engine.main import generate_title_variants
                    generate_title_variants(article, provider='gemini')
                    from news.models import ArticleTitleVariant
                    ab_count = ArticleTitleVariant.objects.filter(article=article).count()
                    enrichment_results['ab_titles'] = {
                        'success': True,
                        'variants_created': ab_count,
                    }
                except Exception as ab_err:
                    logger.warning(f'A/B title generation failed: {ab_err}')
                    enrichment_results['ab_titles'] = {'success': False, 'error': str(ab_err)}

                from django.core.cache import cache
                invalidate_article_cache(article_id=article.id, slug=article.slug)

                result['article_id'] = article.id
                result['article_slug'] = article.slug
                result['saved'] = True
                result['published'] = save_and_publish
                result['tags_assigned'] = tags_assigned
                result['enrichment'] = enrichment_results
                action = 'Published' if save_and_publish else 'Draft saved'
                print(f'💾 {action}: {article.title} (ID: {article.id})')
                if tags_assigned:
                    print(f'🏷️ Tags: {", ".join(tags_assigned)}')
            except Exception as save_error:
                logger.error(f'Failed to save: {save_error}')
                result['saved'] = False
                result['save_error'] = str(save_error)

        return Response({
            'success': True,
            **result,
        })

    @action(detail=True, methods=['post'])
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def rate(self, request, slug=None):
        """Rate an article"""
        article = self.get_object()
        rating_value = request.data.get('rating')
        
        logger.debug(f"Received rating_value: {rating_value}, type: {type(rating_value)}")
        
        if not rating_value:
            return Response(
                {'error': 'Rating value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rating_int = int(rating_value)
            if not (1 <= rating_int <= 5):
                return Response(
                    {'error': 'Rating must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Rating must be a valid number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user IP and user agent for better fingerprinting (harder to bypass with VPN)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create fingerprint (IP + User Agent hash for better uniqueness)
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        
        logger.debug(f"Rating attempt - Article: {article.id}, Fingerprint hash: {fingerprint[:8]}...")
        
        # Check if user already rated (by fingerprint)
        # Standards: If user is authenticated, use user ID as primary key for uniqueness
        if request.user.is_authenticated:
            existing_rating = Rating.objects.filter(article=article, user=request.user).first()
        else:
            existing_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        
        if existing_rating:
            # Update existing rating
            logger.info(f"Updated rating for article {article.id}")
            existing_rating.rating = rating_int
            existing_rating.save()
        else:
            # Create new rating
            logger.info(f"Created new rating for article {article.id}")
            try:
                rating_obj = Rating.objects.create(
                    article=article,
                    user=request.user if request.user.is_authenticated else None,
                    rating=rating_int,
                    ip_address=fingerprint
                )
            except Exception as e:
                logger.error(f"Failed to create rating: {str(e)}")
                return Response(
                    {'error': f'Failed to create rating: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Recalculate average
        article.refresh_from_db()
        
        # CLEAR CACHE to ensure average rating is updated for anonymous users immediately
        # This fixes the bug where rating resets to 0.0 on refresh
        try:
            from django.core.cache import cache
            invalidate_article_cache(article_id=article.id, slug=article.slug)
            logger.info(f"Cache invalidated after rating article: {article.id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
        
        return Response({
            'average_rating': article.average_rating(),
            'rating_count': article.rating_count()
        })
    
    @action(detail=True, methods=['get'], url_path='my-rating')
    def get_user_rating(self, request, slug=None):
        """Get current user's rating for this article"""
        article = self.get_object()
        
        # Get user IP and user agent for fingerprinting
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create fingerprint
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        
        # Get user's rating
        user_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        
        if user_rating:
            return Response({
                'user_rating': user_rating.rating,
                'has_rated': True
            })
        else:
            return Response({
                'user_rating': 0,
                'has_rated': False
            })
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, slug=None):
        """Increment article views using Redis atomic counter for better performance"""
        article = self.get_object()
        
        # Try to use Redis for atomic increment (faster, no race conditions)
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            cache_key = f"article_views:{article.id}"
            
            # Atomic increment in Redis
            new_count = redis_conn.incr(cache_key)
            
            # Sync to database every 10 views (reduces DB writes)
            if new_count % 10 == 0:
                Article.objects.filter(id=article.id).update(views=new_count)
                # Invalidate article cache so the new view count is visible
                try:
                    from django.core.cache import cache
                    invalidate_article_cache(article_id=article.id, slug=article.slug)
                except Exception:
                    pass
            
            return Response({'views': new_count})
        except Exception:
            # Fallback to database if Redis unavailable
            article.views += 1
            article.save(update_fields=['views'])
            return Response({'views': article.views})
    
    @action(detail=True, methods=['post'], url_path='feedback',
            permission_classes=[AllowAny])
    def submit_feedback(self, request, slug=None):
        """Submit user feedback about article issues (hallucinations, errors, etc.)"""
        article = self.get_object()
        
        category = request.data.get('category', 'other')
        message = request.data.get('message', '').strip()
        
        if not message or len(message) < 5:
            return Response({'error': 'Message must be at least 5 characters'}, status=400)
        if len(message) > 1000:
            return Response({'error': 'Message too long (max 1000 characters)'}, status=400)
        
        valid_categories = ['factual_error', 'typo', 'outdated', 'hallucination', 'other']
        if category not in valid_categories:
            category = 'other'
        
        # Rate limit: 1 feedback per IP per article per day
        ip = self._get_client_ip(request)
        from django.utils import timezone
        from datetime import timedelta
        from news.models import ArticleFeedback
        
        if ip:
            recent = ArticleFeedback.objects.filter(
                article=article,
                ip_address=ip,
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            if recent:
                return Response({'error': 'You already submitted feedback for this article today'}, status=429)
        
        feedback = ArticleFeedback.objects.create(
            article=article,
            category=category,
            message=message[:1000],
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300]
        )
        
        return Response({
            'success': True,
            'id': feedback.id,
            'message': 'Thank you for your feedback!'
        }, status=201)
    
    def _get_client_ip(self, request):
        """Extract client IP from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    @action(detail=True, methods=['get'], url_path='ab-title',
            permission_classes=[AllowAny])
    def ab_title(self, request, slug=None):
        """Get the A/B test title variant for this visitor.
        Returns assigned variant based on cookie, or assigns a random one."""
        import random
        from news.models import ArticleTitleVariant
        
        article = self.get_object()
        variants = list(ArticleTitleVariant.objects.filter(article=article))
        
        if not variants:
            return Response({
                'title': article.title,
                'variant': None,
                'ab_active': False
            })
        
        # Googlebot always sees variant A (original)
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_bot = any(bot in user_agent for bot in ['googlebot', 'bingbot', 'yandex', 'spider', 'crawler'])
        
        cookie_key = f'ab_{article.id}'
        assigned_variant = request.COOKIES.get(cookie_key)
        
        if is_bot:
            assigned_variant = 'A'
        
        if assigned_variant and assigned_variant in [v.variant for v in variants]:
            chosen = next(v for v in variants if v.variant == assigned_variant)
        else:
            chosen = random.choice(variants)
            assigned_variant = chosen.variant
        
        # Increment impressions (use F() to avoid race conditions)
        if not is_bot:
            from django.db.models import F
            ArticleTitleVariant.objects.filter(id=chosen.id).update(
                impressions=F('impressions') + 1
            )
        
        response = Response({
            'title': chosen.title,
            'variant': chosen.variant,
            'ab_active': True
        })
        
        # Set cookie for 30 days so visitor always sees same variant
        if not is_bot:
            response.set_cookie(
                cookie_key,
                assigned_variant,
                max_age=30 * 24 * 60 * 60,
                httponly=False,
                samesite='Lax'
            )
        
        return response
    
    @action(detail=True, methods=['post'], url_path='ab-click',
            permission_classes=[AllowAny])
    def ab_click(self, request, slug=None):
        """Record a click (conversion) for an A/B test variant."""
        from news.models import ArticleTitleVariant
        from django.db.models import F
        
        article = self.get_object()
        variant_letter = request.data.get('variant') or request.COOKIES.get(f'ab_{article.id}')
        
        if not variant_letter:
            return Response({'success': False, 'error': 'No variant specified'}, status=400)
        
        updated = ArticleTitleVariant.objects.filter(
            article=article, variant=variant_letter
        ).update(clicks=F('clicks') + 1)
        
        return Response({'success': updated > 0})
    
    @action(detail=True, methods=['get'], url_path='ab-stats',
            permission_classes=[IsAdminUser])
    def ab_stats(self, request, slug=None):
        """Get A/B test statistics for an article (admin only)."""
        from news.models import ArticleTitleVariant
        
        article = self.get_object()
        variants = ArticleTitleVariant.objects.filter(article=article)
        
        data = []
        for v in variants:
            data.append({
                'id': v.id,
                'variant': v.variant,
                'title': v.title,
                'impressions': v.impressions,
                'clicks': v.clicks,
                'ctr': v.ctr,
                'is_winner': v.is_winner,
            })
        
        return Response({
            'article_id': article.id,
            'article_slug': article.slug,
            'original_title': article.title,
            'variants': data,
            'total_impressions': sum(v.impressions for v in variants),
            'total_clicks': sum(v.clicks for v in variants),
        })
    
    @action(detail=True, methods=['post'], url_path='ab-pick-winner',
            permission_classes=[IsAdminUser])
    def ab_pick_winner(self, request, slug=None):
        """Pick the winning A/B variant and apply it as the article title."""
        from news.models import ArticleTitleVariant
        
        article = self.get_object()
        variant_letter = request.data.get('variant')
        
        if not variant_letter:
            return Response({'error': 'Specify variant (A, B, or C)'}, status=400)
        
        try:
            winner = ArticleTitleVariant.objects.get(article=article, variant=variant_letter)
        except ArticleTitleVariant.DoesNotExist:
            return Response({'error': f'Variant {variant_letter} not found'}, status=404)
        
        # Mark winner and unmark others
        ArticleTitleVariant.objects.filter(article=article).update(is_winner=False)
        winner.is_winner = True
        winner.save(update_fields=['is_winner'])
        
        # Apply winning title to article
        article.title = winner.title
        article.save(update_fields=['title'])
        
        return Response({
            'success': True,
            'new_title': winner.title,
            'variant': winner.variant,
            'ctr': winner.ctr
        })

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 15))  # Cache trending for 15 minutes
    def trending(self, request):
        """Get trending articles (most viewed in last 7 days)"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get articles from last 7 days, sorted by views
        week_ago = timezone.now() - timedelta(days=7)
        trending = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=week_ago
        ).order_by('-views')[:10]
        
        serializer = ArticleListSerializer(trending, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))  # Cache popular for 1 hour
    def popular(self, request):
        """Get most popular articles (all time)"""
        popular = Article.objects.filter(
            is_published=True,
            is_deleted=False
        ).order_by('-views')[:10]
        
        serializer = ArticleListSerializer(popular, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def reset_all_views(self, request):
        """Reset all article views to 0 (admin only)"""
        if not request.user.is_staff:
            return Response({'detail': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        count = Article.objects.all().update(views=0)
        return Response({
            'detail': f'Reset views to 0 for {count} articles',
            'articles_updated': count
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def extract_specs(self, request, slug=None):
        """
        Extract vehicle specifications from article using AI
        POST /api/v1/articles/{slug}/extract-specs/
        """
        article = self.get_object()
        
        try:
            from ai_engine.modules.specs_extractor import extract_vehicle_specs
            
            # Extract specs using AI
            specs_data = extract_vehicle_specs(
                title=article.title,
                content=article.content,
                summary=article.summary or ""
            )
            
            # Create or update VehicleSpecs
            vehicle_specs, created = VehicleSpecs.objects.update_or_create(
                article=article,
                defaults=specs_data
            )
            
            serializer = VehicleSpecsSerializer(vehicle_specs)
            
            return Response({
                'success': True,
                'created': created,
                'specs': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error extracting specs for article {article.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='reformat-content')
    def reformat_content(self, request, slug=None):
        """
        Reformat article HTML content using Gemini AI.
        POST /api/v1/articles/{slug}/reformat_content/
        Body: { "content": "<p>raw html...</p>" }
        Returns cleaned, well-structured HTML.
        """
        content = request.data.get('content', '').strip()

        if not content or len(content) < 50:
            return Response({'success': False, 'message': 'Content too short to reformat'},
                          status=status.HTTP_400_BAD_REQUEST)

        system_prompt = """You are a professional article HTML formatter for an automotive news website.
Your job is to reformat the given HTML content into clean, well-structured, SEO-friendly HTML.
Return ONLY the reformatted HTML — no markdown, no code fences, no explanation."""

        format_prompt = f"""Reformat this article HTML content following these strict rules:

STRUCTURE RULES:
- Use <h2> for main section headings (max 5-7 words per heading, descriptive and SEO-friendly)
- Use <h3> for subsections if needed  
- Use <p> for paragraphs — keep them SHORT (2-4 sentences max)
- Use <ul><li> bullet lists for specifications, features, pros/cons
- Every <h2> or <h3> MUST have content after it — if a section is empty, REMOVE the heading entirely
- End the article with a proper concluding paragraph (don't leave articles hanging mid-sentence)

BOLD (<strong>) RULES — BE CONSERVATIVE:
- ONLY use <strong> for: car brand names (BMW, Tesla, etc.), specific model names (Model Y, M5, etc.), and key numerical specs (422 HP, 650 km range, $45,000)
- Do NOT bold: years (2026), publication names (Sunday Times), generic terms (plug-in hybrid, EV, SUV), CEO names, or adjectives
- Maximum 3-5 bold items per paragraph — if everything is bold, nothing stands out
- When a brand+model appears together, bold the whole thing: <strong>BMW M5</strong>, not <strong>BMW</strong> <strong>M5</strong>

CONTENT RULES:
- Keep ALL factual information — do NOT remove real data
- Do NOT add or invent any new information
- Remove speculative/unconfirmed sections (e.g. "US Market Outlook", rumored pricing without source)
- Remove generic filler paragraphs with no real information
- Remove duplicate information — if the same fact appears twice, keep once
- Keep the article language as-is (don't translate)

CLEANUP RULES:
- No inline styles, no CSS classes, no <div> wrappers
- No empty tags (<p></p>, <h2></h2>) or whitespace-only elements
- No empty sections (heading followed immediately by another heading with nothing between)
- Images (<img>) should be preserved as-is
- Ensure proper nesting of all HTML tags

HTML CONTENT TO REFORMAT:
{content[:15000]}

Return ONLY the reformatted HTML."""

        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result = provider.generate_completion(
                format_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=8000,
            )

            # Clean up potential markdown code fences
            import re
            cleaned = result.strip()
            cleaned = re.sub(r'^```(?:html)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Post-processing: remove empty sections (heading with no content after it)
            # Remove <h2>...</h2> or <h3>...</h3> followed immediately by another heading or end of content
            cleaned = re.sub(r'<h([23])>[^<]*</h\1>\s*(?=<h[23]>|$)', '', cleaned)
            # Remove empty paragraphs
            cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
            # Clean up excessive whitespace
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = cleaned.strip()

            if not cleaned or len(cleaned) < 50:
                return Response({
                    'success': False,
                    'message': 'AI returned empty or too short content',
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # Log successful reformat
            try:
                from news.models import AdminActionLog
                original_len = len(content)
                new_len = len(cleaned)
                AdminActionLog.log(self.get_object(), request.user, 'reformat', details={
                    'original_length': original_len,
                    'new_length': new_len,
                    'reduction_pct': round((original_len - new_len) / original_len * 100, 1) if original_len else 0,
                })
            except Exception:
                pass

            return Response({
                'success': True,
                'content': cleaned,
                'original_length': len(content),
                'new_length': len(cleaned),
            })

        except Exception as e:
            logger.error(f'Reformat content failed: {e}')
            try:
                from news.models import AdminActionLog
                AdminActionLog.log(self.get_object(), request.user, 'reformat', success=False, details={'error': str(e)})
            except Exception:
                pass
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='regenerate')
    def regenerate(self, request, slug=None):
        """
        Regenerate article content using AI.
        Auto-detects source type: YouTube (re-downloads transcript) or RSS (re-expands press release).
        
        POST /api/v1/articles/{slug}/regenerate/
        Body: { "provider": "gemini"|"groq" }
        
        Updates existing article in-place (preserves slug, images, publish status).
        Backs up original content to content_original.
        """
        article = self.get_object()
        
        provider = request.data.get('provider', 'gemini')
        if provider not in ['groq', 'gemini']:
            return Response({
                'success': False,
                'message': 'Provider must be "groq" or "gemini"',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            youtube_url = article.youtube_url
            source_type = None
            result = None
            
            # ── AUTO-DETECT SOURCE TYPE ──
            if youtube_url:
                # YouTube article → re-download transcript and regenerate
                source_type = 'youtube'
                from ai_engine.main import _generate_article_content, generate_title_variants
                result = _generate_article_content(youtube_url, provider=provider)
                
                if not result.get('success'):
                    return Response({
                        'success': False,
                        'message': f"AI generation failed: {result.get('error', 'Unknown error')}",
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                # RSS article → find source RSSNewsItem and re-expand press release
                source_type = 'rss'
                from news.models import RSSNewsItem, PendingArticle as PendingArticleModel
                from ai_engine.modules.article_generator import expand_press_release
                from ai_engine.modules.utils import clean_title
                from ai_engine.main import generate_title_variants
                import re as _re
                
                # Trace back: Article ← PendingArticle ← RSSNewsItem
                rss_item = None
                source_url = ''
                press_release_text = ''
                
                # Method 1: Via PendingArticle reverse relation
                pending = PendingArticleModel.objects.filter(published_article=article).first()
                if pending:
                    rss_item = RSSNewsItem.objects.filter(pending_article=pending).first()
                    if not rss_item and pending.source_url:
                        source_url = pending.source_url
                
                # Method 2: Try finding by author_channel_url (which stores the source URL)
                if not rss_item and not source_url and article.author_channel_url:
                    rss_item = RSSNewsItem.objects.filter(
                        source_url=article.author_channel_url
                    ).first()
                    if not rss_item:
                        source_url = article.author_channel_url
                
                if rss_item:
                    # Found the original RSS item — use its content
                    press_release_text = rss_item.content or rss_item.excerpt or ''
                    source_url = rss_item.source_url or source_url
                    
                    # Strip HTML tags to get plain text
                    if '<' in press_release_text:
                        press_release_text = _re.sub(r'<[^>]+>', ' ', press_release_text)
                        press_release_text = _re.sub(r'\s+', ' ', press_release_text).strip()
                elif source_url:
                    # No RSS item found but we have a URL — try to fetch the page
                    try:
                        from ai_engine.modules.web_search import search_and_extract
                        web_results = search_and_extract(article.title, max_results=3)
                        press_release_text = web_results if web_results else article.title
                    except Exception:
                        press_release_text = article.title
                
                if not press_release_text or len(press_release_text.strip()) < 50:
                    return Response({
                        'success': False,
                        'message': 'Cannot regenerate: no source content found. '
                                   'The original RSS news item may have been deleted, '
                                   'and no source URL is available to re-fetch.',
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not source_url:
                    source_url = article.author_channel_url or 'N/A'
                
                # Expand the press release with the new prompt
                expanded_content = expand_press_release(
                    press_release_text=press_release_text,
                    source_url=source_url,
                    provider=provider
                )
                
                if not expanded_content or len(expanded_content) < 200:
                    return Response({
                        'success': False,
                        'message': 'AI returned empty or too short content',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # Extract title from generated content
                title_match = _re.search(r'<h2[^>]*>(.*?)</h2>', expanded_content)
                ai_title = clean_title(title_match.group(1)) if title_match else article.title
                
                # Extract summary (first <p> tag)
                summary_match = _re.search(r'<p>(.*?)</p>', expanded_content)
                ai_summary = ''
                if summary_match:
                    ai_summary = _re.sub(r'<[^>]+>', '', summary_match.group(1))[:300]
                
                # Build result dict (same shape as YouTube result)
                word_count = len(_re.sub(r'<[^>]+>', ' ', expanded_content).split())
                result = {
                    'success': True,
                    'title': ai_title,
                    'content': expanded_content,
                    'summary': ai_summary or article.summary,
                    'generation_metadata': {
                        'provider': provider,
                        'source_type': 'rss',
                        'source_url': source_url,
                        'word_count': word_count,
                        'rss_item_id': rss_item.id if rss_item else None,
                    },
                    'specs': {},
                    'tag_names': [],
                }
            
            # ── SHARED POST-PROCESSING (both YouTube and RSS) ──
            
            # Backup current content
            article.content_original = article.content
            
            # Update article fields
            article.title = result['title']
            article.content = result['content']
            article.summary = result['summary']
            article.generation_metadata = result.get('generation_metadata')
            
            # Update SEO keywords
            if result.get('meta_keywords'):
                article.meta_keywords = result['meta_keywords']
            
            # Update author info if available (YouTube only)
            if result.get('author_name'):
                article.author_name = result['author_name']
            if result.get('author_channel_url'):
                article.author_channel_url = result['author_channel_url']
            
            # Update price if extracted
            specs = result.get('specs') or {}
            if specs.get('price'):
                import re
                price_str = specs['price']
                price_match = re.search(r'[\$€£]?([\d,]+)', price_str.replace(',', ''))
                if price_match:
                    try:
                        article.price_usd = int(price_match.group(1))
                    except (ValueError, TypeError):
                        pass
            
            article.save()
            
            # Update tags
            if result.get('tag_names'):
                from news.models import Tag
                new_tags = []
                for tag_name in result['tag_names']:
                    tag, _ = Tag.objects.get_or_create(
                        name=tag_name,
                        defaults={'slug': tag_name.lower().replace(' ', '-')}
                    )
                    new_tags.append(tag)
                article.tags.set(new_tags)
            
            # Update CarSpecification
            if specs and (specs.get('make') or specs.get('model')):
                try:
                    from news.models import CarSpecification
                    car_spec, created = CarSpecification.objects.get_or_create(article=article)
                    for field in ['make', 'model', 'trim', 'horsepower', 'torque', 
                                  'zero_to_sixty', 'top_speed', 'drivetrain', 'price']:
                        if specs.get(field):
                            setattr(car_spec, field, str(specs[field]))
                    if specs.get('year'):
                        car_spec.release_date = str(specs['year'])
                    car_spec.save()
                except Exception as spec_err:
                    logger.warning(f'CarSpecification update failed: {spec_err}')
            
            # Regenerate A/B title variants
            try:
                from news.models import ArticleTitleVariant
                ArticleTitleVariant.objects.filter(article=article).delete()
                generate_title_variants(article, provider=provider)
            except Exception as ab_err:
                logger.warning(f'A/B title regeneration failed: {ab_err}')
            
            # Invalidate cache
            invalidate_article_cache(article_id=article.id, slug=article.slug)
            
            serializer = self.get_serializer(article)
            
            # Log the regeneration action
            try:
                from news.models import AdminActionLog
                AdminActionLog.log(article, request.user, 'regenerate', details={
                    'provider': provider,
                    'source_type': source_type,
                    'word_count': result.get('generation_metadata', {}).get('word_count'),
                })
            except Exception:
                pass
            
            return Response({
                'success': True,
                'message': f'Article regenerated ({source_type}) with {provider}',
                'article': serializer.data,
                'generation_metadata': result.get('generation_metadata'),
            })
            
        except Exception as e:
            import traceback
            logger.error(f'Regenerate failed: {e}\n{traceback.format_exc()}')
            try:
                from news.models import AdminActionLog
                AdminActionLog.log(article, request.user, 'regenerate', success=False, details={'error': str(e)[:200]})
            except Exception:
                pass
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='re-enrich')
    def re_enrich(self, request, slug=None):
        """
        Re-enrich article metadata using AI (Deep Specs + A/B Titles + Web Search).
        Does NOT modify article content — safe to run on any published article.
        POST /api/v1/articles/{slug}/re-enrich/
        """
        article = self.get_object()
        results = {
            'deep_specs': None,
            'ab_titles': None,
            'web_search': None,
        }
        errors = []

        # --- Step 1: Web Search Enrichment (updates CarSpecification) ---
        try:
            from news.models import CarSpecification
            car_spec = CarSpecification.objects.filter(article=article).first()
            specs_dict = None
            web_context = ''

            if car_spec and car_spec.make:
                # CarSpecification has no 'year' field — extract from title
                import re
                _year = None
                _y_match = re.search(r'\b(20[2-3]\d)\b', article.title)
                if _y_match:
                    _year = int(_y_match.group(1))
                elif car_spec.release_date:
                    _ry = re.search(r'(20[2-3]\d)', car_spec.release_date)
                    if _ry:
                        _year = int(_ry.group(1))
                specs_dict = {
                    'make': car_spec.make or '',
                    'model': car_spec.model or '',
                    'trim': car_spec.trim or '',
                    'year': _year,
                    'horsepower': car_spec.horsepower,
                    'torque': car_spec.torque or '',
                    'acceleration': car_spec.zero_to_sixty or '',
                    'top_speed': car_spec.top_speed or '',
                    'drivetrain': car_spec.drivetrain or '',
                    'price': car_spec.price or '',
                }
            else:
                # Multi-pattern title parser for make/model extraction
                import re
                title = article.title
                year = None
                make = None
                model_name = None

                m = re.match(r'(\d{4})\s+(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Comparison|Test))?$', title, re.IGNORECASE)
                if m:
                    year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()
                if not make:
                    m = re.match(r'(?:First\s+Drive|Review|Test\s+Drive)[:\s]+(\d{4})\s+(\S+)\s+(.+?)(?:\s+-\s+.+)?$', title, re.IGNORECASE)
                    if m:
                        year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()
                        if ' - ' in model_name:
                            model_name = model_name.split(' - ')[0].strip()
                if not make:
                    m = re.match(r'(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Walkaround|Comparison|Test))', title, re.IGNORECASE)
                    if m:
                        make, model_name = m.group(1), m.group(2).strip()
                if not make:
                    try:
                        from news.auto_tags import KNOWN_BRANDS, BRAND_DISPLAY_NAMES
                        title_lower = title.lower()
                        for brand in KNOWN_BRANDS:
                            if title_lower.startswith(brand) or title_lower.startswith(brand + ' '):
                                make = BRAND_DISPLAY_NAMES.get(brand, brand.title())
                                rest = title[len(brand):].strip()
                                model_match = re.match(r'(\S+(?:\s+\S+)?)', rest)
                                if model_match:
                                    model_name = model_match.group(1)
                                break
                    except ImportError:
                        pass
                if not year:
                    y_match = re.search(r'\b(20[2-3]\d)\b', title)
                    if y_match:
                        year = int(y_match.group(1))
                if make and model_name:
                    specs_dict = {'make': make, 'model': model_name, 'year': year}

            if specs_dict and specs_dict.get('make'):
                try:
                    from ai_engine.modules.searcher import get_web_context
                    web_context = get_web_context(specs_dict)
                    results['web_search'] = {
                        'success': True,
                        'context_length': len(web_context),
                    }
                except Exception as ws_err:
                    errors.append(f'Web search: {ws_err}')
                    results['web_search'] = {'success': False, 'error': str(ws_err)}
            else:
                results['web_search'] = {'success': False, 'error': 'No make/model found'}

        except Exception as e:
            errors.append(f'Web search setup: {e}')
            results['web_search'] = {'success': False, 'error': str(e)}

        # --- Step 2: Deep Specs Enrichment (creates/updates VehicleSpecs) ---
        try:
            from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
            vehicle_specs = generate_deep_vehicle_specs(
                article,
                specs=specs_dict,
                web_context=web_context,
                provider='gemini'
            )
            if vehicle_specs:
                results['deep_specs'] = {
                    'success': True,
                    'make': vehicle_specs.make,
                    'model': vehicle_specs.model_name,
                    'trim': vehicle_specs.trim_name or 'Standard',
                    'fields_filled': sum(1 for f in vehicle_specs._meta.fields if getattr(vehicle_specs, f.name) is not None),
                }
            else:
                results['deep_specs'] = {'success': False, 'error': 'No specs generated'}
        except Exception as ds_err:
            errors.append(f'Deep specs: {ds_err}')
            results['deep_specs'] = {'success': False, 'error': str(ds_err)}

        # --- Step 3: A/B Title Variants ---
        try:
            from ai_engine.main import generate_title_variants
            from news.models import ArticleTitleVariant
            existing_count = ArticleTitleVariant.objects.filter(article=article).count()

            if existing_count == 0:
                generate_title_variants(article, provider='gemini')
                new_count = ArticleTitleVariant.objects.filter(article=article).count()
                results['ab_titles'] = {
                    'success': True,
                    'variants_created': new_count,
                }
            else:
                results['ab_titles'] = {
                    'success': True,
                    'skipped': True,
                    'existing_variants': existing_count,
                    'message': 'A/B variants already exist',
                }
        except Exception as ab_err:
            errors.append(f'A/B titles: {ab_err}')
            results['ab_titles'] = {'success': False, 'error': str(ab_err)}

        # --- Step 4: Smart Auto-Tags (with auto-creation) ---
        try:
            from news.auto_tags import auto_tag_article
            tag_result = auto_tag_article(article, use_ai=True)
            results['smart_tags'] = {
                'success': True,
                'new_tags_created': tag_result['created'],
                'existing_tags_matched': tag_result['matched'],
                'total_added': tag_result['total'],
                'ai_used': tag_result['ai_used'],
            }
        except Exception as tag_err:
            errors.append(f'Smart tags: {tag_err}')
            results['smart_tags'] = {'success': False, 'error': str(tag_err)}

        # --- Summary ---
        success_count = sum(1 for r in results.values() if r and r.get('success'))
        total = len(results)

        # Log the re-enrich action
        try:
            from news.models import AdminActionLog
            AdminActionLog.log(article, request.user, 're_enrich', success=success_count > 0, details={
                'steps_completed': f'{success_count}/{total}',
                'deep_specs': results.get('deep_specs', {}).get('success', False),
                'ab_titles': results.get('ab_titles', {}).get('success', False),
                'web_search': results.get('web_search', {}).get('success', False),
                'make': results.get('deep_specs', {}).get('make', ''),
                'model': results.get('deep_specs', {}).get('model_name', ''),
            })
        except Exception:
            pass

        return Response({
            'success': success_count > 0,
            'message': f'{success_count}/{total} enrichment steps completed',
            'results': results,
            'errors': errors if errors else None,
        })

    @action(detail=False, methods=['post'], url_path='bulk-re-enrich')
    def bulk_re_enrich(self, request):
        """
        Bulk re-enrich multiple articles — background thread + polling.
        POST /api/v1/articles/bulk-re-enrich/
        Body: { "mode": "missing"|"selected"|"all", "article_ids": [...] }
        
        Returns { task_id, total } immediately. Poll /bulk-re-enrich-status/?task_id=xxx for progress.
        """
        import threading
        import uuid as _uuid
        from django.core.cache import cache
        from news.models import VehicleSpecs, ArticleTitleVariant, CarSpecification

        mode = request.data.get('mode', 'missing')
        article_ids = request.data.get('article_ids', [])

        published = Article.objects.filter(is_published=True, is_deleted=False)

        if mode == 'selected' and article_ids:
            articles = published.filter(id__in=article_ids)
        elif mode == 'missing':
            articles_with_specs = VehicleSpecs.objects.values_list('article_id', flat=True)
            articles_with_ab = ArticleTitleVariant.objects.values_list('article_id', flat=True)
            articles = published.exclude(
                id__in=set(articles_with_specs) & set(articles_with_ab)
            )
        else:
            articles = published

        total_articles = articles.count()
        article_id_list = list(articles.order_by('id').values_list('id', flat=True))
        task_id = str(_uuid.uuid4())[:8]

        # Store initial state in cache (TTL = 1 hour)
        cache.set(f'bulk_enrich_{task_id}', {
            'status': 'running',
            'current': 0,
            'total': total_articles,
            'results': [],
            'success_count': 0,
            'error_count': 0,
            'message': 'Starting enrichment...',
            'elapsed_seconds': 0,
        }, timeout=3600)

        def _process_task():
            """Background thread — processes articles and updates cache."""
            import re
            import time as _time
            from django.core.cache import cache as _cache
            from django.db import connection

            success_total = 0
            errors_total = 0
            all_results = []
            start_time = _time.time()

            if total_articles == 0:
                _cache.set(f'bulk_enrich_{task_id}', {
                    'status': 'done',
                    'current': 0,
                    'total': 0,
                    'results': [],
                    'success_count': 0,
                    'error_count': 0,
                    'message': 'All articles are fully enriched!',
                    'elapsed_seconds': 0,
                }, timeout=3600)
                return

            for idx, art_id in enumerate(article_id_list, 1):
                try:
                    article = Article.objects.get(id=art_id)
                except Article.DoesNotExist:
                    continue

                article_result = {
                    'id': article.id,
                    'title': article.title[:80],
                    'steps': {},
                    'errors': [],
                }

                # --- Step 1: Web Search ---
                specs_dict = None
                web_context = ''
                try:
                    car_spec = CarSpecification.objects.filter(article=article).first()
                    if car_spec and car_spec.make:
                        _year = None
                        _y_match = re.search(r'\b(20[2-3]\d)\b', article.title)
                        if _y_match:
                            _year = int(_y_match.group(1))
                        elif car_spec.release_date:
                            _ry = re.search(r'(20[2-3]\d)', car_spec.release_date)
                            if _ry:
                                _year = int(_ry.group(1))
                        specs_dict = {
                            'make': car_spec.make or '',
                            'model': car_spec.model or '',
                            'trim': car_spec.trim or '',
                            'year': _year,
                        }
                    else:
                        title = article.title
                        year = None
                        make = None
                        model_name = None

                        # Pattern 1: "2026 BYD Qin L DM-i Review"
                        m = re.match(r'(\d{4})\s+(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Comparison|Test))?$', title, re.IGNORECASE)
                        if m:
                            year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()

                        # Pattern 2: "First Drive: 2026 NIO ET9 - Luxury Electric Sedan"
                        if not make:
                            m = re.match(r'(?:First\s+Drive|Review|Test\s+Drive)[:\s]+(\d{4})\s+(\S+)\s+(.+?)(?:\s+-\s+.+)?$', title, re.IGNORECASE)
                            if m:
                                year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()
                                if ' - ' in model_name:
                                    model_name = model_name.split(' - ')[0].strip()

                        # Pattern 3: "BYD Seal 06 GT Electric Hatchback Walkaround" (no year)
                        if not make:
                            m = re.match(r'(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Walkaround|Comparison|Test))', title, re.IGNORECASE)
                            if m:
                                make, model_name = m.group(1), m.group(2).strip()

                        # Pattern 4: known brands fallback
                        if not make:
                            try:
                                from news.auto_tags import KNOWN_BRANDS, BRAND_DISPLAY_NAMES
                                title_lower = title.lower()
                                for brand in KNOWN_BRANDS:
                                    if title_lower.startswith(brand) or title_lower.startswith(brand + ' '):
                                        make = BRAND_DISPLAY_NAMES.get(brand, brand.title())
                                        rest = title[len(brand):].strip()
                                        model_match = re.match(r'(\S+(?:\s+\S+)?)', rest)
                                        if model_match:
                                            model_name = model_match.group(1)
                                        break
                            except ImportError:
                                pass

                        if not year:
                            y_match = re.search(r'\b(20[2-3]\d)\b', title)
                            if y_match:
                                year = int(y_match.group(1))

                        if make and model_name:
                            specs_dict = {'make': make, 'model': model_name, 'year': year}

                    if specs_dict and specs_dict.get('make'):
                        try:
                            from ai_engine.modules.searcher import get_web_context
                            web_context = get_web_context(specs_dict)
                            article_result['steps']['web_search'] = True
                        except Exception:
                            pass
                except Exception:
                    pass

                # --- Step 2: Deep Specs ---
                existing_vs = VehicleSpecs.objects.filter(article=article).first()
                has_populated_specs = existing_vs and (existing_vs.power_hp or existing_vs.torque_nm) and existing_vs.length_mm
                
                # Force re-enrich for PHEVs with suspicious ranges
                # Small battery (<50kWh) with huge range (>500km) = likely combined, not electric
                if has_populated_specs and existing_vs.battery_kwh and existing_vs.battery_kwh < 50:
                    if (existing_vs.range_km and existing_vs.range_km > 500) or \
                       (existing_vs.range_cltc and existing_vs.range_cltc > 500):
                        print(f"⚠️ Forcing PHEV re-enrich: {existing_vs.make} {existing_vs.model_name} "
                              f"(battery={existing_vs.battery_kwh}kWh, range_km={existing_vs.range_km}, range_cltc={existing_vs.range_cltc})")
                        has_populated_specs = False  # Force through to generate_deep_vehicle_specs
                
                if not has_populated_specs and specs_dict and specs_dict.get('make'):
                    try:
                        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                        vehicle_specs = generate_deep_vehicle_specs(
                            article, specs=specs_dict, web_context=web_context, provider='gemini'
                        )
                        if vehicle_specs:
                            # Count filled fields for the report
                            key_fields = {}
                            for fn in ['power_hp', 'torque_nm', 'battery_kwh', 'range_km', 'range_cltc', 'length_mm', 'weight_kg', 'price_from']:
                                val = getattr(vehicle_specs, fn, None)
                                if val is not None:
                                    key_fields[fn] = val
                            total_filled = sum(1 for f in vehicle_specs._meta.fields if getattr(vehicle_specs, f.name) is not None and f.name not in ('id',))
                            article_result['steps']['deep_specs'] = True
                            article_result['deep_specs_detail'] = {
                                'make': vehicle_specs.make,
                                'model': vehicle_specs.model_name,
                                'fields_filled': total_filled,
                                'key': key_fields,
                            }
                        else:
                            article_result['steps']['deep_specs'] = False
                    except Exception as e:
                        article_result['errors'].append(f'Deep specs: {e}')
                        article_result['steps']['deep_specs'] = False
                elif has_populated_specs:
                    article_result['steps']['deep_specs'] = 'skipped'
                    vs = existing_vs
                    
                    # Normalize model name even for skipped records
                    if specs_dict and specs_dict.get('make'):
                        try:
                            from ai_engine.modules.deep_specs import _clean_model_name
                            from news.auto_tags import BRAND_DISPLAY_NAMES
                            norm_make = BRAND_DISPLAY_NAMES.get((specs_dict.get('make', '') or '').lower().strip(), specs_dict.get('make', ''))
                            cleaned_model = _clean_model_name(vs.model_name, norm_make)
                            vs_update_fields = []
                            if vs.model_name != cleaned_model:
                                vs.model_name = cleaned_model
                                vs_update_fields.append('model_name')
                            if vs.make != norm_make:
                                vs.make = norm_make
                                vs_update_fields.append('make')
                            if vs_update_fields:
                                vs.save(update_fields=vs_update_fields)
                                print(f"📝 Normalized skipped VehicleSpecs: {norm_make} {cleaned_model}")
                        except Exception:
                            pass
                    
                    # Include detail for skipped
                    key_fields = {}
                    for fn in ['power_hp', 'torque_nm', 'battery_kwh', 'range_km', 'range_cltc', 'length_mm', 'weight_kg', 'price_from']:
                        val = getattr(vs, fn, None)
                        if val is not None:
                            key_fields[fn] = val
                    article_result['deep_specs_detail'] = {
                        'make': vs.make,
                        'model': vs.model_name,
                        'fields_filled': sum(1 for f in vs._meta.fields if getattr(vs, f.name) is not None and f.name not in ('id',)),
                        'key': key_fields,
                    }
                else:
                    article_result['steps']['deep_specs'] = 'no_specs'

                # --- Step 3: A/B Titles ---
                has_ab = ArticleTitleVariant.objects.filter(article=article).exists()
                if not has_ab:
                    try:
                        from ai_engine.main import generate_title_variants
                        generate_title_variants(article, provider='gemini')
                        article_result['steps']['ab_titles'] = True
                    except Exception as e:
                        article_result['errors'].append(f'A/B titles: {e}')
                else:
                    article_result['steps']['ab_titles'] = 'skipped'

                # --- Step 4: Smart Auto-Tags ---
                try:
                    from news.auto_tags import auto_tag_article
                    tag_result = auto_tag_article(article, use_ai=True)
                    created_count = len(tag_result['created'])
                    matched_count = len(tag_result['matched'])
                    article_result['steps']['smart_tags'] = created_count + matched_count
                    if tag_result['created']:
                        article_result['steps']['tags_created'] = tag_result['created']
                    if tag_result['ai_used']:
                        article_result['steps']['ai_used'] = True
                except Exception as e:
                    article_result['errors'].append(f'Smart tags: {e}')

                if article_result['errors']:
                    errors_total += 1
                else:
                    success_total += 1

                all_results.append(article_result)

                # Update cache with progress (every article)
                elapsed = round(_time.time() - start_time, 1)
                _cache.set(f'bulk_enrich_{task_id}', {
                    'status': 'running',
                    'current': idx,
                    'total': total_articles,
                    'results': all_results[-10:],  # Keep last 10 for display
                    'success_count': success_total,
                    'error_count': errors_total,
                    'message': f'Processing {idx}/{total_articles}...',
                    'elapsed_seconds': elapsed,
                }, timeout=3600)

            # Final state — build summary
            elapsed = round(_time.time() - start_time, 1)

            # Build deep specs summary
            ds_generated = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') is True)
            ds_skipped = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') == 'skipped')
            ds_failed = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') is False)
            ds_no_specs = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') == 'no_specs')
            total_fields = sum(r.get('deep_specs_detail', {}).get('fields_filled', 0) for r in all_results)
            tags_added = sum(r.get('steps', {}).get('smart_tags', 0) for r in all_results if isinstance(r.get('steps', {}).get('smart_tags'), int))

            summary = {
                'deep_specs': {
                    'generated': ds_generated,
                    'skipped': ds_skipped,
                    'failed': ds_failed,
                    'no_data': ds_no_specs,
                    'total_fields_filled': total_fields,
                },
                'tags_added': tags_added,
                'duration': elapsed,
            }

            _cache.set(f'bulk_enrich_{task_id}', {
                'status': 'done',
                'current': total_articles,
                'total': total_articles,
                'results': all_results,
                'success_count': success_total,
                'error_count': errors_total,
                'message': f'Bulk enrichment completed: {success_total}/{total_articles} articles processed in {elapsed}s',
                'elapsed_seconds': elapsed,
                'summary': summary,
            }, timeout=3600)

            # Close DB connection for this thread
            connection.close()

        # Start background thread
        thread = threading.Thread(target=_process_task, daemon=True)
        thread.start()

        return Response({
            'task_id': task_id,
            'total': total_articles,
            'message': f'Enrichment started for {total_articles} articles',
        })

    @action(detail=False, methods=['get'], url_path='bulk-re-enrich-status')
    def bulk_re_enrich_status(self, request):
        """
        Poll enrichment progress.
        GET /api/v1/articles/bulk-re-enrich-status/?task_id=xxx
        """
        from django.core.cache import cache

        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=400)

        state = cache.get(f'bulk_enrich_{task_id}')
        if not state:
            return Response({'error': 'Task not found or expired'}, status=404)

        return Response(state)

    @action(detail=False, methods=['get'], url_path='debug-vehicle-specs')
    def debug_vehicle_specs(self, request):
        """
        Debug endpoint — dump all VehicleSpecs (admin only).
        GET /api/v1/articles/debug-vehicle-specs/?make=ZEEKR&model=X EV
        """
        from news.models import VehicleSpecs

        make = request.query_params.get('make', '')
        model = request.query_params.get('model', '')

        qs = VehicleSpecs.objects.all()
        if make:
            qs = qs.filter(make__iexact=make)
        if model:
            qs = qs.filter(model_name__iexact=model)

        results = []
        for vs in qs.order_by('make', 'model_name')[:50]:
            fields = {}
            for f in vs._meta.fields:
                val = getattr(vs, f.name)
                if val is not None and f.name not in ('id',):
                    fields[f.name] = str(val) if not isinstance(val, (int, float, bool, type(None))) else val
            results.append(fields)

        return Response({
            'count': qs.count(),
            'results': results,
        })
    
    @action(detail=True, methods=['get'])
    def similar_articles(self, request, slug=None):
        """
        Find similar articles using vector search + make/model fallback.
        GET /api/v1/articles/{slug}/similar-articles/
        
        Priority:
        1. AI vector similarity (best)
        2. Same make+model articles (CarSpecification)
        3. Same make articles
        4. Same category
        """
        article = self.get_object()
        result_ids = []
        
        # 1. Try AI vector similarity first
        try:
            from ai_engine.modules.vector_search import get_vector_engine
            engine = get_vector_engine()
            similar = engine.find_similar_articles(article.id, k=15)
            result_ids = [s['article_id'] for s in similar]
        except Exception as e:
            logger.warning(f"Vector search failed for {article.id}: {e}")
        
        # 2. If < 6 results, augment with make/model matching
        if len(result_ids) < 6:
            try:
                from news.models import CarSpecification
                car_spec = CarSpecification.objects.filter(article=article).first()
                
                if car_spec and car_spec.make and car_spec.make != 'Not specified':
                    existing_ids = set(result_ids) | {article.id}
                    
                    # 2a. Same make + model (highest relevance)
                    if car_spec.model and car_spec.model != 'Not specified':
                        same_model = (
                            CarSpecification.objects
                            .filter(make__iexact=car_spec.make, model__iexact=car_spec.model,
                                    article__is_published=True, article__is_deleted=False)
                            .exclude(article_id__in=existing_ids)
                            .values_list('article_id', flat=True)[:5]
                        )
                        result_ids.extend(same_model)
                        existing_ids.update(same_model)
                    
                    # 2b. Same make, different model
                    same_make = (
                        CarSpecification.objects
                        .filter(make__iexact=car_spec.make,
                                article__is_published=True, article__is_deleted=False)
                        .exclude(article_id__in=existing_ids)
                        .values_list('article_id', flat=True)[:8]
                    )
                    result_ids.extend(same_make)
            except Exception as e:
                logger.warning(f"Make/model fallback failed: {e}")
        
        # 3. If still < 6, add from same category
        if len(result_ids) < 6:
            try:
                existing_ids = set(result_ids) | {article.id}
                cat_ids = article.categories.values_list('id', flat=True)
                if cat_ids:
                    same_cat = (
                        Article.objects
                        .filter(categories__id__in=cat_ids, is_published=True, is_deleted=False)
                        .exclude(id__in=existing_ids)
                        .order_by('-views_count')
                        .values_list('id', flat=True)[:10]
                    )
                    result_ids.extend(same_cat)
            except Exception:
                pass
        
        # Deduplicate while preserving order
        seen = set()
        unique_ids = []
        for aid in result_ids:
            if aid not in seen and aid != article.id:
                seen.add(aid)
                unique_ids.append(aid)
        
        articles = Article.objects.filter(
            id__in=unique_ids[:15],
            is_published=True,
            is_deleted=False
        )
        
        # Preserve original ordering
        id_order = {aid: i for i, aid in enumerate(unique_ids)}
        sorted_articles = sorted(articles, key=lambda a: id_order.get(a.id, 999))
        
        serializer = ArticleListSerializer(sorted_articles, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'similar_articles': serializer.data
        })

class CommentViewSet(viewsets.ModelViewSet):
    """
    Comments API with rate limiting to prevent spam.
    - Anyone can create comments (rate limited to 10/hour per IP)
    - Staff can approve/delete comments
    - Authenticated users can see their own comment history
    """
    queryset = Comment.objects.select_related('article', 'user')
    serializer_class = CommentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Allow anyone to create comments (guests can comment),
        but require staff for approve/delete actions
        """
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['approve', 'my_comments']:
            return [IsAuthenticated()]
        return [IsStaffOrReadOnly()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        is_approved = self.request.query_params.get('is_approved', None)
        # Support 'approved' alias from frontend
        if is_approved is None:
            is_approved = self.request.query_params.get('approved', None)
        
        # Filter by article
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        # Filter by approval status
        if is_approved is not None:
            queryset = queryset.filter(is_approved=(str(is_approved).lower() == 'true'))
        
        # Only filter out replies for list actions, not for detail actions (approve, delete, etc.)
        if self.action == 'list':
            include_replies = self.request.query_params.get('include_replies', 'false')
            if include_replies.lower() != 'true':
                queryset = queryset.filter(parent__isnull=True)
            
        return queryset
    
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Create comment with rate limiting and honeypot spam protection."""
        # Honeypot: hidden 'website' field — real users never fill it,
        # but spam bots auto-fill every field. Silently reject.
        honeypot = request.data.get('website', '')
        if honeypot:
            logger.warning(
                f"🍯 Honeypot caught spam bot: website='{honeypot}' | "
                f"IP: {request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))}"
            )
            # Return fake success so bot doesn't retry
            return Response({'id': 0, 'status': 'created'}, status=status.HTTP_201_CREATED)
        
        # If user is authenticated, save user reference
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if request.user.is_authenticated:
            comment = serializer.save(user=request.user)
        else:
            comment = serializer.save()
        
        # Run comment through moderation engine
        try:
            from news.comment_moderator import moderate_comment
            result = moderate_comment(
                content=comment.content,
                name=comment.name,
                email=comment.email,
                user=request.user if request.user.is_authenticated else None,
                article_id=comment.article_id,
            )
            comment.moderation_status = result.status
            comment.moderation_reason = result.reason[:255]
            comment.is_approved = result.is_approved
            comment.save(update_fields=['moderation_status', 'moderation_reason', 'is_approved'])
            logger.info(
                f"💬 Comment moderation: {result.status} | "
                f"reason: {result.reason} | name: {comment.name}"
            )
        except Exception as e:
            logger.warning(f"Comment moderation error: {e}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['patch', 'post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve or reject comment — also logs decision for ML training."""
        comment = self.get_object()
        
        # Check if 'approved' is in request data (support both keys)
        is_approved = request.data.get('approved')
        if is_approved is None:
            is_approved = request.data.get('is_approved', True)
            
        comment.is_approved = bool(is_approved)
        comment.moderation_status = 'admin_approved' if comment.is_approved else 'admin_rejected'
        comment.moderation_reason = f"{'Approved' if comment.is_approved else 'Rejected'} by {request.user.username}"
        comment.save(update_fields=['is_approved', 'moderation_status', 'moderation_reason'])
        
        # Log decision for ML training
        try:
            from news.models import CommentModerationLog
            CommentModerationLog.objects.create(
                comment=comment,
                admin_user=request.user,
                decision='approved' if comment.is_approved else 'rejected',
            )
        except Exception as e:
            logger.warning(f"Failed to log moderation decision: {e}")
        
        serializer = self.get_serializer(comment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_comments(self, request):
        """Get all comments by the current authenticated user"""
        # Filter by user (for authenticated comments) OR by email (for guest comments)
        user_comments = self.get_queryset().filter(user=request.user)
        email_comments = self.get_queryset().filter(email=request.user.email, user__isnull=True)
        
        # Combine both querysets
        from django.db.models import Q
        comments = self.get_queryset().filter(
            Q(user=request.user) | Q(email=request.user.email, user__isnull=True)
        ).distinct()
        
        serializer = self.get_serializer(comments, many=True)
        return Response({
            'count': comments.count(),
            'results': serializer.data
        })

class RatingViewSet(viewsets.ModelViewSet):
    """
    Ratings API with rate limiting.
    - Users can rate articles (rate limited to 20/hour per IP)
    - Authenticated users can see their rating history
    """
    queryset = Rating.objects.select_related('article', 'user')
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action == 'my_ratings':
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create rating with user IP and user reference if authenticated"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0]
        else:
            user_ip = request.META.get('REMOTE_ADDR')
        
        # Save with user reference if authenticated
        if request.user.is_authenticated:
            serializer.save(ip_address=user_ip, user=request.user)
        else:
            serializer.save(ip_address=user_ip)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_ratings(self, request):
        """Get all ratings by the current authenticated user"""
        ratings = self.get_queryset().filter(user=request.user)
        
        serializer = self.get_serializer(ratings, many=True)
        return Response({
            'count': ratings.count(),
            'results': serializer.data
        })

class ArticleImageViewSet(viewsets.ModelViewSet):
    queryset = ArticleImage.objects.select_related('article')
    serializer_class = ArticleImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['order', 'created_at']
    ordering = ['order']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_param = self.request.query_params.get('article', None)
        
        if article_param:
            # Support both numeric ID and slug
            if article_param.isdigit():
                queryset = queryset.filter(article_id=article_param)
            else:
                queryset = queryset.filter(article__slug=article_param)
            
        return queryset

class FavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user favorites
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return favorites for current user"""
        return Favorite.objects.filter(user=self.request.user).select_related('article').prefetch_related('article__categories')
    
    def create(self, request, *args, **kwargs):
        """Add article to favorites"""
        article_id = request.data.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if article exists
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response(
                {'detail': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already favorited
        if Favorite.objects.filter(user=request.user, article=article).exists():
            return Response(
                {'detail': 'Article already in favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create favorite
        favorite = Favorite.objects.create(user=request.user, article=article)
        serializer = self.get_serializer(favorite)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Remove article from favorites"""
        favorite = self.get_object()
        favorite.delete()
        return Response({'detail': 'Removed from favorites'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle favorite status for an article"""
        article_id = request.data.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if article exists
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response(
                {'detail': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Toggle favorite
        favorite, created = Favorite.objects.get_or_create(user=request.user, article=article)
        
        if not created:
            # Already exists - remove it
            favorite.delete()
            return Response({
                'detail': 'Removed from favorites',
                'is_favorited': False
            })
        else:
            # Created new favorite
            serializer = self.get_serializer(favorite)
            return Response({
                'detail': 'Added to favorites',
                'is_favorited': True,
                'favorite': serializer.data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if article is favorited"""
        article_id = request.query_params.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_favorited = Favorite.objects.filter(
            user=request.user,
            article_id=article_id
        ).exists()
        
        return Response({'is_favorited': is_favorited})

class ArticleFeedbackViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing user-submitted article feedback."""
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        from news.models import ArticleFeedback
        qs = ArticleFeedback.objects.select_related('article').order_by('-created_at')
        
        # Filter by resolved status
        resolved = self.request.query_params.get('resolved')
        if resolved == 'true':
            qs = qs.filter(is_resolved=True)
        elif resolved == 'false':
            qs = qs.filter(is_resolved=False)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        
        return qs
    
    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        data = []
        for fb in (page if page is not None else qs[:100]):
            data.append({
                'id': fb.id,
                'article_id': fb.article_id,
                'article_title': fb.article.title if fb.article else '',
                'article_slug': fb.article.slug if fb.article else '',
                'category': fb.category,
                'category_display': fb.get_category_display(),
                'message': fb.message,
                'ip_address': fb.ip_address,
                'is_resolved': fb.is_resolved,
                'admin_notes': fb.admin_notes,
                'created_at': fb.created_at.isoformat(),
            })
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from news.models import ArticleFeedback
        fb = ArticleFeedback.objects.get(pk=pk)
        fb.is_resolved = True
        fb.admin_notes = request.data.get('admin_notes', fb.admin_notes)
        fb.save(update_fields=['is_resolved', 'admin_notes'])
        return Response({'success': True})
    
    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        from news.models import ArticleFeedback
        fb = ArticleFeedback.objects.get(pk=pk)
        fb.is_resolved = False
        fb.save(update_fields=['is_resolved'])
        return Response({'success': True})

