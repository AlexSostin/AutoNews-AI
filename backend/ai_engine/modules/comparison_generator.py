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
8. After the article, on a NEW LINE write: SUMMARY: [2-3 sentence comparison summary for cards]
9. Do NOT include "Source:" or "Disclaimer:" sections.

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

    # Step 6: Extract summary
    summary = f"{name_a} vs {name_b} — a detailed comparison of specs, performance, and value."
    summary_match = re.search(r'SUMMARY:\s*(.+)', raw, re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip()[:250]
        content = re.sub(r'\n*SUMMARY:.*$', '', content, flags=re.IGNORECASE | re.MULTILINE).strip()

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

    # Step 9: SEO description
    content_plain = re.sub(r'<[^>]+>', '', content).strip()
    seo_description = content_plain[:157].rsplit(' ', 1)[0] + '...' if len(content_plain) > 160 else content_plain

    # Step 10: Slug
    from django.utils.text import slugify
    slug = slugify(f"{spec_a.make}-{spec_a.model_name}-vs-{spec_b.make}-{spec_b.model_name}-comparison")[:200]

    word_count = len(content_plain.split())
    print(f"✅ Comparison generated: {title} ({word_count} words)")

    return {
        'title': title,
        'content': content,
        'summary': summary,
        'seo_description': seo_description,
        'slug': slug,
        'word_count': word_count,
    }
