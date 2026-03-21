"""
Article content generation pipeline.

Takes a YouTube URL, fetches transcript, analyzes it, generates an article,
extracts specs, enriches with web data, runs AI editor, and injects SEO links.

This is the core generation engine used by both the direct-publish and
pending-article workflows.

Helper functions have been extracted into focused modules:
  - generation_progress  → _send_progress
  - title_seo_generator  → _generate_title_and_seo, _truncate_summary
  - specs_validator       → _validate_specs, _get_internal_specs_context, _get_competitor_context_safe
  - tag_detector          → _auto_add_drivetrain_tag, _auto_add_tech_tags, _inject_tech_highlights
  - image_placeholders    → _inject_inline_image_placeholders
"""
import os
import sys
import re
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ── Import helpers from dedicated modules ──────────────────────────────────
from ai_engine.modules.generation_progress import _send_progress
from ai_engine.modules.title_seo_generator import _generate_title_and_seo, _truncate_summary
from ai_engine.modules.specs_validator import (
    _validate_specs,
    _get_internal_specs_context,
    _get_competitor_context_safe,
)
from ai_engine.modules.tag_detector import (
    _auto_add_drivetrain_tag,
    _auto_add_tech_tags,
    _inject_tech_highlights,
    _TECH_TAG_RULES,
    _TECH_DESCRIPTIONS,
)
from ai_engine.modules.image_placeholders import _inject_inline_image_placeholders

# Re-export everything so existing `from ai_engine.modules.content_generator import X`
# and `@patch('ai_engine.modules.content_generator.X')` continue to work.
__all__ = [
    '_send_progress',
    '_truncate_summary',
    '_generate_title_and_seo',
    '_validate_specs',
    '_get_internal_specs_context',
    '_get_competitor_context_safe',
    '_auto_add_drivetrain_tag',
    '_auto_add_tech_tags',
    '_inject_tech_highlights',
    '_inject_inline_image_placeholders',
    '_generate_article_content',
    '_TECH_TAG_RULES',
    '_TECH_DESCRIPTIONS',
]


