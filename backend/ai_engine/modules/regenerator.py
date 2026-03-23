import logging
import re
from news.models import Article, Tag, CarSpecification, RSSNewsItem, PendingArticle as PendingArticleModel, AdminActionLog, ArticleTitleVariant
from ai_engine.modules.article_prompt_builder import expand_press_release, parse_ai_response
from ai_engine.modules.article_post_processor import post_process_article
from ai_engine.modules.utils import clean_title
from ai_engine.modules.publisher import extract_summary
from news.api_views._shared import invalidate_article_cache
from ai_engine.main import _generate_article_content, generate_title_variants

logger = logging.getLogger(__name__)

def fast_rewrite_article(title, content, specs, provider='gemini', instruction=None):
    from datetime import datetime
    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        from ai_engine.modules.prompt_sanitizer import wrap_untrusted
        from ai_engine.modules.searcher import get_web_context
    except ImportError:
        pass
        
    ai = get_ai_provider(provider)
    current_date = datetime.now().strftime("%B %d, %Y")
    
    spec_str = str(specs) if specs else "No strict specs provided. Keep existing numbers."
    
    try:
        web_context_str = get_web_context(specs) if specs else ""
    except Exception as e:
        logger.warning(f"Failed to fetch fast web context: {e}")
        web_context_str = ""
    
    prompt = f"""TODAY'S DATE: {current_date}

You are an expert automotive journalist at FreshMotors. You have an EXISTING article that needs a DEEP REWRITE.
The current draft is okay, but it needs better flow, a more engaging tone, and professional automotive journalism style.

EXISTING TITLE: {title}
EXISTING ARTICLE:
{wrap_untrusted(content, 'EXISTING_ARTICLE')}

VERIFIED VEHICLE SPECS (ABSOLUTE GROUND TRUTH):
{wrap_untrusted(spec_str, 'SPECS_TRIBUNAL')}

{f'''FRESH WEB RESEARCH (Use this to add deep technical substance, chemistry, features, real-world data instead of fluff!):
{wrap_untrusted(web_context_str, 'WEB_CONTEXT')}
''' if web_context_str else ''}

{f'''🚨 USER CUSTOM INSTRUCTIONS (HIGHEST PRIORITY) 🚨
{wrap_untrusted(instruction, 'USER_INSTRUCTION')}
(⚡ CRITICAL: You MUST strictly follow these instructions. If they tell you to change the car name, specs, or ANYTHING else, you MUST DO IT. These instructions OVERRIDE all other rules, including the Verified Specs below.)''' if instruction else ''}

INSTRUCTIONS:
1. REWRITE the article completely to make it flow beautifully. Keep the SAME OR LONGER length. DO NOT SUMMARIZE.
2. {'DO NOT change any numbers or facts from the Verified Specs UNLESS the User Custom Instructions tell you to. Otherwise, use them as your absolute ground truth.' if instruction else 'DO NOT change any numbers or facts from the Verified Specs. Use them as your absolute ground truth.'}
3. Improve the hook/intro paragraph.
4. Improve the FreshMotors Verdict to be punchy, specific and opinionated (minimum 60 words).
5. Every major section (Performance, Design, Technology, Driving Experience) MUST have at least 2 full paragraphs.

═══════════════════════════════════════════════
WORD COUNT & DEPTH RULE:
Your rewritten article MUST be at least the SAME LENGTH as the original, targeting 1000-1300 words. Do not artificially stretch or bloat the article. Use the FRESH WEB RESEARCH to weave highly technical engineering facts, battery details, and advanced features into your paragraphs. DO NOT just fluff with adjectives—add actual substance. 

BANNED TONE & CLICHÉS — DO NOT write like a clickbait blog or you will be penalized:
- "Forget everything you thought you knew" / "Hold on to your hats" / "Buckle up"
- "Consider the gauntlet THROWN" / "shake up the establishment" / "disrupting the market"
- "eye-watering" / "jaw-dropping" / "mind-blowing" / "game-changing"
- "this thing is set to make a serious splash" / "dropping a bombshell"
- Write with CONFIDENCE and AUTHORITY, not hype. Let the specs speak for themselves.

HTML PRESERVATION RULES:
- If there is a <div class="spec-bar">, <table class="specs-table">, or a <div class="pros-cons"> block, LEAVE ITS HTML EXACTLY AS-IS. 
- ═══ FRESHMOTORS VERDICT BLOCK ═══
  Your output MUST include the FreshMotors Verdict formatted EXACTLY like this HTML:
  <div class="fm-verdict">
    <div class="verdict-label">FreshMotors Verdict</div>
    <p>Your punchy, specific and opinionated verdict here. Minimum 60 words.</p>
  </div>
- CRITICAL: DO NOT extract those specs and write them as messy plain text lists underneath! PRESERVE the tags identically!
- WARNING: ABSOLUTELY NO PLAIN TEXT LISTS OF SPECS (e.g. "Horsepower: 351 PS"). All specs MUST either be woven naturally into your paragraph sentences OR left inside their original HTML tables.
- IF THE `EXISTING_ARTICLE` already contains ugly plain text lists of specifications (like redundant stats stacked together), YOU MUST DELETE THEM. Fix the article's mistakes!
- If there is a "How It Compares" section with a <div class="compare-grid">, check if the price difference between vehicles is extreme (>40%). If it is an absurd comparison (e.g. $20k vs $35k), DELETE the entire "How It Compares" section completely (both the text and the HTML grid). Otherwise, preserve the exact HTML of the cards.

OUTPUT FORMAT - You MUST return a valid JSON object (and NOTHING else) with these exact keys:
{{
  "self_reflection": "STEP 1: List all the fields/sections you are including (Introduction, Spec Bar, Performance, Design, Technology, Driving Experience, Pricing, Pros/Cons, Verdict). STEP 2: Verify that each section is filled with REAL facts (not fluff) from the source data.",
  "title": "[New Engaging, Descriptive Title]",
  "seo_description": "[160 chars seo meta]",
  "summary": "[300 chars summary for cards]",
  "final_html_article": "<p>Rewritten HTML article...</p>"
}}
"""

    system_prompt = "You are an expert automotive journalist rewriting an article. Keep all facts intact. ALWAYS OUTPUT VALID JSON ONLY."
    
    raw_response = ai.generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=16384,
        caller='fast_regenerate'
    )
    
    parsed = parse_ai_response(raw_response)
    if not parsed or 'final_html_article' not in parsed:
        return None
        
    enhanced = parsed.get("final_html_article", "")
    enhanced = post_process_article(enhanced)
    
    # Strictly ensure verdict is present and complete, using the rewritten HTML itself as context
    try:
        from ai_engine.modules.article_self_review import _ensure_verdict_written
        enhanced = _ensure_verdict_written(enhanced, enhanced, provider)
    except Exception as e:
        logger.error(f"Failed to ensure verdict for fast rewrite: {e}")
        
    # Strictly enforce DB maximums to prevent PostgreSQL "value too long" errors
    new_title = parsed.get('title', title)
    new_summary = parsed.get('summary', '')
    new_seo_desc = parsed.get('seo_description', '')
    
    if len(new_title) > 250:
        new_title = new_title[:247] + "..."
    if len(new_summary) > 400:
        new_summary = new_summary[:397] + "..."
    if len(new_seo_desc) > 158:
        new_seo_desc = new_seo_desc[:155] + "..."
    
    return {
        'title': new_title,
        'content': enhanced,
        'summary': new_summary,
        'seo_description': new_seo_desc,
        'word_count': len(re.sub(r'<[^>]+>', ' ', enhanced).split())
    }

