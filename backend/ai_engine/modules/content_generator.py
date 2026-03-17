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
from datetime import datetime, timezone

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


def _truncate_summary(text: str, max_len: int = 3000) -> str:
    """Truncate summary at a sentence or word boundary.
    
    Priority: last sentence end (.) within limit > last word boundary > hard cut.
    Targets ~500 words (3000 chars) for rich article preview cards.
    """
    if len(text) <= max_len:
        return text
    
    truncated = text[:max_len]
    
    # Try to cut at last sentence end (period followed by space or end)
    last_period = truncated.rfind('. ')
    if last_period > max_len * 0.4:  # Only if we keep at least 40% of content
        return truncated[:last_period + 1]
    
    # Fall back to last word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.5:
        return truncated[:last_space]
    
    # Hard cut (very rare — would need 1500+ char word)
    return truncated


def _generate_title_and_seo(article_html: str, specs: dict) -> dict:
    """
    Generate an engaging title and SEO description using a lightweight AI call.
    
    This runs AFTER article generation, so the AI can pick the most impressive
    fact from the completed article for the title hook.
    
    Returns: {'title': str, 'seo_description': str} or None on failure.
    """
    # re already imported globally
    
    try:
        from ai_engine.modules.ai_provider import get_generate_provider
    except ImportError:
        from modules.ai_provider import get_generate_provider
    
    # Extract key specs for the prompt
    make = specs.get('make', '')
    model = specs.get('model', '')
    year = specs.get('year', '')
    trim = specs.get('trim', '')
    hp = specs.get('horsepower', '')
    price = specs.get('price', '')
    range_val = specs.get('range', '')
    
    if not make or make == 'Not specified' or not model or model == 'Not specified':
        print("⚠️ Cannot generate AI title: missing make/model")
        return None
    
    # Format specs nicely
    year_str = f"{year} " if year else ""
    trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
    hp_str = f" • {hp}" if hp else ""
    price_str = f" • {price}" if price else ""
    range_str = f" • {range_val}" if range_val else ""
    
    # Prepare preview
    article_preview = _truncate_summary(article_html, max_len=4000)  # uses global re
    
    prompt = f"""Generate a TITLE, SEO DESCRIPTION, and SUMMARY for this car article.

CAR: {year_str}{make} {model}{trim_str}
KEY SPECS: {hp_str}{price_str}{range_str}

ARTICLE PREVIEW:
{article_preview}

═══ TITLE RULES ═══
- LENGTH: 50-90 characters (STRICT — count carefully)
- FORMAT: "[Year] [Brand] [Model]: [Engaging hook with standout spec or price]"

═══ SEO DESCRIPTION RULES ═══  
- LENGTH: STRICTLY 150-160 CHARACTERS (letters, not words!). This is usually 20-25 words.
- MUST include: car name, standout specs, and a reason to click.
- Include numbers if possible: price, range, horsepower, 0-100 time.

═══ SUMMARY RULES ═══
- LENGTH: STRICTLY 150-200 CHARACTERS (2-3 sentences).
- Used on article cards, social previews, and listing pages.
- Include the car name and its most impressive spec or selling point.
- Must be a complete, engaging sentence — NOT truncated mid-word.
- Do NOT write a long essay. Just 2-3 punchy sentences.

═══ OUTPUT FORMAT (strict) ═══
TITLE: [your title here]
SEO_DESCRIPTION: [your description here, STRICTLY 150-160 chars]
SUMMARY: [your 150-200 char summary here]
"""

    try:
        ai = get_generate_provider()
        result = ai.generate_completion(
            prompt=prompt,
            system_prompt="You are a senior automotive SEO specialist and editor. Generate concise, high-quality metadata.",
            temperature=0.7,
            max_tokens=2500,
            caller='title_seo'
        )

        
        if not result:
            return None
        
        # Parse the response
        title = None
        seo_desc = None
        
        # re already imported globally
        
        title_match = re.search(r'TITLE:\s*(.+?)(?=\nSEO_DESCRIPTION:|\nSUMMARY:|$)', result, re.IGNORECASE | re.DOTALL)
        seo_match = re.search(r'SEO_?DESCRIPTION:\s*(.+?)(?=\nSUMMARY:|\nTITLE:|$)', result, re.IGNORECASE | re.DOTALL)
        summary_match = re.search(r'SUMMARY:\s*(.+?)(?=\nSEO_DESCRIPTION:|\nTITLE:|$)', result, re.IGNORECASE | re.DOTALL)
        
        title = title_match.group(1).strip().strip('"').strip("'") if title_match else None
        seo_desc = seo_match.group(1).strip().strip('"').strip("'") if seo_match else None
        summary = summary_match.group(1).strip().strip('"').strip("'") if summary_match else None
        
        if seo_desc:
            seo_desc = seo_desc.replace('\n', ' ')
        
        # Validate title
        if title:
            title = title.strip('"').strip("'")
            if len(title) < 20 or len(title) > 120:
                print(f"⚠️ AI title rejected (length {len(title)}): {title}")
                title = None
            elif title.lower().endswith(('review', 'review & specs', 'range & specs')):
                print(f"⚠️ AI title rejected (generic suffix): {title}")
                title = None
        
        # Validate SEO description
        if seo_desc:
            seo_desc = seo_desc.strip('"').strip("'")
            if len(seo_desc) < 80:
                print(f"⚠️ AI SEO description rejected (too short: {len(seo_desc)}): {seo_desc}")
                seo_desc = None
            elif len(seo_desc) > 160:
                seo_desc = seo_desc[:157].rsplit(' ', 1)[0]
                if not seo_desc.endswith('.'):
                    seo_desc += '...'
        
        if title or seo_desc or summary:
            return {'title': title, 'seo_description': seo_desc, 'summary': summary}
        
        return None
        
    except Exception as e:
        print(f"⚠️ _generate_title_and_seo failed: {e}")
        return None


