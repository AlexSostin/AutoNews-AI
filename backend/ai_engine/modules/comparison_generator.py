"""
Comparison Article Generator
Auto-generates "X vs Y" comparison articles from VehicleSpecs data.

The AI does NOT generate specs — it only writes analysis around DB-provided data.
This eliminates hallucinated numbers and minimizes token usage.
"""
import re
import logging

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.ai_provider import get_ai_provider
    from ai_engine.modules.article_generator import post_process_article, ensure_html_only
    from ai_engine.modules.searcher import search_car_details
    from ai_engine.modules.prompt_sanitizer import ANTI_INJECTION_NOTICE
except ImportError:
    from modules.ai_provider import get_ai_provider
    from modules.article_generator import post_process_article, ensure_html_only
    from modules.searcher import search_car_details
    from modules.prompt_sanitizer import ANTI_INJECTION_NOTICE


def _fmt(val, suffix='', fallback='N/A'):
    """Format a spec value with optional suffix, or return fallback."""
    if val is None:
        return fallback
    return f"{val:,}{suffix}" if isinstance(val, (int, float)) else f"{val}{suffix}"


def build_specs_table(spec_a, spec_b) -> str:
    """
    Build an HTML comparison table from two VehicleSpecs objects.
    No AI needed — pure data formatting from the database.

    Returns HTML string with a comparison table.
    """
    name_a = f"{spec_a.make} {spec_a.model_name}".strip()
    name_b = f"{spec_b.make} {spec_b.model_name}".strip()
    if spec_a.trim_name:
        name_a += f" {spec_a.trim_name}"
    if spec_b.trim_name:
        name_b += f" {spec_b.trim_name}"

    rows = []

    def add_row(label, val_a, val_b):
        if val_a != 'N/A' or val_b != 'N/A':
            rows.append(f"<tr><td><strong>{label}</strong></td><td>{val_a}</td><td>{val_b}</td></tr>")

    # Body & Type
    add_row("Body Type", _fmt(spec_a.get_body_type_display() if spec_a.body_type else None),
            _fmt(spec_b.get_body_type_display() if spec_b.body_type else None))
    add_row("Fuel Type", _fmt(spec_a.get_fuel_type_display() if spec_a.fuel_type else None),
            _fmt(spec_b.get_fuel_type_display() if spec_b.fuel_type else None))
    add_row("Seats", _fmt(spec_a.seats), _fmt(spec_b.seats))

    # Performance
    add_row("Power", _fmt(spec_a.power_hp, ' HP'), _fmt(spec_b.power_hp, ' HP'))
    add_row("Torque", _fmt(spec_a.torque_nm, ' Nm'), _fmt(spec_b.torque_nm, ' Nm'))
    add_row("0-100 km/h", _fmt(spec_a.acceleration_0_100, 's'), _fmt(spec_b.acceleration_0_100, 's'))
    add_row("Top Speed", _fmt(spec_a.top_speed_kmh, ' km/h'), _fmt(spec_b.top_speed_kmh, ' km/h'))
    add_row("Drivetrain", _fmt(spec_a.drivetrain), _fmt(spec_b.drivetrain))

    # EV / Battery
    add_row("Battery", _fmt(spec_a.battery_kwh, ' kWh'), _fmt(spec_b.battery_kwh, ' kWh'))
    add_row("Range (WLTP)", _fmt(spec_a.range_wltp, ' km'), _fmt(spec_b.range_wltp, ' km'))
    add_row("Range (CLTC)", _fmt(spec_a.range_cltc, ' km'), _fmt(spec_b.range_cltc, ' km'))
    add_row("Range", _fmt(spec_a.range_km, ' km'), _fmt(spec_b.range_km, ' km'))
    add_row("Fast Charging", _fmt(spec_a.charging_time_fast), _fmt(spec_b.charging_time_fast))
    add_row("Max Charging Power", _fmt(spec_a.charging_power_max_kw, ' kW'),
            _fmt(spec_b.charging_power_max_kw, ' kW'))

    # Dimensions
    add_row("Length", _fmt(spec_a.length_mm, ' mm'), _fmt(spec_b.length_mm, ' mm'))
    add_row("Width", _fmt(spec_a.width_mm, ' mm'), _fmt(spec_b.width_mm, ' mm'))
    add_row("Height", _fmt(spec_a.height_mm, ' mm'), _fmt(spec_b.height_mm, ' mm'))
    add_row("Wheelbase", _fmt(spec_a.wheelbase_mm, ' mm'), _fmt(spec_b.wheelbase_mm, ' mm'))
    add_row("Weight", _fmt(spec_a.weight_kg, ' kg'), _fmt(spec_b.weight_kg, ' kg'))
    add_row("Cargo", _fmt(spec_a.cargo_liters, ' L'), _fmt(spec_b.cargo_liters, ' L'))
    add_row("Ground Clearance", _fmt(spec_a.ground_clearance_mm, ' mm'),
            _fmt(spec_b.ground_clearance_mm, ' mm'))

    # Pricing
    price_a = spec_a.get_price_display()
    price_b = spec_b.get_price_display()
    add_row("Price", price_a, price_b)

    # Technical
    add_row("Platform", _fmt(spec_a.platform), _fmt(spec_b.platform))
    add_row("Voltage Architecture", _fmt(spec_a.voltage_architecture, 'V'),
            _fmt(spec_b.voltage_architecture, 'V'))

    if not rows:
        return ""

    table_html = (
        f'<table class="comparison-table">'
        f'<thead><tr><th>Specification</th><th>{name_a}</th><th>{name_b}</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )
    return table_html


def generate_comparison(spec_a, spec_b, provider='gemini') -> dict:
    """
    Generate a comparison article from two VehicleSpecs objects.

    1. Builds specs table from DB data (no AI)
    2. Fetches web context for both vehicles (fact-checking)
    3. AI writes analysis around the data
    4. Full post-processing pipeline

    Returns dict: {title, content, summary, seo_description, slug}
    """
    name_a = f"{spec_a.make} {spec_a.model_name}".strip()
    name_b = f"{spec_b.make} {spec_b.model_name}".strip()

    print(f"🔄 Generating comparison: {name_a} vs {name_b} ({provider})")

    # Step 1: Build specs table from DB
    specs_table = build_specs_table(spec_a, spec_b)
    if not specs_table:
        raise ValueError(f"No spec data available for {name_a} vs {name_b}")

    # Step 2: Web search for context
    web_context_parts = []
    for name, make, model in [(name_a, spec_a.make, spec_a.model_name),
                               (name_b, spec_b.make, spec_b.model_name)]:
        try:
            ctx = search_car_details(make, model)
            if ctx:
                web_context_parts.append(f"--- WEB CONTEXT FOR {name.upper()} ---\n{ctx[:2000]}")
                logger.info(f"[Comparison] Web search for {name}: {len(ctx)} chars")
        except Exception as e:
            logger.warning(f"[Comparison] Web search failed for {name}: {e}")

    web_block = "\n\n".join(web_context_parts) if web_context_parts else ""

    # Step 3: AI prompt — only generates analysis, NOT specs
    body_type = spec_a.get_body_type_display() if spec_a.body_type else 'vehicle'
    fuel_type = spec_a.get_fuel_type_display() if spec_a.fuel_type else ''

    # Build key stats for prompt context
    stats_summary = []
    for n, sp in [(name_a, spec_a), (name_b, spec_b)]:
        parts = [n]
        if sp.power_hp:
            parts.append(f"{sp.power_hp} HP")
        if sp.range_wltp or sp.range_km:
            parts.append(f"{sp.range_wltp or sp.range_km} km range")
        if sp.price_from:
            parts.append(f"from {sp.get_price_display()}")
        stats_summary.append(' | '.join(parts))

    prompt = f"""You are a senior automotive journalist for FreshMotors.net.

Write a COMPARISON article between {name_a} and {name_b} ({fuel_type} {body_type} segment).

VERIFIED SPECIFICATIONS TABLE (from our database — use these exact numbers, DO NOT change them):
{specs_table}

{f'WEB RESEARCH CONTEXT (use for additional insights, reviews, availability info):{chr(10)}{web_block}' if web_block else ''}

{ANTI_INJECTION_NOTICE}

ARTICLE STRUCTURE (output HTML only):
1. <h1> tag: Create a compelling, SEO-optimized title like "{name_a} vs {name_b}: Which {body_type} Wins in 2026?"
2. <h2>Introduction</h2> — Set the context: why these two are compared, target buyer
3. <h2>Design & Dimensions</h2> — Compare exterior/interior if data available
4. <h2>Performance & Powertrain</h2> — Power, acceleration, drivetrain analysis
5. <h2>Battery & Range</h2> — EV range, charging, battery tech (skip for non-EVs)
6. <h2>Pricing & Value</h2> — Price comparison, value proposition
7. <h2>Verdict</h2> — Clear recommendation with reasoning. Who should buy which?

CRITICAL RULES:
1. Use EXACTLY the numbers from the specs table. Do NOT invent or change any specifications.
2. The specs table above will be inserted separately — do NOT recreate it in your article.
3. Write 800-1200 words of analysis text (excluding the table).
4. Output clean HTML only. Use <h2>, <p>, <ul>/<li>, <strong>. No markdown.
5. DO NOT use these banned phrases: "game-changer", "raises the bar", "sets a new standard",
   "redefines", "takes it to the next level", "boasts", "under the hood", "let's dive in",
   "buckle up", "hitting the road", "at the end of the day"
6. Be specific and analytical. Compare actual numbers, not vague statements.
7. Mention both cars' names in the <h1> title.
8. Do NOT include "Source:" or "Disclaimer:" sections.

AFTER the article HTML, on separate lines, write these (NOT inside HTML tags):
SUMMARY: [Write a specific, engaging 2-3 sentence summary that mentions actual specs like power, range, or price. Example: "The {name_a} delivers {spec_a.power_hp or '???'} HP with {spec_a.range_wltp or spec_a.range_km or '???'} km range, while the {name_b} counters with... Both compete in the ??-?? price range." Don't be generic — include numbers!]
SEO_DESCRIPTION: [Write a 120-150 character Google meta description. Must mention both car names and a key differentiator. Example: "Compare {name_a} vs {name_b}: specs, range, pricing and verdict. Which {body_type} is the better buy in 2026?"]

Write the comparison article now:"""

    # Step 4: Generate
    ai = get_ai_provider(provider)
    raw = ai.generate_completion(
        prompt=prompt,
        system_prompt="You are an automotive journalist writing factual comparison articles. Output clean HTML only.",
        temperature=0.65,
        max_tokens=4000,
    )

    if not raw or len(raw) < 200:
        raise ValueError(f"AI returned empty/short response for {name_a} vs {name_b}")

    # Step 5: Extract title
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.IGNORECASE | re.DOTALL)
    if h1_match:
        title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        content = raw[:h1_match.start()] + raw[h1_match.end():]
    else:
        title = f"{name_a} vs {name_b}: Head-to-Head Comparison"
        content = raw

    # Step 6: Extract summary (with better fallback)
    summary_match = re.search(r'SUMMARY:\s*(.+)', raw, re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip()[:250]
        content = re.sub(r'\n*SUMMARY:.*', '', content, flags=re.IGNORECASE).strip()
    else:
        # Fallback with actual specs instead of generic text
        parts = []
        if spec_a.power_hp and spec_b.power_hp:
            parts.append(f"{spec_a.power_hp} HP vs {spec_b.power_hp} HP")
        if (spec_a.range_wltp or spec_a.range_km) and (spec_b.range_wltp or spec_b.range_km):
            r_a = spec_a.range_wltp or spec_a.range_km
            r_b = spec_b.range_wltp or spec_b.range_km
            parts.append(f"{r_a} km vs {r_b} km range")
        detail = f" ({', '.join(parts)})" if parts else ''
        summary = f"Head-to-head comparison of the {name_a} and {name_b}{detail}. Which {fuel_type} {body_type} is the better buy?"

    # Step 7: Clean and insert specs table
    content = re.sub(r'^```html\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content.strip())

    # Insert the DB-sourced specs table after the first <h2> section
    # (so it appears after the introduction)
    first_h2_close = content.find('</h2>')
    if first_h2_close != -1:
        # Find end of the first section (next <h2> or end)
        next_h2 = content.find('<h2', first_h2_close + 5)
        if next_h2 != -1:
            content = content[:next_h2] + specs_table + '\n\n' + content[next_h2:]
        else:
            content = specs_table + '\n\n' + content
    else:
        content = specs_table + '\n\n' + content

    # Step 8: Post-processing
    content = post_process_article(content)

    # Step 9: SEO description — extract from AI output, NOT from table HTML
    seo_match = re.search(r'SEO_DESCRIPTION:\s*(.+)', raw, re.IGNORECASE)
    if seo_match:
        seo_description = seo_match.group(1).strip()[:160]
        content = re.sub(r'\n*SEO_DESCRIPTION:.*', '', content, flags=re.IGNORECASE).strip()
    else:
        # Fallback: build from non-table content
        # Strip the specs table first, then extract text
        content_no_table = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
        content_plain = re.sub(r'<[^>]+>', '', content_no_table).strip()
        seo_description = content_plain[:157].rsplit(' ', 1)[0] + '...' if len(content_plain) > 160 else content_plain

    # Step 10: Slug
    from django.utils.text import slugify
    slug = slugify(f"{spec_a.make}-{spec_a.model_name}-vs-{spec_b.make}-{spec_b.model_name}-comparison")[:200]

    # Word count (from non-table content)
    content_no_table = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.DOTALL)
    content_text = re.sub(r'<[^>]+>', '', content_no_table).strip()
    word_count = len(content_text.split())
    print(f"✅ Comparison generated: {title} ({word_count} words)")

    # Step 11: Get images + photo credit from linked articles
    image_url_a = None
    image_url_b = None
    photo_credit = None
    review_links = []

    for label, spec in [('a', spec_a), ('b', spec_b)]:
        try:
            art = spec.article
            if art:
                # Image URL
                if art.image:
                    if label == 'a':
                        image_url_a = art.image.url
                    else:
                        image_url_b = art.image.url

                    # Photo credit: detect YouTube source
                    if not photo_credit and getattr(art, 'image_source', '') == 'youtube':
                        # Try to find channel name from generation_metadata
                        meta = art.generation_metadata or {}
                        channel = meta.get('source_channel') or meta.get('youtube_channel', '')
                        if not channel:
                            # Try from pending article link
                            try:
                                pending = art.carspecification_set.first()
                                if pending and hasattr(pending, 'pending_article'):
                                    channel = getattr(pending.pending_article, 'youtube_channel', None)
                                    if channel:
                                        channel = str(channel)
                            except Exception:
                                pass
                        if not channel:
                            channel = 'Source'
                        photo_credit = channel

                # Internal link to original review
                if art.is_published and art.slug:
                    spec_name = f"{spec.make} {spec.model_name}"
                    review_links.append({
                        'name': spec_name,
                        'slug': art.slug,
                        'title': art.title,
                    })
        except Exception:
            pass

    # Step 12: Insert photo credit into content
    if photo_credit:
        credit_html = f'<p class="photo-credit" style="font-size: 0.8em; color: #888; margin-top: -8px; margin-bottom: 16px;">Photo: {photo_credit} / YouTube</p>'
        # Insert after specs table
        table_end = content.find('</table>')
        if table_end != -1:
            insert_pos = table_end + len('</table>')
            content = content[:insert_pos] + '\n' + credit_html + content[insert_pos:]

    # Step 13: Append internal links to original reviews
    if review_links:
        links_html = '\n<div class="related-reviews" style="margin-top: 32px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #4f46e5;">'
        links_html += '\n<h3 style="margin-top: 0;">\U0001f4d6 Read Our Full Reviews</h3>'
        links_html += '\n<ul style="margin-bottom: 0;">'
        for link in review_links:
            links_html += f'\n<li><a href="/articles/{link["slug"]}">{link["name"]} — Full Review \u2192</a></li>'
        links_html += '\n</ul>'
        links_html += '\n</div>'
        content += links_html

    return {
        'title': title,
        'content': content,
        'summary': summary,
        'seo_description': seo_description,
        'slug': slug,
        'word_count': word_count,
        'image_url_a': image_url_a,
        'image_url_b': image_url_b,
        'photo_credit': photo_credit,
        'review_links': review_links,
    }
