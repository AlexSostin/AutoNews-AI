"""
Article generation mixin — handles YouTube generation, translation/enhancement,
content reformatting, and article regeneration.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import os
import sys
import re
import logging

from news.api_views._shared import invalidate_article_cache, is_valid_youtube_url

logger = logging.getLogger(__name__)


class ArticleGenerationMixin:
    """Mixin for article generation actions on ArticleViewSet."""

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def generate_from_youtube(self, request):
        """Generate article from YouTube URL with WebSocket progress"""
        import uuid
        from news.models import Article
        
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
        import json
        from news.models import Article, Category, Tag, CarSpecification
        
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

                        # Skip year tags (e.g. "2025") from fuzzy matching
                        if tag_lower.isdigit():
                            if any(kw.strip().lower() == tag_lower for kw in seo_kw_list):
                                matched = True
                        # 1. Exact keyword match
                        elif any(kw.strip().lower() == tag_lower for kw in seo_kw_list):
                            matched = True
                        # 2. Keyword contains tag name
                        elif len(tag_lower) >= 3 and tag_lower not in GENERIC_TAGS and tag_lower in keywords_text:
                            matched = True
                        # 3. Tag name appears in title
                        elif len(tag_lower) >= 2 and (f' {tag_lower} ' in f' {title_lower} ' or title_lower.startswith(f'{tag_lower} ')):
                            matched = True
                        # 4. Brand/body/fuel tags — check content too
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

        system_prompt = """You are an HTML formatter. Your ONLY job is to wrap text in proper HTML tags.
You must NOT change, remove, shorten, or rewrite ANY text. Keep every single word exactly as-is.
Return ONLY the formatted HTML — no markdown, no code fences, no explanation."""

        format_prompt = f"""Take this article text and wrap it in proper HTML tags. 

⚠️ CRITICAL: Do NOT change the text content AT ALL. Every sentence, every word, every number 
must remain EXACTLY as in the original. You are ONLY adding/fixing HTML tags.

FORMATTING RULES:
- Wrap section titles in <h2> tags (or <h3> for sub-sections)
- Wrap paragraphs in <p> tags
- Wrap bullet-point lists in <ul><li> tags
- Use <strong> ONLY for: brand names (BMW, Tesla), model names (Model Y), and key specs (680 HP, $36,000)
- Do NOT bold years, generic terms, or adjectives
- Keep the article title as the first <h2>

DO NOT:
- Remove ANY sections, paragraphs, or sentences
- Shorten or summarize ANY text
- Change wording, rephrase, or "improve" anything
- Add new information or commentary
- Remove inline styles from existing tags if present
- Change the article language

PRESERVE:
- ALL text content word-for-word
- ALL sections including pricing, availability, market info
- ALL images (<img> tags) as-is
- The original article structure and order

TEXT TO FORMAT:
{content[:15000]}