# Trigger backend deploy to sync `fix(ai-engine)` logic
def regenerate_existing_article(article_id, provider='gemini', instruction=None, user_id=None, celery_task=None):
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
            # YouTube article -> FAST REWRITE (takes ~15 seconds instead of 5 minutes)
            source_type = 'youtube_rewrite'
            
            # Extract current specs to safely feed into the rewrite engine
            specs_dict = {}
            try:
                car_spec = CarSpecification.objects.get(article=article)
                specs_dict = {
                    'make': car_spec.make,
                    'model': car_spec.model,
                    'engine': car_spec.engine,
                    'horsepower': car_spec.horsepower,
                    'price': car_spec.price,
                    'torque': car_spec.torque,
                    'zero_to_sixty': car_spec.zero_to_sixty,
                    'drivetrain': car_spec.drivetrain
                }
            except CarSpecification.DoesNotExist:
                pass

            if celery_task:
                celery_task.update_state(state='PROGRESS', meta={'step': 'Running Deep Rewrite (~30-60s)', 'progress': 40})

            rewrite_result = fast_rewrite_article(article.title, article.content, specs_dict, provider=provider, instruction=instruction)
            if not rewrite_result:
                return {'success': False, 'message': 'AI fast rewrite failed or returned empty content.'}
                
            if celery_task:
                celery_task.update_state(state='PROGRESS', meta={'step': 'Saving rewritten content...', 'progress': 85})
                
            result = {
                'success': True,
                'title': rewrite_result['title'],
                'content': rewrite_result['content'],
                'summary': rewrite_result['summary'],
                'seo_description': rewrite_result['seo_description'],
                'generation_metadata': {
                    'provider': provider,
                    'source_type': source_type,
                    'source_url': youtube_url,
                    'word_count': rewrite_result['word_count'],
                },
                'specs': specs_dict, # Preserve specs EXACTLY as they were
                'tag_names': [t.name for t in article.tags.all()], # Preserve original tags initially
            }
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
                instruction=instruction,
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

        # --- Smart Tag Assignment ---
        tags_assigned = []
        try:
            from ai_engine.modules.smart_tagger import assign_tags
            # For RSS, AI might return empty tags so we look at the content
            # For YouTube, AI returns tag_names but smart_tagger will sanitize them vs DB
            tag_ids = assign_tags(article.title, article.content)
            if tag_ids:
                article.tags.set(tag_ids)
                tags_assigned = list(Tag.objects.filter(id__in=tag_ids).values_list('name', flat=True))
        except Exception as tag_err:
            logger.warning(f'Regenerate smart_tagger failed: {tag_err}')
            
        # Fallback to direct Tag creation if smart_tagger failed/returned none but we have raw tag_names
        if not tags_assigned and result.get('tag_names'):
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
