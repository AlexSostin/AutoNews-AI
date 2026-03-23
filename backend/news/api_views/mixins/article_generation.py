"""
Article generation mixin — handles YouTube generation, translation/enhancement,
content reformatting, and article regeneration.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import os
import sys
import re
import logging

from news.api_views._shared import invalidate_article_cache, is_valid_youtube_url

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.prompt_sanitizer import sanitize_for_prompt, wrap_untrusted
except ImportError:
    # Fallback — no sanitization if module not found (shouldn't happen)
    sanitize_for_prompt = lambda text, max_length=15000: text[:max_length]
    wrap_untrusted = lambda text, label='DATA', max_length=15000: text[:max_length]


class ArticleGenerationMixin:
    """Mixin for article generation actions on ArticleViewSet."""

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def generate_from_youtube(self, request):
        """
        Start async article generation from a YouTube URL.
        Returns task_id immediately; poll generate_status for progress.

        POST /api/v1/articles/generate_from_youtube/
        Body: { youtube_url, provider? }
        Response: { success, task_id }
        """
        youtube_url = request.data.get('youtube_url')

        if not youtube_url:
            return Response(
                {'error': 'youtube_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not is_valid_youtube_url(youtube_url):
            return Response(
                {'error': 'Invalid YouTube URL format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        provider = request.data.get('provider', 'gemini')
        if provider != 'gemini':
            provider = 'gemini'

        try:
            from news.tasks import generate_from_youtube_task
            task = generate_from_youtube_task.delay(
                youtube_url=youtube_url,
                provider=provider,
                user_id=request.user.id if request.user else None,
            )
            return Response({
                'success': True,
                'message': 'Generation task started.',
                'task_id': task.id,
            })
        except Exception as e:
            import traceback
            logger.error(f'generate_from_youtube task dispatch failed: {e}\n{traceback.format_exc()}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser],
            url_path='generate_status')
    def generate_status(self, request):
        """
        Poll the status of an async generate_from_youtube task.
        GET /api/v1/articles/generate_status/?task_id=...
        Returns: { status: pending|running|done|error, article_id?, article?, error?, timeout? }
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        from celery.result import AsyncResult
        task = AsyncResult(task_id)

        if task.state == 'PENDING':
            return Response({'status': 'pending'})
        elif task.state == 'PROGRESS':
            # Real progress data from update_state() in the AI pipeline
            info = task.info or {}
            return Response({
                'status': 'running',
                'step': info.get('step'),
                'progress': info.get('progress', 0),
                'message': info.get('message', ''),
            })
        elif task.state == 'STARTED':
            return Response({'status': 'running'})
        elif task.state == 'SUCCESS':
            result = task.result
            if isinstance(result, dict) and not result.get('success'):
                return Response({
                    'status': 'error',
                    'error': result.get('message', 'Generation failed.'),
                    'timeout': result.get('timeout', False),
                })
            # Fetch created article
            article_id = result.get('article_id') if isinstance(result, dict) else None
            article_data = None
            if article_id:
                from news.models import Article
                article = Article.objects.filter(id=article_id).first()
                if article:
                    serializer = self.get_serializer(article)
                    article_data = serializer.data
                    # Invalidate homepage cache now that article exists
                    invalidate_article_cache(article_id=article_id)
            return Response({
                'status': 'done',
                'article_id': article_id,
                'article': article_data,
            })
        elif task.state == 'FAILURE':
            return Response({
                'status': 'error',
                'error': str(task.info),
            })
        else:
            return Response({'status': task.state.lower()})

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser], url_path='translate-enhance')
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
        if provider != 'gemini':
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

                # --- Smart Tag Assignment ---
                tags_assigned = []
                try:
                    from ai_engine.modules.smart_tagger import assign_tags
                    tag_ids = assign_tags(result.get('title', ''), result.get('content', ''))
                    if tag_ids:
                        article.tags.set(tag_ids)
                        from news.models import Tag
                        tags_assigned = list(Tag.objects.filter(id__in=tag_ids).values_list('name', flat=True))
                except Exception as tag_err:
                    logger.warning(f'Smart tag assignment failed: {tag_err}')

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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser],
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

        # ── Smart skip: if HTML is already well-structured, don't send to AI ──
        has_h2 = bool(re.search(r'<h2[^>]*>', content))
        has_paragraphs = content.count('<p>') >= 3
        has_lists = bool(re.search(r'<ul[^>]*>', content))
        html_tag_count = len(re.findall(r'<[a-z][^>]*>', content, re.I))

        if has_h2 and has_paragraphs and html_tag_count > 10:
            # Already well-formatted — just clean up whitespace and empty tags
            cleaned = content
            cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            cleaned = cleaned.strip()

            if cleaned == content.strip():
                return Response({
                    'success': True,
                    'content': cleaned,
                    'original_length': len(content),
                    'new_length': len(cleaned),
                    'skipped': True,
                    'message': 'Content already well-formatted, no AI changes needed.',
                })

        system_prompt = """You are an HTML article formatter for an automotive news website.
Your job is to IMPROVE the HTML structure of an article while preserving EVERY SINGLE WORD of content.
Return ONLY the formatted HTML — no markdown, no code fences, no explanation."""

        format_prompt = f"""Reformat this automotive article's HTML structure. 

⚠️ ABSOLUTE RULES — VIOLATION = FAILURE:
1. PRESERVE every single word, sentence, paragraph, and section. Do NOT remove, shorten, or rewrite ANY text.
2. The output must contain ALL sections from the original — from the title to the very last paragraph.
3. If HTML tags already exist, KEEP them — only fix or improve tag choices where needed.

FORMATTING GUIDELINES:
- Use <h2> for main section titles, <h3> for sub-sections
- Wrap text paragraphs in <p> tags
- Wrap bullet-point lists in <ul><li> tags, numbered lists in <ol><li> tags
- Use <strong> ONLY for: brand names, model names, and key numeric specs (HP, km, price)
- Do NOT bold years, generic adjectives, or common words
- Keep all <img> tags exactly as-is
- Remove any stray markdown formatting (**, ##, etc.) and replace with proper HTML

INPUT HTML:
{sanitize_for_prompt(content, max_length=20000)}

OUTPUT: Return the COMPLETE reformatted HTML with every word preserved. Do NOT truncate."""

        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result = provider.generate_completion(
                format_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=16000,
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

            # ── Safety: Validate AI output ──
            if not cleaned or len(cleaned) < 50:
                return Response({
                    'success': False,
                    'message': 'AI returned empty or too short content',
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Check that output isn't drastically shorter than input (truncation detection)
            input_text_len = len(re.sub(r'<[^>]+>', '', content))  # text-only length
            output_text_len = len(re.sub(r'<[^>]+>', '', cleaned))
            
            if output_text_len < input_text_len * 0.6:
                logger.warning(
                    f'Reformat truncation detected: input text={input_text_len}, '
                    f'output text={output_text_len} ({output_text_len/input_text_len*100:.0f}%). '
                    f'Rejecting AI result, returning original.'
                )
                return Response({
                    'success': False,
                    'message': f'AI truncated the content ({output_text_len/input_text_len*100:.0f}% of original). '
                               f'Original preserved. Try again or edit manually.',
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Check that output contains HTML tags (not plain text)
            if not re.search(r'<(h[1-6]|p|ul|ol|li|strong|em|div)\b', cleaned):
                logger.warning('Reformat returned plain text without HTML tags, rejecting.')
                return Response({
                    'success': False,
                    'message': 'AI returned plain text without HTML formatting. Try again.',
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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser],
            url_path='regenerate-seo')
    def regenerate_seo(self, request, slug=None):
        """
        Regenerate SEO fields (title, summary, seo_description) based on the current body text.
        """
        import json
        article = self.get_object()
        content = request.data.get('content', article.content)
        
        if not content or len(content) < 100:
            return Response({'success': False, 'message': 'Content too short to generate SEO'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            from ai_engine.modules.title_seo_generator import _generate_title_and_seo
            
            specs_dict = {}
            if hasattr(article, 'carspecification') and article.carspecification:
                cs = article.carspecification
                specs_dict = {
                    'make': cs.make,
                    'model': cs.model,
                    'year': cs.release_date,
                    'horsepower': cs.horsepower,
                    'price': cs.price,
                }
                
            ai_result = _generate_title_and_seo(content, specs_dict)
            
            if not ai_result:
                return Response({'success': False, 'message': 'AI failed to generate SEO metadata.'}, status=500)
                
            updated_fields = []
            if ai_result.get('title'):
                article.title = ai_result['title']
                updated_fields.append('title')
            if ai_result.get('summary'):
                article.summary = ai_result['summary']
                updated_fields.append('summary')
            if ai_result.get('seo_description'):
                article.seo_description = ai_result['seo_description']
                updated_fields.append('seo_description')
                
            if updated_fields:
                article.save(update_fields=updated_fields + ['updated_at'])
                try:
                    invalidate_article_cache(article_id=article.id, slug=article.slug)
                except Exception:
                    pass
            
            try:
                from news.models import AdminActionLog
                AdminActionLog.log(article, request.user, 'edit_save', details={'note': 'Regenerated SEO with AI', 'fields': updated_fields})
            except Exception:
                pass
                
            return Response({
                'success': True,
                'title': article.title,
                'summary': article.summary,
                'seo_description': article.seo_description,
                'message': 'SEO and Summary successfully regenerated!'
            })
            
        except Exception as e:
            logger.error(f'Regenerate SEO failed: {e}')
            return Response({
                'success': False,
                'message': f'Failed to generate SEO: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser],
            url_path='auto-fill-metadata')
    def auto_fill_metadata(self, request):
        """
        Extract metadata from article HTML content.
        
        Hybrid approach:
        - Tags & Categories: ML model (local TF-IDF, free, instant)
        - Title, Summary, SEO: Gemini AI (needs LLM for creative generation)
        """
        import json
        from django.utils.text import slugify
        from news.models import Category, Tag
        
        content = request.data.get('content', '').strip()
        
        if not content or len(content) < 100:
            return Response({
                'success': False,
                'message': 'Content too short. Paste or write at least a few paragraphs.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Strip HTML to get plain text
        plain_text = re.sub(r'<[^>]+>', ' ', content)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        
        # ── ML predictions for tags & categories (free, instant) ──
        ml_tag_ids = []
        ml_cat_ids = []
        prediction_source = 'gemini'
        
        try:
            from ai_engine.modules.content_recommender import predict_tags, predict_categories, is_available
            if is_available():
                ml_tags = predict_tags('', content, plain_text[:500], top_n=8)
                ml_cats = predict_categories('', content, plain_text[:500], top_n=2)
                if ml_tags:
                    ml_tag_ids = [t['id'] for t in ml_tags]
                    prediction_source = 'ml'
                    logger.info(f"ML predicted {len(ml_tag_ids)} tags: {[t['name'] for t in ml_tags]}")
                if ml_cats:
                    ml_cat_ids = [c['id'] for c in ml_cats]
                    logger.info(f"ML predicted {len(ml_cat_ids)} categories: {[c['name'] for c in ml_cats]}")
        except Exception as ml_err:
            logger.warning(f'ML prediction failed, falling back to Gemini: {ml_err}')
        
        # ── Gemini for title/summary/SEO (needs LLM) ──
        system_prompt = "You are a metadata extractor. Return ONLY valid JSON, nothing else."
        
        if ml_tag_ids:
            # ML handled tags/cats — simpler prompt (fewer tokens)
            extract_prompt = f"""Extract metadata from this automotive article.

ARTICLE (first 3000 chars):
{plain_text[:3000]}

Return JSON:
{{"title":"SEO title with brand/model/year","summary":"2-3 sentences","seo_description":"max 155 chars","detected_brand":"Brand","detected_model":"Model"}}"""
        else:
            available_categories = list(Category.objects.values_list('name', flat=True))
            available_tags = list(Tag.objects.values_list('name', flat=True)[:50])
            extract_prompt = f"""Extract metadata from this automotive article.

CATEGORIES (pick 1-2): {json.dumps(available_categories)}
TAGS (pick up to 6): {json.dumps(available_tags)}

ARTICLE (first 3000 chars):
{plain_text[:3000]}

Return JSON:
{{"title":"SEO title with brand/model/year","summary":"2-3 sentences","seo_description":"max 155 chars","suggested_categories":["Cat"],"suggested_tags":["Tag1","Tag2"],"detected_brand":"Brand","detected_model":"Model"}}"""
        
        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result_text = provider.generate_completion(
                extract_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=2000,
            )
            
            cleaned = result_text.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
            
            try:
                metadata = json.loads(cleaned)
            except json.JSONDecodeError:
                cleaned = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"]*$', '', cleaned)
                open_braces = cleaned.count('{') - cleaned.count('}')
                open_brackets = cleaned.count('[') - cleaned.count(']')
                if not cleaned.endswith('"') and '"' in cleaned:
                    if cleaned.count('"') % 2 != 0:
                        cleaned += '"'
                cleaned += ']' * max(0, open_brackets)
                cleaned += '}' * max(0, open_braces)
                metadata = json.loads(cleaned)
            
            title = metadata.get('title', '')
            slug = slugify(title)[:80] if title else ''
            
            # Use ML predictions if available, otherwise Gemini's
            if ml_tag_ids:
                matched_tag_ids = ml_tag_ids
            else:
                matched_tag_ids = []
                for tag_name in metadata.get('suggested_tags', []):
                    tag = Tag.objects.filter(name__iexact=tag_name).first()
                    if tag:
                        matched_tag_ids.append(tag.id)
            
            if ml_cat_ids:
                matched_category_ids = ml_cat_ids
            else:
                matched_category_ids = []
                for cat_name in metadata.get('suggested_categories', []):
                    cat = Category.objects.filter(name__iexact=cat_name).first()
                    if cat:
                        matched_category_ids.append(cat.id)
            
            return Response({
                'success': True,
                'title': title,
                'slug': slug,
                'summary': metadata.get('summary', ''),
                'seo_description': metadata.get('seo_description', '')[:160],
                'category_ids': matched_category_ids,
                'tag_ids': matched_tag_ids,
                'detected_brand': metadata.get('detected_brand', ''),
                'detected_model': metadata.get('detected_model', ''),
                'prediction_source': prediction_source,
            })

        except json.JSONDecodeError as e:
            logger.error(f'Auto-fill metadata JSON parse failed: {e}\nRaw: {result_text[:500]}')
            return Response({
                'success': False,
                'message': 'AI returned invalid format. Please try again.',
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.error(f'Auto-fill metadata failed: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser],
            url_path='regenerate')
    def regenerate(self, request, slug=None):
        """
        Regenerate article content using AI.
        Now async via Celery to avoid proxy timeouts.
        
        POST /api/v1/articles/{slug}/regenerate/
        Body: { "provider": "gemini" }
        """
        # Fetch article manually to return a proper JSON response instead of a raw 404 (which causes CORS errors in Nginx)
        slug_or_id = self.kwargs.get(self.lookup_field) or slug
        try:
            from news.models import Article
            if str(slug_or_id).isdigit():
                article = Article.objects.get(pk=int(slug_or_id))
            else:
                article = Article.objects.get(slug=slug_or_id)
                
            if article.is_deleted:
                return Response({
                    'success': False,
                    'message': 'This article has been deleted and cannot be regenerated.',
                }, status=status.HTTP_400_BAD_REQUEST)
        except Article.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Article not found.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        provider = request.data.get('provider', 'gemini')
        if provider != 'gemini':
            provider = 'gemini'
        
        instruction = request.data.get('instruction', '').strip()

        
        try:
            from news.tasks import regenerate_article_task
            task = regenerate_article_task.delay(
                article_id=article.id,
                slug=article.slug,
                provider=provider,
                instruction=instruction,
                user_id=request.user.id if request.user else None
            )
            
            return Response({
                'success': True,
                'message': 'Regeneration task started successfully.',
                'task_id': task.id
            })
            
        except Exception as e:
            import traceback
            logger.error(f'Regenerate task dispatch failed: {e}\n{traceback.format_exc()}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser],
            url_path='regenerate_status')
    def regenerate_status(self, request):
        """
        Check the status of an async article regeneration task.
        GET /api/v1/articles/regenerate_status/?task_id=...
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        from celery.result import AsyncResult
        task = AsyncResult(task_id)

        if task.state == 'PENDING':
            return Response({'status': 'pending'})
        elif task.state == 'PROGRESS':
            info = task.info or {}
            return Response({
                'status': 'running',
                'step': info.get('step'),
                'progress': info.get('progress', 0),
                'message': info.get('message', ''),
            })
        elif task.state == 'STARTED':
            return Response({'status': 'running'})
        elif task.state == 'SUCCESS':
            result = task.result
            if isinstance(result, dict) and not result.get('success'):
                return Response({
                    'status': 'error',
                    'error': result.get('message', 'Generation failed silently.')
                })
            
            # Fetch updated article if successful
            article_id = result.get('article_id') if isinstance(result, dict) else None
            article_data = None
            if article_id:
                from news.models import Article
                article = Article.objects.filter(id=article_id).first()
                if article:
                    serializer = self.get_serializer(article)
                    article_data = serializer.data
                    
            return Response({
                'status': 'done',
                'result': result,
                'article': article_data
            })
        elif task.state == 'FAILURE':
            return Response({
                'status': 'error',
                'error': str(task.info)
            })
        else:
            return Response({'status': task.state.lower()})