def _validate_specs(specs: dict) -> dict:
    """Sanitize extracted specs — reject garbage values that AI sometimes hallucinates."""
    if not specs:
        return specs

    # Define realistic ranges for numeric fields
    RANGES = {
        'horsepower': (50, 2500),
        'torque': (50, 2500),       # Nm
        'top_speed': (80, 500),     # km/h
        'range': (50, 2500),        # km
    }
    for key, (lo, hi) in RANGES.items():
        val = specs.get(key)
        if not val or val == 'Not specified':
            continue
        nums = re.findall(r'\d+', str(val))
        if nums:
            n = int(nums[0])
            if not (lo <= n <= hi):
                print(f"⚠️ Specs validation: {key}={val!r} out of range ({lo}-{hi}), clearing")
                specs[key] = None

    # Validate year
    year = specs.get('year')
    if year:
        year_nums = re.findall(r'\d{4}', str(year))
        if year_nums and not (2018 <= int(year_nums[0]) <= 2028):
            print(f"⚠️ Specs validation: year={year!r} out of range, clearing")
            specs['year'] = None

    # Validate acceleration (0-100 in 1.5-25 seconds)
    accel = specs.get('acceleration')
    if accel and accel != 'Not specified':
        accel_nums = re.findall(r'[\d.]+', str(accel))
        if accel_nums:
            a = float(accel_nums[0])
            if not (1.5 <= a <= 25):
                print(f"⚠️ Specs validation: acceleration={accel!r} out of range, clearing")
                specs['acceleration'] = None

    return specs


def _auto_add_drivetrain_tag(specs: dict, tag_names: list) -> None:
    """Auto-add drivetrain tag (AWD/FWD/RWD/4WD) if present in specs and not yet tagged."""
    drivetrain = specs.get('drivetrain')
    if drivetrain and drivetrain not in ('Not specified', '', None):
        dt_upper = drivetrain.upper()
        has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
        if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
            tag_names.append(dt_upper)
            print(f"🏷️ Auto-added drivetrain tag: {dt_upper}")