def _generate_article_content(youtube_url, task_id=None, provider='gemini', video_title=None, exclude_article_id=None, celery_task=None, cache_task_id=None):
    """
    Internal function to generate article content without saving to DB.
    Returns dictionary with all article data.

    Args:
        celery_task: Bound Celery task instance (self) — enables real-time progress via update_state().
        cache_task_id: UUID string — enables progress via Django cache for thread-based flows.
    """
    # Import modules (with fallback for different run contexts)
    try:
        from ai_engine.modules.transcriber import transcribe_from_youtube
        from ai_engine.modules.analyzer import analyze_transcript
        from ai_engine.modules.article_generator import generate_article
        from ai_engine.modules.downloader import extract_video_screenshots
        from ai_engine.modules.title_utils import extract_title, validate_title, _is_generic_header
        from ai_engine.modules.duplicate_checker import check_car_duplicate
        from ai_engine.modules.utils import clean_video_title
    except ImportError:
        from modules.transcriber import transcribe_from_youtube
        from modules.analyzer import analyze_transcript
        from modules.article_generator import generate_article
        from modules.downloader import extract_video_screenshots
        from modules.title_utils import extract_title, validate_title, _is_generic_header
        from modules.duplicate_checker import check_car_duplicate
        from modules.utils import clean_video_title

    def send_progress(step, progress, message):
        _send_progress(task_id, step, progress, message, celery_task=celery_task, cache_task_id=cache_task_id)


    try:
        import time as _time
        _t_start = _time.time()
        _timings = {}

        # Fallback tracker — every degraded step is recorded here
        try:
            from ai_engine.modules.generation_errors import FallbackTracker, GenerationError, is_token_limit_error
        except ImportError:
            from modules.generation_errors import FallbackTracker, GenerationError, is_token_limit_error
        _tracker = FallbackTracker()

        
        provider_name = "Groq" if provider == 'groq' else "Google Gemini"
        send_progress(1, 5, f"🚀 Starting generation with {provider_name}...")
        print(f"🚀 Starting generation from: {youtube_url} using {provider_name}")
        
        # 0. Fetch video metadata (title, channel info)
        author_name = ''
        author_channel_url = ''
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={youtube_url}&format=json"
            resp = requests.get(oembed_url, timeout=5)
            if resp.status_code == 200:
                oembed_data = resp.json()
                if not video_title:
                    video_title = oembed_data.get('title')
                    print(f"🎥 Fetched Video Title: {video_title}")
                author_name = oembed_data.get('author_name', '')
                author_channel_url = oembed_data.get('author_url', '')
                print(f"👤 Channel: {author_name} ({author_channel_url})")
        except Exception as e:
            print(f"⚠️ Could not fetch video metadata: {e}")

        # 0.5. Clean video title — strip YouTube noise ("walk around", "first look", etc.)
        if video_title:
            video_title = clean_video_title(video_title)

        # 1. Fetch transcript
        _t_step = _time.time()
        send_progress(2, 20, "📝 Fetching subtitles from YouTube...")
        print("📝 Fetching transcript...")
        transcript = transcribe_from_youtube(youtube_url)
        _timings['transcript'] = round(_time.time() - _t_step, 1)
        
        if not transcript or len(transcript) < 5 or transcript.startswith("ERROR:"):
            error_msg = transcript if transcript and transcript.startswith("ERROR:") else "Failed to retrieve transcript or it is too short"
            send_progress(2, 100, f"❌ {error_msg}")
            _tracker.add('transcript', error_msg, critical=True)
            if _tracker.needs_token_retry:
                return {**GenerationError.token_limit('transcript', error_msg).to_result_dict(),
                        'title': '', 'content': ''}
            raise GenerationError.from_tracker(_tracker, step='transcript')
        
        send_progress(2, 30, f"✓ Transcript received ({len(transcript)} chars)")
        
        # 1.5 Video fact extraction via Gemini vision
        video_facts = {}
        try:
            from ai_engine.modules.video_fact_extractor import (
                extract_facts_from_video,
                format_video_facts_for_prompt,
            )
            send_progress(2, 32, "🎬 Extracting facts from video visuals...")
            video_facts = extract_facts_from_video(youtube_url)
            _timings['video_facts'] = True
        except Exception as e:
            _tracker.add('video_facts', str(e), critical=False)  # non-critical
        
        # 2. Analyze transcript
        _t_step = _time.time()
        send_progress(3, 40, f"🔍 Analyzing transcript with {provider_name} AI...")
        print("🔍 Analyzing transcript...")
        analysis = analyze_transcript(transcript, video_title=video_title, provider=provider)
        
        if not analysis:
            _tracker.add('analysis', 'analyze_transcript returned empty', critical=True)
            if _tracker.needs_token_retry:
                return {**GenerationError.from_tracker(_tracker, 'analysis').to_result_dict(),
                        'title': '', 'content': ''}
            send_progress(3, 100, "❌ Analysis failed")
            raise GenerationError.from_tracker(_tracker, step='analysis')
        
        _timings['analysis'] = round(_time.time() - _t_step, 1)
        send_progress(3, 50, "✓ Analysis complete")
        
        # 2.4 Merge video facts into analysis (enriches prompt with visual data)
        if video_facts:
            try:
                video_facts_text = format_video_facts_for_prompt(video_facts)
                if video_facts_text:
                    analysis += video_facts_text
                    print(f"✅ Video facts merged into analysis")
            except Exception as e:
                print(f"⚠️ Video facts merge failed (non-fatal): {e}")
        
        send_progress(4, 55, "🏷️ Categorizing...")
        try:
            from ai_engine.modules.analyzer import categorize_article, extract_specs_dict
        except ImportError:
            from modules.analyzer import categorize_article, extract_specs_dict
        
        category_name, tag_names = categorize_article(analysis)
        
        # 2.6. Extract Specs
        specs = extract_specs_dict(analysis)
        send_progress(4, 60, f"✓ {specs['make']} {specs['model']}")
        
        # 2.6.1 AUTO-ADD YEAR TAG if not already present
        year = specs.get('year')
        if year:
            year_str = str(year)
            # Check if any year tag is already present
            has_year_tag = any(t.isdigit() and len(t) == 4 for t in tag_names)
            if not has_year_tag:
                tag_names.append(year_str)
                print(f"🏷️ Auto-added year tag: {year_str}")
        
        _auto_add_drivetrain_tag(specs, tag_names)
        
        # 2.6.3 AUTO-ADD MODEL TAG from DB if not already present
        try:
            from news.models import Tag
            model_name = specs.get('model')
            make_name = specs.get('make')
            if model_name and model_name != 'Not specified':
                # Check if any Models-group tag matches
                has_model_tag = False
                model_tags = Tag.objects.filter(group__name='Models').values_list('name', flat=True)
                tag_names_lower = [t.lower() for t in tag_names]
                for mt in model_tags:
                    if mt.lower() in tag_names_lower:
                        has_model_tag = True
                        break
                if not has_model_tag:
                    # Try to find a matching Model tag in DB
                    for mt in model_tags:
                        mn_lower = model_name.lower()
                        mt_lower = mt.lower()
                        # Short names (e.g. 'S', 'X', 'e2') must match exactly
                        if len(mn_lower) <= 2 or len(mt_lower) <= 2:
                            if mn_lower == mt_lower:
                                tag_names.append(mt)
                                print(f"🏷️ Auto-added model tag: {mt}")
                                break
                        elif mn_lower in mt_lower or mt_lower in mn_lower:
                            tag_names.append(mt)
                            print(f"🏷️ Auto-added model tag: {mt}")
                            break
        except Exception as e:
            print(f"⚠️ Model tag auto-add failed: {e}")
        
        # 2.65. DUPLICATE CHECK — skip if article already exists for same car
        dup_result = check_car_duplicate(specs, send_progress=send_progress, exclude_article_id=exclude_article_id)
        if dup_result and dup_result.get('is_duplicate'):
            return {'success': False, 'status': 'skipped', 'reason': dup_result['reason'],
                    'existing_article_id': dup_result.get('existing_article_id'),
                    'existing_pending_id': dup_result.get('existing_pending_id'),
                    'error': dup_result['error']}
        
        # 2.7 WEB SEARCH ENRICHMENT
        web_context = ""
        try:
            from ai_engine.modules.searcher import get_web_context
            send_progress(4, 62, "🌐 Searching web for facts...")
            
            # Helper to clean model name if it's "Chin L"
            if "Chin" in specs.get('model', '') and "Qin" not in specs.get('model', ''):
                specs['model'] = specs['model'].replace("Chin", "Qin")
                
            web_context = get_web_context(specs)
            if web_context:
                print(f"✓ Web search successful")
        except Exception as e:
            print(f"⚠️ Web search failed: {e}")
        
        # 2.8 SPECS ENRICHMENT — fill gaps using web data
        if web_context:
            try:
                from ai_engine.modules.specs_enricher import enrich_specs_from_web
                send_progress(4, 63, "🔍 Cross-referencing specs...")
                specs = enrich_specs_from_web(specs, web_context)
                
                # Build enriched analysis to give the generator better data
                enriched_lines = []
                for key in ['make', 'model', 'trim', 'year', 'engine', 'torque', 
                           'acceleration', 'top_speed', 'drivetrain', 'battery', 'range', 'price']:
                    val = specs.get(key, 'Not specified')
                    if val and val != 'Not specified':
                        enriched_lines.append(f"{key.replace('_', ' ').title()}: {val}")
                hp = specs.get('horsepower')
                if hp:
                    enriched_lines.append(f"Horsepower: {hp} hp")
                
                if enriched_lines:
                    analysis += f"\n\n[ENRICHED SPECS FROM WEB]:\n" + '\n'.join(enriched_lines)
            except Exception as e:
                print(f"⚠️ Specs enrichment failed (continuing): {e}")
        
        # 2.85 SPEC REFILL — AI-fill remaining gaps if coverage < 70%
        try:
            from ai_engine.modules.spec_refill import refill_missing_specs, compute_coverage
            _, _, pre_coverage, _ = compute_coverage(specs)
            if pre_coverage < 70:
                send_progress(4, 64, f"🔄 Spec refill ({pre_coverage:.0f}% coverage)...")
                specs = refill_missing_specs(specs, article_html if 'article_html' in dir() else '', web_context, provider)
                refill_meta = specs.pop('_refill_meta', {})
                if refill_meta.get('triggered'):
                    _timings['spec_refill'] = True
                    print(f"🔄 Spec refill: {refill_meta.get('coverage_before', 0)}% → {refill_meta.get('coverage_after', 0)}%")
        except Exception as e:
            print(f"⚠️ Spec refill failed (continuing): {e}")
        
        # 2.86 SPECS VALIDATION — reject garbage values from AI extraction
        specs = _validate_specs(specs)

        # Step 5.1: POST-ENRICHMENT: re-check drivetrain tag (enricher may have found it)
        _auto_add_drivetrain_tag(specs, tag_names)
        
        # 2.10 AUTO-ADD SEGMENT TAG based on price
        try:
            try:
                from ai_engine.modules.analyzer import extract_price_usd
            except ImportError:
                from modules.analyzer import extract_price_usd
            price_usd = extract_price_usd(analysis)
            if price_usd and price_usd > 0:
                # Check if any price-based segment already assigned
                price_segments = {'Budget', 'Premium', 'Luxury'}
                has_price_segment = any(t in price_segments for t in tag_names)
                if not has_price_segment:
                    if price_usd < 25000:
                        tag_names.append('Budget')
                        print(f"🏷️ Auto-added segment: Budget (${price_usd:,.0f})")
                    elif 25000 <= price_usd < 50000:
                        tag_names.append('Mid-Range')
                        print(f"🏷️ Auto-added segment: Mid-Range (${price_usd:,.0f})")
                    elif 50000 <= price_usd < 80000:
                        tag_names.append('Premium')
                        print(f"🏷️ Auto-added segment: Premium (${price_usd:,.0f})")
                    elif price_usd >= 80000:
                        tag_names.append('Luxury')
                        print(f"🏷️ Auto-added segment: Luxury (${price_usd:,.0f})")
        except Exception as e:
            print(f"⚠️ Price segment auto-add failed: {e}")
        
        # 3. Generate Article
        _t_step = _time.time()
        send_progress(5, 65, f"✍️ Generating article with {provider_name}...")
        print(f"✍️  Generating article...")
        
        # Step 7: COMPETITOR LOOKUP — enrich prompt with real cars from our DB
        competitor_context, competitor_data = _get_competitor_context_safe(specs, send_progress)

        # Step 8: INTERNAL SPEC VERIFICATION — check our own DB for verified specs
        internal_specs_context = _get_internal_specs_context(specs)

        # Append internal specs to web_context so the generator sees them
        enriched_web_context = web_context
        if internal_specs_context:
            enriched_web_context = (internal_specs_context + "\n" + web_context) if web_context else internal_specs_context

        # Collect approved competitor makes for hallucination guard
        allowed_competitor_makes = list({c.get('make', '') for c in competitor_data if c.get('make')})

        # Pass web context + competitor context to generator
        article_html = generate_article(
            analysis, provider=provider,
            web_context=enriched_web_context,
            source_title=video_title,
            competitor_context=competitor_context or None,
            competitor_makes=allowed_competitor_makes or None,
        )
        
        if not article_html or len(article_html) < 100:
            send_progress(5, 100, "❌ Article generation failed")
            raise Exception("Article content is empty or too short")
        
        # Stamp the article with AI provider info (hidden from readers, visible in admin)
        # datetime already imported at top level
        gen_stamp = f"<!-- Generated by: {provider_name} | {datetime.now().strftime('%Y-%m-%d %H:%M')} -->"
        article_html = article_html.strip() + f"\n\n{gen_stamp}\n"
        
        _timings['generation'] = round(_time.time() - _t_step, 1)
        send_progress(5, 75, "✓ Article generated")
        
        # 4. Determine title + SEO description — AI-powered generation
        ai_title = None
        ai_seo_desc = None
        ai_summary = None
        
        # Priority 0: AI-generated title + SEO description (best quality)
        try:
            ai_result = _generate_title_and_seo(article_html, specs)
            if ai_result:
                ai_title = ai_result.get('title')
                ai_seo_desc = ai_result.get('seo_description')
                ai_summary = ai_result.get('summary')
                if ai_title:
                    print(f"🤖 AI-generated title: {ai_title}")
                if ai_seo_desc:
                    print(f"🤖 AI-generated SEO description ({len(ai_seo_desc)} chars): {ai_seo_desc}")
                if ai_summary:
                    print(f"🤖 AI-generated rich Summary ({len(ai_summary.split())} words)")
        except Exception as e:
            print(f"⚠️ AI title/SEO generation failed, using fallbacks: {e}")
        
        title = ai_title  # May be None if AI failed
        
        # Fallback 1: SEO Title from Analysis (clean YouTube noise from it)
        if not title and specs.get('seo_title') and len(specs['seo_title']) > 5:
            candidate = specs['seo_title'].replace('"', '').replace("'", "")
            candidate = clean_video_title(candidate)  # strip "walk around" etc.
            if not _is_generic_header(candidate):
                title = candidate
                print(f"📌 Fallback — SEO Title from Analysis: {title}")
            
        # Fallback 2: Extract from HTML <h2> (first non-generic header)
        if not title:
            extracted = extract_title(article_html)
            if extracted:
                title = extracted
                print(f"📌 Fallback — Extracted Title from HTML: {title}")
        
        # Fallback 3: Construct from Specs (if Make/Model exist)
        if not title and specs.get('make') and specs.get('model') and specs['make'] != 'Not specified':
            year = specs.get('year', '')
            year_str = f"{year} " if year else ""
            trim = specs.get('trim', '')
            trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
            title = f"{year_str}{specs['make']} {specs['model']}{trim_str} Review"
            print(f"📌 Fallback — Constructed Title from Specs: {title}")
            
        # Final validation — catches anything that slipped through
        title = validate_title(title, video_title=video_title, specs=specs)
        title = clean_video_title(title)  # final safety net for YouTube noise
        print(f"✅ Final validated title: {title}")
        
        # 4.5. Clean YouTube noise from article body too
        # AI may echo "walk around" in every car name mention
        noise_body_re = re.compile(
            r'\s+(walk[\s-]*around|walkaround|first\s+look|first\s+drive|test\s+drive)',
            re.IGNORECASE
        )
        article_html = noise_body_re.sub('', article_html)
        
        # 4.6 Content sanitization — strip non-Latin chars and duplicate words
        try:
            from ai_engine.modules.content_sanitizer import sanitize_article_html
            article_html = sanitize_article_html(article_html)
        except Exception as e:
            print(f"⚠️ Content sanitizer failed (continuing): {e}")
        
        # 4.7 AUTO-ADD TECH & FEATURES TAGS — scan article HTML for technology keywords
        # Done AFTER generation so we scan actual article, not raw analysis
        detected_tech_tags = []
        try:
            pre_count = len(tag_names)
            _auto_add_tech_tags(article_html, tag_names, specs)
            # Collect only the newly added tech tags
            detected_tech_tags = tag_names[pre_count:]
        except Exception as e:
            print(f"⚠️ Tech tag auto-add failed (continuing): {e}")
        
        # 4.8 INJECT TECH HIGHLIGHTS BLOCK into article HTML
        try:
            article_html = _inject_tech_highlights(article_html, detected_tech_tags)
        except Exception as e:
            print(f"⚠️ Tech highlights injection failed (continuing): {e}")
        
        # 5. Extract screenshots from video
        _t_step = _time.time()
        send_progress(6, 80, "📸 Extracting screenshots...")
        print("📸 Extracting screenshots...")
        screenshot_paths = []
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            local_paths = extract_video_screenshots(youtube_url, output_dir=screenshots_dir, count=6)
            
            if local_paths:
                # Upload to Cloudinary immediately
                import cloudinary
                import cloudinary.uploader
                import shutil
                from django.conf import settings
                
                print(f"☁️ Uploading {len(local_paths)} screenshots to Cloudinary...")
                for path in local_paths:
                    if os.path.exists(path):
                        uploaded = False
                        try:
                            # Try Cloudinary first
                            if os.getenv('CLOUDINARY_URL'):
                                upload_result = cloudinary.uploader.upload(
                                    path, 
                                    folder="pending_articles",
                                    resource_type="image"
                                )
                                secure_url = upload_result.get('secure_url')
                                if secure_url:
                                    screenshot_paths.append(secure_url)
                                    print(f"  ✓ Uploaded: {secure_url}")
                                    uploaded = True
                        except Exception as cloud_err:
                            print(f"  ⚠️ Cloudinary upload failed for {path}: {cloud_err}")
                        
                        # Fallback to local media if not uploaded
                        if not uploaded:
                            try:
                                # Copy to MEDIA_ROOT
                                media_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
                                os.makedirs(media_dir, exist_ok=True)
                                filename = os.path.basename(path)
                                dest_path = os.path.join(media_dir, filename)
                                shutil.copy2(path, dest_path)
                                # Store relative URL for DB and frontend
                                relative_url = os.path.join(settings.MEDIA_URL, 'screenshots', filename)
                                screenshot_paths.append(relative_url)
                                print(f"  ✓ Copied to media: {dest_path} -> {relative_url}")
                            except Exception as copy_err:
                                print(f"  ❌ Failed to copy to media: {copy_err}")
                                screenshot_paths.append(path) # Last resort
                    else:
                        screenshot_paths.append(path)
                        
                send_progress(6, 85, f"✓ Extracted and uploaded {len(screenshot_paths)} screenshots")
            else:
                send_progress(6, 85, "⚠️ No screenshots found")
        except Exception as e:
            print(f"⚠️  Screenshot extraction/upload error: {e}")
            screenshot_paths = []
        
        # Split images: first 4 for article (cover + 3 inline), rest for gallery
        gallery_paths = []
        if len(screenshot_paths) > 4:
            gallery_paths = screenshot_paths[4:]
            screenshot_paths = screenshot_paths[:4]
            print(f"  📸 Split: {len(screenshot_paths)} inline + {len(gallery_paths)} gallery")
        
        # 6. Create summary/description
        _timings['screenshots'] = round(_time.time() - _t_step, 1)
        send_progress(7, 90, "📝 Creating description...")
        import html
        
        # Try to extract summary from AI analysis if available
        # Target: 150-200 characters (for article cards, OG tags, listing pages)
        summary = ""
        if ai_summary and len(ai_summary) > 50:
            # Reject if summary is about transcript/error rather than the car
            _garbage_indicators = ['captcha', 'error page', 'could not be extracted',
                                   'provided text', 'not an actual', 'google captcha',
                                   'unable to', 'no information', 'automated query',
                                   'no specifications', 'consequently',
                                   'rather than', 'not the actual']
            if any(g in ai_summary.lower() for g in _garbage_indicators):
                print(f"⚠️ AI summary rejected (garbage content): {ai_summary[:80]}")
                ai_summary = None
            else:
                summary = ai_summary
                # Ensure AI summary stays within 200 chars for card display
                if len(summary) > 200:
                    summary = _truncate_summary(summary, max_len=200)
                print(f"✅ Using AI-generated Summary ({len(summary)} chars)")
        elif isinstance(analysis, str) and 'Summary:' in analysis:
            summary = analysis.split('Summary:')[-1].split('\n')[0].strip()
            if len(summary) > 200:
                summary = _truncate_summary(summary, max_len=200)
        elif isinstance(analysis, dict) and analysis.get('summary'):
            summary = str(analysis.get('summary'))
            if len(summary) > 200:
                summary = _truncate_summary(summary, max_len=200)
            
        if not summary:
            # Scrape from HTML, but skip the first heading (it's often redundant)
            # and thoroughly clean tags and unescape content
            temp_content = article_html
            # Skip first h2 if it exists
            if '</h2>' in temp_content:
                temp_content = temp_content.split('</h2>', 1)[-1]
            
            match = re.search(r'<p>(.*?)</p>', temp_content, re.DOTALL)
            if match:
                raw_text = match.group(1)
                # Unescape first to catch &lt;h2&gt; etc.
                clean_text = html.unescape(raw_text)
                # Strip any remaining tags
                summary = re.sub(r'<[^>]+>', '', clean_text).strip()
            else:
                # Absolute fallback from whole content
                clean_all = re.sub(r'<[^>]+>', '', html.unescape(temp_content))
                summary = clean_all.strip()
            
            # For fallback summaries (not AI-generated): truncate to 200 chars
            if len(summary) > 200:
                summary = _truncate_summary(summary, max_len=200)
                
        if not summary:
            summary = f"Comprehensive review of the {specs.get('make', '')} {specs.get('model', '')}"
        
        # POST-VALIDATION: reject summary that copies the article's first paragraph
        _first_para = ''
        _fp_match = re.search(r'<p>(.*?)</p>', article_html or '', re.DOTALL)
        if _fp_match:
            _first_para = re.sub(r'<[^>]+>', '', html.unescape(_fp_match.group(1))).strip()
        if _first_para and summary and len(_first_para) > 50:
            # Compare first 60 chars — if ≥80% overlap, summary is a lazy copy
            _s_prefix = summary[:60].lower().strip()
            _p_prefix = _first_para[:60].lower().strip()
            if _s_prefix == _p_prefix or (_s_prefix[:40] and _s_prefix[:40] in _p_prefix):
                _bad = {'', 'None', 'Not specified', 'N/A', 'none', 'n/a', 'not specified'}
                _clean = lambda v: '' if (v is None or str(v).strip() in _bad) else str(v).strip()
                _make = _clean(specs.get('make'))
                _model = _clean(specs.get('model'))
                _year = _clean(specs.get('year'))
                _hp_raw = _clean(specs.get('horsepower'))
                _price = _clean(specs.get('price'))
                _range = _clean(specs.get('range'))

                # Normalize hp: prefer hp value; if kW only, convert; always append unit
                _hp = ''
                if _hp_raw:
                    _hp_nums = re.findall(r'(\d+)', _hp_raw)
                    _has_hp = 'hp' in _hp_raw.lower() or 'bhp' in _hp_raw.lower() or 'ps' in _hp_raw.lower()
                    _has_kw = 'kw' in _hp_raw.lower()
                    if _hp_nums:
                        if _has_hp:
                            # Already has hp unit, find the hp number
                            _hp_match = re.search(r'(\d+)\s*(?:hp|bhp|ps)', _hp_raw, re.IGNORECASE)
                            _hp = f"{_hp_match.group(1)} hp" if _hp_match else f"{_hp_nums[0]} hp"
                        elif _has_kw:
                            # kW only — convert to hp for display (1 kW ≈ 1.341 hp)
                            _kw_val = int(_hp_nums[0])
                            _hp = f"{round(_kw_val * 1.341)} hp"
                        else:
                            # Bare number — assume hp if in realistic hp range
                            _n = int(_hp_nums[0])
                            if 50 <= _n <= 2000:
                                _hp = f"{_n} hp"

                # If specs are empty (e.g. promo video), try extracting from generated HTML spec bar
                if not _hp:
                    _m = re.search(r'<div class="spec-label">POWER</div>\s*<div class="spec-value">([^<]+)</div>', article_html or '', re.IGNORECASE)
                    if _m: _hp = _clean(_m.group(1))
                if not _range:
                    _m = re.search(r'<div class="spec-label">RANGE</div>\s*<div class="spec-value">([^<]+)</div>', article_html or '', re.IGNORECASE)
                    if _m: _range = _clean(_m.group(1))
                if not _price:
                    _m = re.search(r'<div class="spec-label">(?:\w+\s+)?PRICE</div>\s*<div class="spec-value">([^<]+)</div>', article_html or '', re.IGNORECASE)
                    if _m: _price = _clean(_m.group(1))
                
                if _make and _model:
                    _name = f"The {_year + ' ' if _year else ''}{_make} {_model}"
                    _parts = [_name]
                    if _hp:
                        _parts.append(f"delivers {_hp}")
                    if _range:
                        _parts.append(f"with {_range} range")
                    if _price:
                        _parts.append(f"starting at {_price}")
                    summary = ', '.join(_parts) + '.'
                    if len(summary) > 200:
                        summary = _truncate_summary(summary, max_len=200)
                    print(f"✅ Rebuilt summary from specs ({len(summary)} chars): {summary[:80]}")
                else:
                    print(f"⚠️ Cannot rebuild summary: make={repr(_make)}, model={repr(_model)}")
        
        # 6.1 SEO description — use AI-generated if available, else template fallback
        seo_description = ''
        if ai_seo_desc and len(ai_seo_desc) >= 80:
            seo_description = ai_seo_desc
            # POST-VALIDATION: ensure SEO description fits 160 chars and ends properly
            if len(seo_description) > 160:
                # Trim to last complete sentence within 160 chars
                _trimmed = seo_description[:160]
                _last_period = _trimmed.rfind('.')
                if _last_period > 80:
                    seo_description = _trimmed[:_last_period + 1]
                else:
                    seo_description = _trimmed.rsplit(' ', 1)[0] + '...'
                print(f"⚠️ Trimmed AI SEO description to {len(seo_description)} chars")
            elif not seo_description.rstrip().endswith(('.', '!', '?')):
                # AI text doesn't end with punctuation — it was likely cut off
                _last_period = seo_description.rfind('.')
                if _last_period > 80:
                    seo_description = seo_description[:_last_period + 1]
                    print(f"⚠️ Trimmed SEO description at last sentence ({len(seo_description)} chars)")
                else:
                    seo_description = seo_description.rstrip() + '.'
            print(f"✅ Using AI-generated SEO description ({len(seo_description)} chars)")
        else:
            # Fallback: template-based SEO description
            make = specs.get('make', '')
            model = specs.get('model', '')
            year = specs.get('year', '')
            hp_raw = str(specs.get('horsepower', '') or '')
            
            # Extract clean numeric HP and validate range (50-2000 is realistic)
            hp_num = None
            hp_match = re.search(r'(\d{2,4})', hp_raw)
            if hp_match:
                val = int(hp_match.group(1))
                if 50 <= val <= 2000:
                    hp_num = val
            
            if make and model and make != 'Not specified':
                year_str = f"{year} " if year else ""
                hp_str = f", {hp_num} HP" if hp_num else ""
                # Build data-rich SEO description with key specs
                range_val = specs.get('range', '')
                price_val = specs.get('price', '')
                range_str = f", {range_val} range" if range_val and range_val != 'Not specified' else ""
                price_str = f" from {price_val}" if price_val and price_val != 'Not specified' else ""
                seo_description = f"The {year_str}{make} {model}{hp_str}{range_str}{price_str}. Full specs, pricing, performance data & expert review."
                if len(seo_description) > 160:
                    seo_description = seo_description[:157].rsplit(' ', 1)[0] + '...'
            if not seo_description:
                seo_description = summary[:157].rsplit(' ', 1)[0] + '...' if len(summary) > 160 else summary
            print(f"📌 Fallback SEO description ({len(seo_description)} chars)")
        
        # 6.5. Generate SEO keywords
        try:
            from ai_engine.modules.seo_helpers import generate_seo_keywords
        except ImportError:
            from modules.seo_helpers import generate_seo_keywords
        seo_keywords = ''
        if isinstance(analysis, dict):
            seo_keywords = generate_seo_keywords(analysis, title)
        
        content_original = article_html  # preserve for metadata
        send_progress(8, 95, "✅ Generation complete")
        
        # 8. SEO Internal Linking
        send_progress(9, 97, "🔗 Injecting SEO internal links...")
        try:
            from ai_engine.modules.seo_linker import inject_internal_links
            article_html = inject_internal_links(article_html, tag_names, specs.get('make'))
        except Exception as seo_err:
            print(f"⚠️ SEO Linker failed: {seo_err}")
        
        # 8.5. Inject inline image placeholders into article body
        # Places {{IMAGE_2}} and {{IMAGE_3}} between h2 sections at logical positions
        if len(screenshot_paths) >= 2:
            # Primary: body_type only — fuel_type matching was causing too many misses
            # (EREV cars stored inconsistently in DB; price proximity handles segment well)
            # fuel_type is preserved as a soft signal in the weight function (body_bonus)
            try:
                article_html = _inject_inline_image_placeholders(article_html, len(screenshot_paths) - 1)
            except Exception as img_err:
                print(f"⚠️ Inline image placeholder injection failed: {img_err}")
            
        # Build generation metadata
        _timings['total'] = round(_time.time() - _t_start, 1)
        generation_metadata = {
            'provider': provider,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'timings': _timings,
            'competitor_data': competitor_data,  # for ML logging after article save
        }
        print(f"📊 Generation timing: {_timings}")
        
        # Record provider performance for tracking
        try:
            from ai_engine.modules.provider_tracker import record_generation
            from ai_engine.modules.spec_refill import compute_coverage
            import ai_engine.modules.ai_provider as _ai_mod
            _, _, _spec_cov, _ = compute_coverage(specs)
            # Use exact model name if Gemini (e.g. 'gemini-2.5-flash-lite')
            _model_used = _ai_mod._last_model_used if provider == 'gemini' else provider
            record_generation(
                provider=provider,
                make=specs.get('make', ''),
                quality_score=0,  # filled later by quality_scorer
                spec_coverage=_spec_cov,
                total_time=_timings.get('total', 0),
                spec_fields_filled=int(_spec_cov / 10),
                model=_model_used,
                step_timings=_timings,
            )
        except Exception as e:
            print(f"⚠️ Provider tracking failed: {e}")
        
        return {
            'success': True,
            'title': title,
            'content': article_html,
            'content_original': content_original,
            'summary': summary,
            'seo_description': seo_description,
            'category_name': category_name,
            'tag_names': tag_names,
            'specs': specs,
            'meta_keywords': seo_keywords,
            'image_paths': screenshot_paths,
            'gallery_paths': gallery_paths,
            'analysis': analysis,
            'web_context': web_context,
            'video_title': video_title,
            'author_name': author_name,
            'author_channel_url': author_channel_url,
            'generation_metadata': generation_metadata
        }
        
    except Exception as e:
        import traceback
        err_str = str(e)
        err_tb = traceback.format_exc()
        print(f"❌ Error in _generate_article_content: {err_str}")
        print(err_tb)

        # If it's already a structured GenerationError, pass its info up
        try:
            from ai_engine.modules.generation_errors import GenerationError, is_token_limit_error
        except ImportError:
            from modules.generation_errors import GenerationError, is_token_limit_error

        if isinstance(e, GenerationError):
            result = e.to_result_dict()
            result['traceback'] = err_tb[:1000]
            return result

        # For unexpected exceptions, detect token-limit errors and mark for retry
        needs_retry = is_token_limit_error(err_str)
        return {
            'success': False,
            'error': err_str,
            'error_step': 'unknown',
            'needs_retry': needs_retry,
            'retry_after_seconds': 300 if needs_retry else None,
            'traceback': err_tb[:1000],
            'degradation_report': None,
        }