Return ONLY the HTML-formatted version with every word preserved."""

        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result = provider.generate_completion(
                format_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=12000,
            )

            # Clean up potential markdown code fences
            cleaned = result.strip()
            cleaned = re.sub(r'^```(?:html)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
            
            # Post-processing: remove empty sections
            cleaned = re.sub(r'<h([23])>[^<]*</h\1>\s*(?=<h[23]>|$)', '', cleaned)
            cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            
            # Remove ALT_TEXT / SEO metadata that shouldn't be in visible content
            cleaned = re.sub(r'<div\s+class="alt-texts"[^>]*>.*?</div>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r'(?:^|\n)\s*ALT_TEXT_\d+:.*?(?:\n|$)', '\n', cleaned)
            cleaned = re.sub(r'<p>\s*(?:<strong>)?SEO Visual Assets:?(?:</strong>)?\s*</p>', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'(?:^|\n)\s*SEO Visual Assets:?\s*(?:\n|$)', '\n', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
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
        from news.models import Article, Tag, CarSpecification
        
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
                # YouTube article → try enhancement first, then full regeneration
                source_type = 'youtube'
                from ai_engine.main import _generate_article_content, generate_title_variants
                
                # Try enhancing existing content with web data first
                if article.content and len(article.content) > 500:
                    from ai_engine.modules.article_generator import enhance_existing_article
                    
                    # Build specs dict from existing CarSpecification
                    enhance_specs = {}
                    try:
                        car_spec = CarSpecification.objects.filter(article=article).first()
                        if car_spec:
                            enhance_specs = {
                                'make': car_spec.make or '',
                                'model': car_spec.model or '',
                                'year': car_spec.release_date or '',
                            }
                    except Exception:
                        pass
                    
                    # Fallback: extract from title
                    if not enhance_specs.get('make'):
                        import re as _title_re
                        title_parts = article.title.split()
                        if len(title_parts) >= 3:
                            # Try "2026 BYD TANG" pattern
                            if title_parts[0].isdigit() and len(title_parts[0]) == 4:
                                enhance_specs['year'] = title_parts[0]
                                enhance_specs['make'] = title_parts[1]
                                enhance_specs['model'] = ' '.join(title_parts[2:4])
                            else:
                                enhance_specs['make'] = title_parts[0]
                                enhance_specs['model'] = ' '.join(title_parts[1:3])
                    
                    print(f"🔄 Trying enhancement mode for: {enhance_specs.get('make')} {enhance_specs.get('model')}")
                    enhanced = enhance_existing_article(
                        existing_html=article.content,
                        specs=enhance_specs,
                        provider=provider,
                    )
                    
                    if enhanced and enhanced.get('content'):
                        result = {
                            'success': True,
                            'title': enhanced['title'] or article.title,
                            'content': enhanced['content'],
                            'summary': enhanced['summary'] or article.summary,
                            'generation_metadata': {
                                'provider': provider,
                                'source_type': 'youtube_enhanced',
                                'word_count': enhanced.get('word_count', 0),
                                'mode': 'enhancement',
                            },
                            'specs': {},
                            'tag_names': [],
                        }
                        source_type = 'youtube_enhanced'
                        print(f"✅ Enhancement succeeded ({enhanced.get('word_count', 0)} words)")
                    else:
                        print(f"⚠️ Enhancement failed, falling back to full regeneration")
                        enhanced = None
                
                # Full regeneration if enhancement didn't work
                if not result:
                    result = _generate_article_content(youtube_url, provider=provider, exclude_article_id=article.id)
                
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
                
                # Method 2: Try finding by author_channel_url
                if not rss_item and not source_url and article.author_channel_url:
                    rss_item = RSSNewsItem.objects.filter(
                        source_url=article.author_channel_url
                    ).first()
                    if not rss_item:
                        source_url = article.author_channel_url
                
                if rss_item:
                    press_release_text = rss_item.content or rss_item.excerpt or ''
                    source_url = rss_item.source_url or source_url
                    
                    if '<' in press_release_text:
                        press_release_text = _re.sub(r'<[^>]+>', ' ', press_release_text)
                        press_release_text = _re.sub(r'\s+', ' ', press_release_text).strip()
                elif source_url:
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
                
                expanded_content = expand_press_release(
                    press_release_text=press_release_text,
                    source_url=source_url,
                    provider=provider,
                    source_title=article.title,
                )
                
                if not expanded_content or len(expanded_content) < 200:
                    return Response({
                        'success': False,
                        'message': 'AI returned empty or too short content',
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                title_match = _re.search(r'<h2[^>]*>(.*?)</h2>', expanded_content)
                ai_title = clean_title(title_match.group(1)) if title_match else article.title
                
                summary_match = _re.search(r'<p>(.*?)</p>', expanded_content)
                ai_summary = ''
                if summary_match:
                    ai_summary = _re.sub(r'<[^>]+>', '', summary_match.group(1))[:300]
                
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
            
            if result.get('meta_keywords'):
                article.meta_keywords = result['meta_keywords']
            
            if result.get('author_name'):
                article.author_name = result['author_name']
            if result.get('author_channel_url'):
                article.author_channel_url = result['author_channel_url']
            
            specs = result.get('specs') or {}
            if specs.get('price'):
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