def _get_internal_specs_context(specs: dict) -> str:
    """Check our VehicleSpecs DB for verified specs and return context string for prompt."""
    try:
        from news.models.vehicles import VehicleSpecs
        _make = specs.get('make', '')
        _model = specs.get('model', '')
        if not (_make and _model and _make != 'Not specified'):
            return ""
        existing = VehicleSpecs.objects.filter(
            make__iexact=_make,
            model_name__icontains=_model,
        ).order_by('-updated_at').first()
        if not existing:
            print(f"ℹ️ No existing VehicleSpecs for {_make} {_model}")
            return ""
        parts = [
            f"Make: {existing.make}",
            f"Model: {existing.model_name}",
        ]
        field_map = [
            ('trim_name', 'Trim'), ('model_year', 'Year'),
            ('power_hp', 'Power (hp)'), ('power_kw', 'Power (kW)'),
            ('torque_nm', 'Torque (Nm)'), ('battery_kwh', 'Battery (kWh)'),
            ('acceleration_0_100', '0-100 (s)'),
            ('fuel_type', 'Fuel Type'), ('body_type', 'Body Type'),
            ('drivetrain', 'Drivetrain'),
        ]
        for attr, label in field_map:
            val = getattr(existing, attr, None)
            if val:
                parts.append(f"{label}: {val}")
        range_val = existing.range_wltp or existing.range_cltc or existing.range_epa or existing.range_km
        if range_val:
            parts.append(f"Range: {range_val} km")
        if existing.price_usd_from:
            parts.append(f"Price: from ${existing.price_usd_from:,}")
        if len(parts) > 4:
            ctx = (
                "\n═══ VERIFIED SPECS FROM OUR DATABASE (HIGH PRIORITY) ═══\n"
                "We already have this car in our database with VERIFIED specs.\n"
                "Use these as GROUND TRUTH — they override web search data:\n"
                + "\n".join(f"  ▸ {p}" for p in parts)
                + "\n\nIf your article contradicts these numbers, YOUR article is WRONG.\n"
                "═══════════════════════════════════════════════\n"
            )
            print(f"✅ Internal DB match: {existing.make} {existing.model_name} — injecting verified specs")
            return ctx
        else:
            print(f"ℹ️ Internal DB match found but sparse data ({len(parts)} fields)")
            return ""
    except Exception as e:
        print(f"⚠️ Internal spec verification failed (non-fatal): {e}")
        return ""


def _get_competitor_context_safe(specs: dict, send_progress) -> tuple:
    """Safely look up competitor cars from DB. Returns (context_str, competitor_data_list)."""
    try:
        from ai_engine.modules.competitor_lookup import get_competitor_context
        _make = specs.get('make', '')
        _model = specs.get('model', '')
        _fuel_raw = specs.get('powertrain_type') or specs.get('fuel_type') or ''
        _fuel_map = {
            'ev': 'EV', 'electric': 'EV', 'bev': 'EV',
            'phev': 'PHEV', 'plug-in': 'PHEV',
            'hybrid': 'Hybrid', 'erev': 'Hybrid',
            'gas': 'Gas', 'petrol': 'Gas', 'ice': 'Gas',
            'diesel': 'Diesel', 'hydrogen': 'Hydrogen',
        }
        _fuel_type = _fuel_map.get(_fuel_raw.lower().strip(), '')
        _body_type = specs.get('body_type', '')
        _power_hp = None
        _price_usd = None
        try:
            hp_match = re.search(r'(\d+)\s*(?:hp|HP|bhp)', specs.get('horsepower', ''))
            if hp_match:
                _power_hp = int(hp_match.group(1))
            _price_usd = int(specs.get('price_usd', 0) or 0) or None
        except Exception:
            pass
        if _make and _model:
            send_progress(4, 64, "🏆 Finding similar cars for comparison...")
            ctx, data = get_competitor_context(
                make=_make, model_name=_model,
                fuel_type=_fuel_type, body_type=_body_type,
                power_hp=_power_hp, price_usd=_price_usd,
            )
            if ctx:
                print(f"✓ Competitor context: {len(data)} cars found for comparison")
            else:
                print("ℹ️ No competitor context — no matching cars in DB yet")
            return ctx, data
    except Exception as e:
        print(f"⚠️ Competitor lookup failed (non-fatal): {e}")
    return "", []


