import logging
import re
from news.models import Article, Tag, CarSpecification, RSSNewsItem, PendingArticle as PendingArticleModel, AdminActionLog, ArticleTitleVariant
from ai_engine.modules.article_prompt_builder import expand_press_release
from ai_engine.modules.utils import clean_title
from ai_engine.modules.publisher import extract_summary
from news.api_views._shared import invalidate_article_cache
from ai_engine.main import _generate_article_content, generate_title_variants

logger = logging.getLogger(__name__)

def regenerate_existing_article(article_id, provider='gemini', user_id=None, celery_task=None):
    """
    Core logic for regenerating an existing article (YouTube or RSS).
    Used by the Celery task to run async and avoid proxy timeouts.
    """
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return {'success': False, 'message': 'Article not found.'}
        
    try:
        user = None
        if user_id:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.filter(id=user_id).first()
            
        youtube_url = article.youtube_url
        source_type = None
        result = None
        
        # ── AUTO-DETECT SOURCE TYPE ──
        if youtube_url:
            # YouTube article -> full regeneration
            source_type = 'youtube'
            result = _generate_article_content(youtube_url, provider=provider, exclude_article_id=article.id, celery_task=celery_task)
            
            if not result.get('success'):
                return {'success': False, 'message': f"AI generation failed: {result.get('error', 'Unknown error')}"}
        else:
            # RSS article -> find source RSSNewsItem and re-expand press release
            source_type = 'rss'
            
            rss_item = None
            source_url = ''
            press_release_text = ''
            
            pending = PendingArticleModel.objects.filter(published_article=article).first()
            if pending:
                rss_item = RSSNewsItem.objects.filter(pending_article=pending).first()
                if not rss_item and pending.source_url:
                    source_url = pending.source_url
            
            if not rss_item and not source_url and article.author_channel_url:
                rss_item = RSSNewsItem.objects.filter(source_url=article.author_channel_url).first()
                if not rss_item:
                    source_url = article.author_channel_url
            
            if rss_item:
                press_release_text = rss_item.content or rss_item.excerpt or ''
                source_url = rss_item.source_url or source_url
                
                if '<' in press_release_text:
                    press_release_text = re.sub(r'<[^>]+>', ' ', press_release_text)
                    press_release_text = re.sub(r'\s+', ' ', press_release_text).strip()
            elif source_url:
                try:
                    from ai_engine.modules.searcher import _search_ddgs
                    raw_results = _search_ddgs(article.title, max_results=3)
                    web_results = " ".join([r.get('desc', '') for r in raw_results]) if raw_results else ""
                    press_release_text = web_results if web_results else article.title
                except Exception:
                    press_release_text = article.title
            
            if not press_release_text or len(press_release_text.strip()) < 50:
                return {
                    'success': False,
                    'message': 'Cannot regenerate: no source content found for RSS item.'
                }

            if not source_url:
                source_url = article.author_channel_url or 'N/A'
            
            expanded_content = expand_press_release(
                press_release_text=press_release_text,
                source_url=source_url,
                provider=provider,
                source_title=article.title,
            )
            
            if not expanded_content or len(expanded_content) < 200:
                return {'success': False, 'message': 'AI returned empty or too short content'}
            
            ai_title = article.title
            ai_seo_desc = article.seo_description
            ai_summary = article.summary
            
            try:
                from ai_engine.modules.content_generator import _generate_title_and_seo
                ai_result = _generate_title_and_seo(expanded_content, {})
                if ai_result:
                    ai_title = ai_result.get('title') or ai_title
                    ai_seo_desc = ai_result.get('seo_description') or ai_seo_desc
                    ai_summary = ai_result.get('summary') or ai_summary
            except Exception as e:
                logger.error(f"[REGENERATE RSS] Metadata extraction failed: {e}")
                
            # Absolute fallback
            if not ai_summary:
                try:
                    ai_summary = extract_summary(expanded_content)
                except Exception:
                    summary_match = re.search(r'<p>(.*?)</p>', expanded_content)
                    ai_summary = re.sub(r'<[^>]+>', '', summary_match.group(1)) if summary_match else ''
            
            if ai_title == article.title:
                title_match = re.search(r'<h2[^>]*>(.*?)</h2>', expanded_content)
                if title_match:
                    ai_title = clean_title(title_match.group(1))
            
            word_count = len(re.sub(r'<[^>]+>', ' ', expanded_content).split())
            result = {
                'success': True,
                'title': ai_title,
                'content': expanded_content,
                'summary': ai_summary,
                'seo_description': ai_seo_desc,
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
        
        # ── SHARED POST-PROCESSING ──
        article.content_original = article.content
        article.title = result['title']
        article.content = result['content']
        if result.get('summary'):
            article.summary = result['summary']
        if result.get('seo_description'):
            article.seo_description = result['seo_description']
            
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

        try:
            gen_meta = result.get('generation_metadata') or {}
            comp_data = gen_meta.get('competitor_data', [])
            comp_subject_make = (result.get('specs') or {}).get('make', '')
            comp_subject_model = (result.get('specs') or {}).get('model', '')
            if comp_data and comp_subject_make and comp_subject_model:
                from ai_engine.modules.competitor_lookup import log_competitor_pairs
                log_competitor_pairs(
                    article_id=article.id,
                    subject_make=comp_subject_make,
                    subject_model=comp_subject_model,
                    competitors=comp_data,
                    selection_method='rule_based',
                )
        except Exception as _cle:
            logger.warning(f"Competitor pair logging failed (non-fatal): {_cle}")

        if result.get('tag_names'):
            new_tags = []
            for tag_name in result['tag_names']:
                tag, _ = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': tag_name.lower().replace(' ', '-')}
                )
                new_tags.append(tag)
            article.tags.set(new_tags)
        
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
        
        try:
            ArticleTitleVariant.objects.filter(article=article).delete()
            generate_title_variants(article, provider=provider)
        except Exception as ab_err:
            logger.warning(f'A/B title regeneration failed: {ab_err}')
        
        invalidate_article_cache(article_id=article.id, slug=article.slug)
        
        try:
            if user:
                AdminActionLog.log(article, user, 'regenerate', details={
                    'provider': provider,
                    'source_type': source_type,
                    'word_count': result.get('generation_metadata', {}).get('word_count'),
                })
        except Exception:
            pass
            
        from ai_engine.modules.image_placeholders import replace_inline_images_in_article
        replace_inline_images_in_article(article)
        
        return {
            'success': True,
            'message': f'Article regenerated ({source_type}) with {provider}',
            'article_id': article.id,
            'title': article.title,
            'slug': article.slug,
            'generation_metadata': result.get('generation_metadata'),
        }
        
    except Exception as e:
        import traceback
        logger.error(f'Regenerate failed: {e}\n{traceback.format_exc()}')
        try:
            if user:
                AdminActionLog.log(article, user, 'regenerate', success=False, details={'error': str(e)[:200]})
        except Exception:
            pass
        return {
            'success': False,
            'message': str(e),
        }
