from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from ..models import Article, PendingArticle, Category, Tag, CarSpecification, VehicleSpecs
from ..serializers import PendingArticleSerializer
from ._shared import invalidate_article_cache
import os
import logging

logger = logging.getLogger(__name__)


class PendingArticleViewSet(viewsets.ModelViewSet):
    """
    Manage pending articles waiting for review.
    Staff only.
    """
    queryset = PendingArticle.objects.select_related(
        'youtube_channel',
        'rss_feed',
        'suggested_category'
    ).all()
    serializer_class = PendingArticleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'video_title']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = PendingArticle.objects.select_related(
            'youtube_channel',
            'rss_feed',
            'suggested_category'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)
        
        # Filter by RSS feed ID
        rss_feed_id = self.request.query_params.get('rss_feed')
        if rss_feed_id:
            queryset = queryset.filter(rss_feed_id=rss_feed_id)
        
        # Filter only RSS articles (exclude YouTube)
        only_rss = self.request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        # Filter only YouTube articles (exclude RSS)
        only_youtube = self.request.query_params.get('only_youtube')
        exclude_rss = self.request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve and publish a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Create the actual article
        try:
            from django.utils.text import slugify
            import uuid
            
            # Generate unique slug
            base_slug = slugify(pending.title)[:80]
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            
            is_published = request.data.get('publish', True)
            
            # Extract author info from channel if available
            author_name = pending.author_name
            author_channel_url = pending.author_channel_url
            
            if not author_name:
                if pending.youtube_channel:
                    author_name = pending.youtube_channel.name
                    author_channel_url = pending.youtube_channel.channel_url
                elif pending.rss_feed:
                    # For RSS articles, use feed name and source URL
                    author_name = pending.rss_feed.name
                    author_channel_url = pending.source_url or pending.rss_feed.feed_url

            article = Article.objects.create(
                title=pending.title,
                slug=slug,
                content=pending.content,
                summary=pending.excerpt or pending.content[:200],
                is_published=is_published,
                youtube_url=pending.video_url,
                author_name=author_name,
                author_channel_url=author_channel_url,
                image_source=pending.image_source or 'unknown',
            )
            
            # Add category (ManyToMany field)
            # For RSS articles, use suggested_category or fallback to "News"
            if pending.rss_feed:
                if pending.suggested_category:
                    article.categories.add(pending.suggested_category)
                else:
                    # Fallback to "News" category for RSS articles
                    from news.models import Category
                    news_category, _ = Category.objects.get_or_create(
                        slug='news',
                        defaults={'name': 'News', 'description': 'General automotive news'}
                    )
                    article.categories.add(news_category)
            elif pending.suggested_category:
                # For non-RSS articles (YouTube), only add if exists
                article.categories.add(pending.suggested_category)
            
            
            # Handle Images (Upload local files or save Cloudinary URLs)
            logger.info(f"[APPROVE] Processing images for article '{article.title[:50]}'")
            logger.info(f"[APPROVE] pending.images = {pending.images}")
            logger.info(f"[APPROVE] pending.featured_image = {pending.featured_image}")
            
            image_sources = []
            if pending.images and isinstance(pending.images, list):
                image_sources = pending.images[:3]
            elif pending.featured_image:
                image_sources = [pending.featured_image]
            
            if image_sources:
                from django.core.files import File
                from django.core.files.base import ContentFile
                import requests as img_requests
                for i, image_path in enumerate(image_sources):
                    if not image_path: continue
                    
                    try:
                        file_name = f"{slug}_{i+1}.jpg"
                        content_file = None
                        
                        # Case A+B: Any URL (Cloudinary, Pexels, etc) — download and upload via .save()
                        if image_path.startswith('http'):
                            logger.info(f"[APPROVE] Downloading image {i+1} from URL: {image_path[:100]}")
                            
                            # Extract domain for Referer header
                            from urllib.parse import urlparse
                            parsed = urlparse(image_path)
                            domain = f"{parsed.scheme}://{parsed.netloc}"
                            
                            # Try multiple header combinations for resilience
                            header_variants = [
                                {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'image/*,*/*;q=0.8',
                                },
                                {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'image/*,*/*;q=0.8',
                                    'Referer': domain,
                                },
                                {
                                    'User-Agent': 'Googlebot-Image/1.0',
                                    'Accept': 'image/*',
                                },
                            ]
                            
                            resp = None
                            for attempt, headers in enumerate(header_variants, 1):
                                try:
                                    resp = img_requests.get(image_path, timeout=15, headers=headers)
                                    logger.info(f"[APPROVE] Attempt {attempt}: status={resp.status_code}, size={len(resp.content)} bytes")
                                    if resp.status_code == 200 and len(resp.content) > 1000:
                                        break
                                except Exception as dl_err:
                                    logger.warning(f"[APPROVE] Attempt {attempt} failed: {dl_err}")
                                    resp = None
                            
                            if resp and resp.status_code == 200 and len(resp.content) > 0:
                                # Validate magic bytes — ensure downloaded content is actually an image
                                VALID_MAGIC = [b'\xff\xd8\xff', b'\x89PNG', b'RIFF', b'GIF8']
                                is_valid_image = any(resp.content[:4].startswith(m) for m in VALID_MAGIC)
                                
                                if is_valid_image:
                                    content_file = ContentFile(resp.content, name=file_name)
                                else:
                                    logger.warning(f"[APPROVE] Downloaded content is not a valid image (magic bytes: {resp.content[:4]})")
                            else:
                                logger.warning(f"[APPROVE] Failed to download image after {len(header_variants)} attempts")
                        
                        # Case C: It's a local file relative path
                        elif image_path.startswith('/media/'):
                             from django.conf import settings
                             full_path = os.path.join(settings.BASE_DIR, image_path.lstrip('/'))
                             logger.info(f"[APPROVE] Reading relative image: {full_path}")
                             if os.path.exists(full_path):
                                 with open(full_path, 'rb') as f:
                                     content = f.read()
                                     content_file = ContentFile(content, name=file_name)
                             else:
                                 logger.warning(f"[APPROVE] Local file not found: {full_path}")
                        
                        # Case C.5: It's a relative path stored in the Django storage backend (e.g., Cloudinary)
                        elif not image_path.startswith('http') and not os.path.exists(image_path) and not image_path.startswith('/'):
                            from django.core.files.storage import default_storage
                            logger.info(f"[APPROVE] Attempting to download from default storage URL for: {image_path}")
                            try:
                                file_url = default_storage.url(image_path)
                                logger.info(f"[APPROVE] Storage URL: {file_url}")
                                
                                # Fix double https issues if Cloudinary is misconfigured
                                if file_url.count('https://') > 1:
                                    file_url = file_url[file_url.rfind('https://'):]
                                    
                                resp = img_requests.get(file_url, timeout=15)
                                
                                # Cloudinary sometimes adds v1/media/ to the URL which breaks for media not in the media/ folder
                                if resp.status_code == 404:
                                    logger.warning(f"[APPROVE] Storage URL {file_url} returned 404. Trying alternative paths...")
                                    alt_url_1 = file_url.replace('/v1/media/', '/')
                                    alt_url_2 = file_url.replace('/media/', '/')
                                    for alt_url in [alt_url_1, alt_url_2]:
                                        resp_alt = img_requests.get(alt_url, timeout=15)
                                        if resp_alt.status_code == 200:
                                            resp = resp_alt
                                            logger.info(f"[APPROVE] Success with alternative URL: {alt_url}")
                                            break

                                if resp.status_code == 200:
                                    content_file = ContentFile(resp.content, name=file_name)
                                else:
                                    logger.warning(f"[APPROVE] Download from storage failed with status {resp.status_code}")
                            except Exception as storage_err:
                                 logger.warning(f"[APPROVE] Error processing storage URL: {storage_err}")
                        
                        # Case D: It's a legacy absolute local path
                        elif os.path.exists(image_path):
                            logger.info(f"[APPROVE] Reading local image: {image_path}")
                            with open(image_path, 'rb') as f:
                                content = f.read()
                                content_file = ContentFile(content, name=file_name)
                        else:
                            logger.warning(f"[APPROVE] Image path not recognized/found: {image_path}")
                                
                        # Save to Article via .save() — works with any storage backend
                        if content_file:
                            logger.info(f"[APPROVE] Saving image {i+1} ({file_name}, {len(content_file)} bytes) to article...")
                            if i == 0:
                                article.image.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 1 saved. article.image.url = {article.image.url if article.image else 'NONE'}")
                            elif i == 1:
                                article.image_2.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 2 saved. article.image_2.url = {article.image_2.url if article.image_2 else 'NONE'}")
                            elif i == 2:
                                article.image_3.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 3 saved. article.image_3.url = {article.image_3.url if article.image_3 else 'NONE'}")
                        else:
                            logger.warning(f"[APPROVE] No content_file for image {i+1}")
                                
                    except Exception as img_err:
                        logger.error(f"[APPROVE] Error saving image {image_path}: {img_err}", exc_info=True)
            else:
                logger.warning(f"[APPROVE] No images found in pending article")
            
            # Restore Tags from PendingArticle
            if pending.tags and isinstance(pending.tags, list):
                try:
                    from django.utils.text import slugify
                    for tag_name in pending.tags:
                        tag_slug = slugify(tag_name)
                        tag, _ = Tag.objects.get_or_create(
                            slug=tag_slug, 
                            defaults={'name': tag_name}
                        )
                        article.tags.add(tag)
                    print(f"  Restored {len(pending.tags)} tags")
                except Exception as e:
                    print(f"  Error restoring tags: {e}")

            # --- Smart tag matching (same logic as translate-enhance) ---
            try:
                all_tags = list(Tag.objects.select_related('group').all())
                title_lower = article.title.lower()
                content_lower = (article.content or '').lower()
                combined_text = f"{title_lower} {content_lower}"
                seo_kw_list = [kw.strip() for kw in (article.meta_keywords or '').split(',') if kw.strip()]
                keywords_text = ' '.join(kw.lower() for kw in seo_kw_list)

                GENERIC_TAGS = {'technology', 'navigation', 'advanced', 'performance', 'budget', 'luxury'}
                existing_tag_names = list(article.tags.values_list('name', flat=True))

                for tag in all_tags:
                    tag_lower = tag.name.lower()
                    matched = False

                    if tag_lower.isdigit():
                        if any(kw.lower() == tag_lower for kw in seo_kw_list):
                            matched = True
                    elif any(kw.lower() == tag_lower for kw in seo_kw_list):
                        matched = True
                    elif len(tag_lower) >= 3 and tag_lower not in GENERIC_TAGS and tag_lower in keywords_text:
                        matched = True
                    elif len(tag_lower) >= 2 and (f' {tag_lower} ' in f' {title_lower} ' or title_lower.startswith(f'{tag_lower} ')):
                        matched = True
                    elif tag.group and tag.group.name in ('Manufacturers', 'Brands', 'Body Types', 'Fuel Types', 'Segments'):
                        if tag_lower not in GENERIC_TAGS and f' {tag_lower} ' in f' {combined_text} ':
                            matched = True
                    elif tag_lower in ('ev', 'electric') and ('electric' in combined_text or ' ev ' in f' {combined_text} ' or 'bev' in combined_text):
                        matched = True
                    elif tag_lower == 'phev' and 'phev' in combined_text:
                        matched = True
                    elif tag_lower == 'hybrid' and 'hybrid' in combined_text:
                        matched = True

                    if matched and tag.name not in existing_tag_names:
                        article.tags.add(tag)
                        existing_tag_names.append(tag.name)

                smart_tags = list(article.tags.values_list('name', flat=True))
                print(f"  🏷️ Smart tags: {', '.join(smart_tags)}")
            except Exception as tag_err:
                logger.warning(f"Smart tag matching failed: {tag_err}")

            # Restore Specs from PendingArticle
            if pending.specs and isinstance(pending.specs, dict):
                try:
                    specs = pending.specs
                    if specs.get('make') != 'Not specified':
                        CarSpecification.objects.update_or_create(
                            article=article,
                            defaults={
                                'model_name': f"{specs.get('make', '')} {specs.get('model', '')}",
                                'engine': specs.get('engine', ''),
                                'horsepower': str(specs.get('horsepower', '')),
                                'torque': specs.get('torque', ''),
                                'zero_to_sixty': specs.get('acceleration', ''),
                                'top_speed': specs.get('top_speed', ''),
                                'price': specs.get('price', ''),
                            }
                        )
                        print("  Restored CarSpecification")
                except Exception as e:
                    print(f"  Error restoring specs: {e}")
            
            # Update pending article
            pending.status = 'published'
            pending.published_article = article
            pending.reviewed_by = request.user
            pending.reviewed_at = timezone.now()
            pending.save()
            
            # Generate A/B title variants
            try:
                from ai_engine.main import generate_title_variants
                generate_title_variants(article, provider='gemini')
            except Exception as ab_err:
                logger.warning(f"A/B title variant generation failed: {ab_err}")
            
            # Deep specs enrichment — auto-fill VehicleSpecs card
            try:
                from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                # Build specs dict from CarSpecification if available
                specs_dict = None
                web_context = ''
                try:
                    car_spec = CarSpecification.objects.filter(article=article).first()
                    if car_spec:
                        # CarSpecification has no 'year' field — extract from title
                        import re as _re
                        _year = None
                        _y_match = _re.search(r'\b(20[2-3]\d)\b', article.title)
                        if _y_match:
                            _year = int(_y_match.group(1))
                        elif car_spec.release_date:
                            _ry = _re.search(r'(20[2-3]\d)', car_spec.release_date)
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
                except Exception:
                    pass
                
                # Web search for better spec accuracy
                if specs_dict and specs_dict.get('make'):
                    try:
                        from ai_engine.modules.searcher import get_web_context
                        web_context = get_web_context(specs_dict)
                    except Exception:
                        pass
                    generate_deep_vehicle_specs(article, specs=specs_dict, web_context=web_context, provider='gemini')
            except Exception as ds_err:
                logger.warning(f"Deep specs enrichment failed: {ds_err}")
            
            # Clear cache so the new article appears on homepage immediately
            try:
                invalidate_article_cache(article_id=article.id, slug=article.slug)
                logger.info(f"Cache invalidated after publishing article: {article.slug}")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate cache: {cache_err}")
            
            return Response({
                'message': 'Article approved successfully' if not is_published else 'Article published successfully',
                'article_id': article.id,
                'article_slug': article.slug
            })
        except Exception as e:
            logger.error(f"Failed to publish article: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        pending.status = 'rejected'
        pending.reviewed_by = request.user
        pending.reviewed_at = timezone.now()
        pending.review_notes = request.data.get('reason', '')
        pending.save()
        
        return Response({'message': 'Article rejected'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about pending articles"""
        # Get base queryset
        queryset = PendingArticle.objects.all()
        
        # Apply source filters
        only_rss = request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        only_youtube = request.query_params.get('only_youtube')
        exclude_rss = request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return Response({
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'published': queryset.filter(status='published').count(),
            'total': queryset.count()
        })