def _inject_inline_image_placeholders(html: str, max_images: int = 2) -> str:
    """
    Insert {{IMAGE_2}} and {{IMAGE_3}} placeholders into article HTML
    at logical section breaks between <h2> headings.

    Strategy:
    - Find all <h2> section boundaries
    - Skip sections containing custom blocks (spec-bar, pros-cons, verdict, compare-grid)
    - Distribute placeholders evenly across remaining text-heavy sections
    - Insert each placeholder BEFORE the <h2> heading of the target section
      (so the image appears at the end of the previous section)

    Args:
        html: Generated article HTML
        max_images: Number of placeholders to insert (typically 2 for IMAGE_2 + IMAGE_3)
    
    Returns:
        HTML with {{IMAGE_2}} and {{IMAGE_3}} placeholders inserted
    """
    # Custom blocks to avoid placing images near
    SKIP_CLASSES = ['spec-bar', 'pros-cons', 'fm-verdict', 'compare-grid',
                    'price-tag', 'powertrain-specs']

    # Find all <h2> positions (these are section boundaries)
    h2_pattern = re.compile(r'<h2[^>]*>', re.IGNORECASE)
    h2_matches = list(h2_pattern.finditer(html))

    if len(h2_matches) < 3:
        print(f"  📸 Not enough sections ({len(h2_matches)}) for inline images, skipping")
        return html

    # Build a list of "insertable" positions (indices of h2 tags where we CAN place an image before)
    insertable = []
    for i, match in enumerate(h2_matches):
        if i == 0:
            continue  # Never before the first h2 (title)

        # Check the content between this h2 and the previous one
        prev_end = h2_matches[i - 1].end()
        section_content = html[prev_end:match.start()]

        # Skip if the section contains custom blocks
        has_custom_block = any(cls in section_content for cls in SKIP_CLASSES)
        if has_custom_block:
            continue

        # Skip if section is too short (< 200 chars of text = probably just a heading + 1 line)
        text_only = re.sub(r'<[^>]+>', '', section_content).strip()
        if len(text_only) < 200:
            continue

        insertable.append(match.start())

    if not insertable:
        print("  📸 No suitable positions found for inline images")
        return html

    # Distribute images evenly across available positions
    num_to_place = min(max_images, len(insertable))
    if num_to_place == 0:
        return html

    # Pick evenly spaced positions
    if num_to_place == 1:
        chosen_indices = [len(insertable) // 2]
    else:
        step = len(insertable) / (num_to_place + 1)
        chosen_indices = [int(step * (i + 1)) for i in range(num_to_place)]
        # Clamp to valid range
        chosen_indices = [min(idx, len(insertable) - 1) for idx in chosen_indices]
        # Deduplicate
        chosen_indices = list(dict.fromkeys(chosen_indices))

    # Build placeholder tags (IMAGE_2 = first inline, IMAGE_3 = second inline)
    placeholders = ['{{IMAGE_2}}', '{{IMAGE_3}}']

    # Insert from end to start (to preserve positions)
    placed = 0
    for idx in reversed(chosen_indices):
        if placed >= len(placeholders):
            break
        pos = insertable[idx]
        placeholder_idx = len(chosen_indices) - 1 - list(reversed(chosen_indices)).index(idx)
        if placeholder_idx < len(placeholders):
            tag = placeholders[placeholder_idx]
            # Insert the placeholder right before the <h2> with a newline
            html = html[:pos] + f'\n{tag}\n' + html[pos:]
            placed += 1

    print(f"  📸 Inserted {placed} inline image placeholder(s) into article body")
    return html


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

        # Pass web context + competitor context to generator
        article_html = generate_article(
            analysis, provider=provider,
            web_context=enriched_web_context,
            source_title=video_title,
            competitor_context=competitor_context or None,
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
            summary = ai_summary
            # Ensure AI summary stays within 200 chars for card display
            if len(summary) > 200:
                summary = _truncate_summary(summary, max_len=200)
            print(f"✅ Using AI-generated Summary ({len(summary)} chars)")
        elif isinstance(analysis, str) and 'Summary:' in analysis:
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
        
        # 6.1 SEO description — use AI-generated if available, else template fallback
        seo_description = ''
        if ai_seo_desc and len(ai_seo_desc) >= 100:
            seo_description = ai_seo_desc
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
        print(f"❌ Error in _generate_article_content: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }
