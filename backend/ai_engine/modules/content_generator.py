"""
Article content generation pipeline.

Takes a YouTube URL, fetches transcript, analyzes it, generates an article,
extracts specs, enriches with web data, runs AI editor, and injects SEO links.

This is the core generation engine used by both the direct-publish and
pending-article workflows.
"""
import os
import sys
import re
import logging
import requests

logger = logging.getLogger(__name__)

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def _send_progress(task_id, step, progress, message):
    """Send progress update via WebSocket."""
    if not task_id:
        print(f"[{progress}%] {message}")
        return
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"generation_{task_id}",
                {
                    "type": "send_progress",
                    "step": step,
                    "progress": progress,
                    "message": message
                }
            )
    except Exception as e:
        print(f"WebSocket progress error: {e}")


def _generate_article_content(youtube_url, task_id=None, provider='gemini', video_title=None, exclude_article_id=None):
    """
    Internal function to generate article content without saving to DB.
    Returns dictionary with all article data.
    """
    # Import modules (with fallback for different run contexts)
    try:
        from ai_engine.modules.transcriber import transcribe_from_youtube
        from ai_engine.modules.analyzer import analyze_transcript
        from ai_engine.modules.article_generator import generate_article
        from ai_engine.modules.downloader import extract_video_screenshots
        from ai_engine.modules.title_utils import extract_title, validate_title, _is_generic_header
        from ai_engine.modules.duplicate_checker import check_car_duplicate
    except ImportError:
        from modules.transcriber import transcribe_from_youtube
        from modules.analyzer import analyze_transcript
        from modules.article_generator import generate_article
        from modules.downloader import extract_video_screenshots
        from modules.title_utils import extract_title, validate_title, _is_generic_header
        from modules.duplicate_checker import check_car_duplicate

    def send_progress(step, progress, message):
        _send_progress(task_id, step, progress, message)

    try:
        import time as _time
        _t_start = _time.time()
        _timings = {}
        
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

        # 1. Fetch transcript
        _t_step = _time.time()
        send_progress(2, 20, "📝 Fetching subtitles from YouTube...")
        print("📝 Fetching transcript...")
        transcript = transcribe_from_youtube(youtube_url)
        _timings['transcript'] = round(_time.time() - _t_step, 1)
        
        if not transcript or len(transcript) < 5 or transcript.startswith("ERROR:"):
            error_msg = transcript if transcript and transcript.startswith("ERROR:") else "Failed to retrieve transcript or it is too short"
            send_progress(2, 100, f"❌ {error_msg}")
            raise Exception(error_msg)
        
        send_progress(2, 30, f"✓ Transcript received ({len(transcript)} chars)")
        
        # 2. Analyze transcript
        _t_step = _time.time()
        send_progress(3, 40, f"🔍 Analyzing transcript with {provider_name} AI...")
        print("🔍 Analyzing transcript...")
        analysis = analyze_transcript(transcript, video_title=video_title, provider=provider)
        
        if not analysis:
            send_progress(3, 100, "❌ Analysis failed")
            raise Exception("Failed to analyze transcript")
        
        _timings['analysis'] = round(_time.time() - _t_step, 1)
        send_progress(3, 50, "✓ Analysis complete")
        
        # 2.5. Categorize and Tags
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
        
        # 2.6.2 AUTO-ADD DRIVETRAIN TAG from enriched specs
        drivetrain = specs.get('drivetrain')
        if drivetrain and drivetrain not in ('Not specified', '', None):
            dt_upper = drivetrain.upper()
            has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
            if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
                tag_names.append(dt_upper)
                print(f"🏷️ Auto-added drivetrain tag: {dt_upper}")
        
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
                        if model_name.lower() in mt.lower() or mt.lower() in model_name.lower():
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
        
        # 2.9 POST-ENRICHMENT: auto-add drivetrain tag if enricher found it
        drivetrain = specs.get('drivetrain')
        if drivetrain and drivetrain not in ('Not specified', '', None):
            dt_upper = drivetrain.upper()
            has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
            if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
                tag_names.append(dt_upper)
                print(f"🏷️ Auto-added drivetrain tag (post-enrichment): {dt_upper}")
        
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
        
        # Pass web context to generator
        article_html = generate_article(analysis, provider=provider, web_context=web_context, source_title=video_title)
        
        if not article_html or len(article_html) < 100:
            send_progress(5, 100, "❌ Article generation failed")
            raise Exception("Article content is empty or too short")
        
        # Stamp the article with AI provider info (hidden from readers, visible in admin)
        from datetime import datetime
        gen_stamp = f"<!-- Generated by: {provider_name} | {datetime.now().strftime('%Y-%m-%d %H:%M')} -->"
        article_html = article_html.strip() + f"\n\n{gen_stamp}\n"
        
        _timings['generation'] = round(_time.time() - _t_step, 1)
        send_progress(5, 75, "✓ Article generated")
        
        # 4. Determine title — multi-layer validation
        title = None
        
        # Priority 1: SEO Title from Analysis
        if specs.get('seo_title') and len(specs['seo_title']) > 5:
            candidate = specs['seo_title'].replace('"', '').replace("'", "")
            if not _is_generic_header(candidate):
                title = candidate
                print(f"📌 Using SEO Title from Analysis: {title}")
            
        # Priority 2: Extract from HTML <h2> (first non-generic header)
        if not title:
            extracted = extract_title(article_html)
            if extracted:
                title = extracted
                print(f"📌 Extracted Title from HTML: {title}")
        
        # Priority 3: Construct from Specs (if Make/Model exist)
        if not title and specs.get('make') and specs.get('model') and specs['make'] != 'Not specified':
            year = specs.get('year', '')
            year_str = f"{year} " if year else ""
            trim = specs.get('trim', '')
            trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
            title = f"{year_str}{specs['make']} {specs['model']}{trim_str} Review"
            print(f"📌 Constructed Title from Specs: {title}")
            
        # Final validation — catches anything that slipped through
        title = validate_title(title, video_title=video_title, specs=specs)
        print(f"✅ Final validated title: {title}")
        
        # 5. Extract screenshots from video
        _t_step = _time.time()
        send_progress(6, 80, "📸 Extracting screenshots...")
        print("📸 Extracting screenshots...")
        screenshot_paths = []
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            local_paths = extract_video_screenshots(youtube_url, output_dir=screenshots_dir, count=3)
            
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
            print(f"⚠️  Ошибка при извлечении/загрузке скриншотов: {e}")
            screenshot_paths = []
        
        # 6. Create summary/description
        _timings['screenshots'] = round(_time.time() - _t_step, 1)
        send_progress(7, 90, "📝 Creating description...")
        import html
        
        # Try to extract summary from AI analysis if available
        summary = ""
        if isinstance(analysis, str) and 'Summary:' in analysis:
            summary = analysis.split('Summary:')[-1].split('\n')[0].strip()
        elif isinstance(analysis, dict) and analysis.get('summary'):
            summary = analysis.get('summary')
            
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
                summary = re.sub(r'<[^>]+>', '', clean_text).strip()[:300]
            else:
                # Absolute fallback from whole content
                clean_all = re.sub(r'<[^>]+>', '', html.unescape(temp_content))
                summary = clean_all.strip()[:300]
                
        if not summary:
            summary = f"Comprehensive review of the {specs.get('make', '')} {specs.get('model', '')}"
        
        # 6.5. Generate SEO keywords
        try:
            from ai_engine.modules.seo_helpers import generate_seo_keywords
        except ImportError:
            from modules.seo_helpers import generate_seo_keywords
        seo_keywords = ''
        if isinstance(analysis, dict):
            seo_keywords = generate_seo_keywords(analysis, title)
        
        # 7. AI Editor — removed (rules consolidated into main generation prompt)
        content_original = article_html  # preserve for metadata
        _t_step = _time.time()
        send_progress(8, 95, "✅ Generation complete")
        ai_editor_diff = {'changed': False, 'skipped': True, 'reason': 'consolidated_into_prompt'}
        _timings['ai_editor'] = round(_time.time() - _t_step, 1)
        
        # 8. SEO Internal Linking
        send_progress(9, 97, "🔗 Injecting SEO internal links...")
        try:
            from ai_engine.modules.seo_linker import inject_internal_links
            article_html = inject_internal_links(article_html, tag_names, specs.get('make'))
        except Exception as seo_err:
            print(f"⚠️ SEO Linker failed: {seo_err}")
            
        # Build generation metadata
        _timings['total'] = round(_time.time() - _t_start, 1)
        generation_metadata = {
            'provider': provider,
            'timestamp': datetime.utcnow().isoformat(),
            'timings': _timings,
            'ai_editor': ai_editor_diff,
        }
        print(f"📊 Generation timing: {_timings}")
        
        # Record provider performance for tracking
        try:
            from ai_engine.modules.provider_tracker import record_generation
            from ai_engine.modules.spec_refill import compute_coverage
            _, _, _spec_cov, _ = compute_coverage(specs)
            record_generation(
                provider=provider,
                make=specs.get('make', ''),
                quality_score=0,  # filled later by quality_scorer
                spec_coverage=_spec_cov,
                total_time=_timings.get('total', 0),
                spec_fields_filled=int(_spec_cov / 10),
            )
        except Exception as e:
            print(f"⚠️ Provider tracking failed: {e}")
        
        return {
            'success': True,
            'title': title,
            'content': article_html,
            'content_original': content_original,
            'summary': summary,
            'category_name': category_name,
            'tag_names': tag_names,
            'specs': specs,
            'meta_keywords': seo_keywords,
            'image_paths': screenshot_paths,
            'analysis': analysis,
            'web_context': web_context,
            'video_title': video_title,
            'author_name': author_name,
            'author_channel_url': author_channel_url,
            'generation_metadata': generation_metadata
        }
        
    except Exception as e:
        print(f"❌ Error in _generate_article_content: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }
