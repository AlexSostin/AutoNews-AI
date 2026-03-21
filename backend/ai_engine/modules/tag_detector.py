"""
Automatic technology tag detection and HTML injection.

- _auto_add_drivetrain_tag: add drivetrain tag from specs (AWD/FWD/RWD/4WD).
- _auto_add_tech_tags: scan article HTML for technology keywords and add tags.
- _inject_tech_highlights: inject visual 'Key Technologies' block into article HTML.
"""
import re
import logging

logger = logging.getLogger(__name__)


def _auto_add_drivetrain_tag(specs: dict, tag_names: list) -> None:
    """Auto-add drivetrain tag (AWD/FWD/RWD/4WD) if present in specs and not yet tagged."""
    drivetrain = specs.get('drivetrain')
    if drivetrain and drivetrain not in ('Not specified', '', None):
        dt_upper = drivetrain.upper()
        has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
        if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
            tag_names.append(dt_upper)
            print(f"🏷️ Auto-added drivetrain tag: {dt_upper}")


# ── Keyword-based Tech & Features auto-tagger ──────────────────────────
# Maps: tag_name → list of keyword patterns (case-insensitive) to search in article HTML.
# If ANY keyword matches in the article text, the tag is added.
# All patterns are checked against plain text (HTML tags stripped).
_TECH_TAG_RULES: list[tuple[str, list[str]]] = [
    # ── Driving Assistance ──
    ('ADAS',           ['adas', 'advanced driver assist', 'driver assistance system',
                        'pilot assist', 'autopilot', 'co-pilot', 'highway pilot',
                        'city pilot', 'urban pilot', 'noa', 'navigate on autopilot']),
    ('LiDAR',          ['lidar', 'laser radar', 'laser-based', 'laser sensor',
                        'roof-mounted sensor', 'roof-mounted lidar']),
    ('Adaptive Cruise', ['adaptive cruise', 'acc ', 'intelligent cruise',
                         'smart cruise', 'traffic-aware cruise']),
    ('Lane Assist',    ['lane assist', 'lane keep', 'lane departure', 'lane centering',
                        'lane change assist', 'lka', 'lca']),
    ('Parking Assist', ['parking assist', 'auto park', 'remote park', 'self-park',
                        'autonomous parking', 'apa ', 'valet parking']),
    ('Self-Driving',   ['self-driving', 'self driving', 'autonomous driving',
                        'level 3', 'level 4', 'l3 autonomous', 'l4 autonomous',
                        'full self-driving', 'fsd']),
    ('Radar',          ['radar sensor', 'millimeter wave radar', 'mmwave radar',
                        'corner radar', '4d radar', '4d imaging radar']),
    ('Sensors',        ['ultrasonic sensor', 'surround view', '360 camera',
                        '360-degree camera', 'bird.s eye', 'bird.s-eye']),
    ('Camera',         ['dash cam', 'dashcam', 'driving recorder', 'hdr camera',
                        'surround camera', 'rear camera', 'cabin camera']),
    ('Night Vision',   ['night vision', 'infrared', 'thermal camera',
                        'thermal imaging']),
    # ── Charging & Battery ──
    ('Fast Charging',  ['fast charg', 'dc fast', 'supercharg', 'ultra-fast charg',
                        'rapid charg', '800v', '800 v architecture',
                        'ccs2', 'chademo', 'nacs', '150 kw', '200 kw', '250 kw',
                        '300 kw', '350 kw', '400 kw', '500 kw',
                        '10% to 80%', '10-80%', '30 minutes', '20 minutes',
                        '15 minutes', '18 minutes']),
    ('Charging',       ['charg', 'ac charg', 'home charg', 'wall box', 'wallbox',
                        'level 2', 'type 2', 'on-board charger', 'obc',
                        'v2l', 'v2g', 'vehicle-to-load', 'vehicle-to-grid',
                        'bidirectional charg']),
    ('Battery',        ['battery pack', 'kwh', 'kilo.?watt.?hour', 'lfp',
                        'blade battery', 'nmc', 'ncm', 'cell-to-pack',
                        'cell-to-body', 'cell-to-chassis', 'catl',
                        'solid.state battery', 'sodium.ion', 'qilin battery']),
    ('Long-Range',     ['long.range', '1[,.]?[0-9]00.{0,5}km', '800.{0,5}km',
                        '700.{0,5}km', '600.{0,5}km', '500.{0,5}km',
                        '400.{0,3}mile']),
    # ── Drive & Performance ──
    ('Performance',    ['launch control', 'track mode', 'sport mode',
                        'drift mode', 'race mode', 'performance mode',
                        'nürburgring', 'nurburgring']),
    ('Supercharged',   ['supercharg']),
    ('Turbo',          ['turbo', 'turbocharg']),
    ('Twin-Turbo',     ['twin.turbo', 'bi.turbo', 'biturbo']),
    # ── Cockpit & Infotainment ──
    ('Digital Cockpit', ['digital cockpit', 'digital instrument', 'virtual cockpit',
                         'digital cluster', 'digital dashboard', 'head-up display',
                         'hud', 'ar.hud', 'augmented reality display',
                         'floating display', 'oled display', 'mini.led display']),
    ('Infotainment',   ['infotainment', 'touchscreen', 'entertainment system',
                        'android auto', 'carplay', 'apple carplay',
                        'spotify', 'karaoke', 'rear entertainment']),
    ('CarPlay',        ['carplay', 'apple carplay']),
    ('Android Auto',   ['android auto']),
    ('Connected Car',  ['connected car', 'connected service', 'ota', 'over-the-air',
                        'remote control', 'smart summon', 'remote summon',
                        'digital key', 'nfc key', 'uwb key', 'bluetooth key',
                        'phone as key', 'smartphone key']),
    ('OTA Update',     ['ota update', 'over-the-air update', 'software update',
                        'firmware update', 'ota upgrade']),
    ('AI',             ['artificial intelligence', 'machine learning', 'neural network',
                        'ai-powered', 'ai powered', 'large language model',
                        'voice assistant', 'gpt', 'chatgpt', 'in-car ai']),
    # ── Comfort & Interior ──
    ('Interior',       ['nappa leather', 'alcantara', 'massaging seat', 'massage seat',
                        'ventilated seat', 'heated seat', 'cooled seat',
                        'panoramic roof', 'panoramic sunroof', 'starlight',
                        'ambient light', 'zero gravity seat', 'reclining seat']),
    ('Climate',        ['heat pump', 'dual.zone climate', 'tri.zone climate',
                        'four.zone climate', 'pre.conditioning', 'fragrance system',
                        'air purif', 'pm2.5', 'hvac']),
    # ── Safety ──
    ('Safety',         ['airbag', 'ncap', 'collision avoid', 'emergency braking',
                        'aeb ', 'blind spot', 'cross traffic', 'child safety',
                        'isofix', 'automatic emergency', 'rollover protect',
                        'pedestrian detection', 'cyclist detection']),
    # ── Fuel Economy ──
    ('Fuel Economy',   ['fuel economy', 'fuel efficiency', 'fuel consumption',
                        'l/100', 'liters per 100', 'mpg', 'miles per gallon',
                        'wltp consumption', 'nedc consumption',
                        'low fuel consumption']),
    # ── Aero & Design ──
    ('Aerodynamics',   ['aerodynamic', 'drag coefficient', 'cd 0.', 'cx 0.',
                        'active aero', 'active spoiler', 'active grille']),
    # ── Advanced Tech ──
    ('Solid State',    ['solid.state batter', 'solid state batter']),
]


def _auto_add_tech_tags(article_html: str, tag_names: list, specs: dict) -> None:
    """
    Auto-add Tech & Features tags by scanning the generated article HTML
    for technology keywords. Modifies tag_names in place.

    Called AFTER article generation so we scan the actual article content,
    not the raw analysis (which often lacks tech details).
    """
    # Strip HTML tags → plain text for keyword matching
    plain = re.sub(r'<[^>]+>', ' ', article_html).lower()

    # Also include specs for extra signals
    specs_text = ' '.join(str(v) for v in specs.values() if v).lower()
    combined_text = plain + ' ' + specs_text

    existing_lower = {t.lower() for t in tag_names}
    added = []

    for tag_name, keywords in _TECH_TAG_RULES:
        # Skip if already present
        if tag_name.lower() in existing_lower:
            continue

        for kw in keywords:
            # Treat keywords with regex chars as regex patterns
            if any(c in kw for c in r'.?*+[](){}|\\'):
                try:
                    if re.search(kw, combined_text):
                        tag_names.append(tag_name)
                        existing_lower.add(tag_name.lower())
                        added.append(tag_name)
                        break
                except re.error:
                    continue
            else:
                if kw in combined_text:
                    tag_names.append(tag_name)
                    existing_lower.add(tag_name.lower())
                    added.append(tag_name)
                    break

    if added:
        print(f"🏷️ Auto-added {len(added)} Tech & Features tag(s): {', '.join(added)}")


# ── Tech Highlights descriptions for article injection ──────────────────
# Maps tag_name → (icon, short user-facing description)
_TECH_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    'ADAS':            ('🛡️', 'Advanced driver assistance — automatic lane-keeping, collision avoidance, and traffic monitoring'),
    'LiDAR':           ('📡', 'Laser-based 3-D environment scanning for centimeter-accurate obstacle detection'),
    'Adaptive Cruise': ('🚗', 'Radar/camera cruise control that adjusts speed to traffic automatically'),
    'Lane Assist':     ('🛤️', 'Active lane centering keeps the car within lane markings hands-on'),
    'Parking Assist':  ('🅿️', 'Automated parking — the car steers itself into parallel or perpendicular spots'),
    'Self-Driving':    ('🤖', 'Autonomous driving capability — the car can navigate some routes without driver input'),
    'Radar':           ('📡', 'Millimeter-wave radar sensors for all-weather object detection'),
    'Sensors':         ('👁️', '360° surround-view cameras and ultrasonic sensors for spatial awareness'),
    'Camera':          ('📷', 'Multi-camera system for recording, monitoring, and visual ADAS'),
    'Night Vision':    ('🌙', 'Infrared or thermal imaging that detects pedestrians and animals in darkness'),
    'Fast Charging':   ('⚡', 'DC fast charging support — replenish 10→80 % in under 30 minutes'),
    'Charging':        ('🔌', 'Plug-in charging capability — home AC or public station compatible'),
    'Battery':         ('🔋', 'High-capacity traction battery with advanced cell chemistry'),
    'Long-Range':      ('🛣️', 'Extended driving range that eliminates range anxiety for long trips'),
    'Performance':     ('🏁', 'Sport-tuned driving modes — launch control, track settings, or drift mode'),
    'Turbo':           ('💨', 'Turbocharged engine — forced induction for higher output from a smaller displacement'),
    'Twin-Turbo':      ('💨', 'Twin-turbo setup — two turbochargers for minimal lag and maximum boost'),
    'Supercharged':    ('💨', 'Supercharged engine — belt-driven compressor for instant throttle response'),
    'Digital Cockpit': ('🖥️', 'Fully digital instrument cluster and head-up display for at-a-glance data'),
    'Infotainment':    ('📱', 'Central touchscreen infotainment with apps, navigation, and media streaming'),
    'CarPlay':         ('🍎', 'Apple CarPlay integration for seamless iPhone mirroring'),
    'Android Auto':    ('🤖', 'Android Auto integration for Google Maps, calls, and media from your phone'),
    'Connected Car':   ('📶', 'Always-connected services — remote control, OTA updates, and digital key'),
    'OTA Update':      ('🔄', 'Over-the-air software updates — new features delivered without a dealer visit'),
    'AI':              ('🧠', 'On-board AI engine powering voice assistant, route planning, or autonomous features'),
    'Interior':        ('💺', 'Premium cabin materials — ventilated or massaging seats, panoramic roof, ambient lighting'),
    'Climate':         ('❄️', 'Multi-zone climate control with heat pump for efficient cabin temperature management'),
    'Safety':          ('🦺', 'Active safety suite — AEB, blind-spot monitoring, and collision avoidance'),
    'Fuel Economy':    ('⛽', 'Optimized fuel efficiency — low consumption per 100 km for cost-effective driving'),
    'Aerodynamics':    ('🌀', 'Wind-tunnel-optimized body with low drag coefficient for better range and stability'),
    'Solid State':     ('⚗️', 'Next-gen solid-state battery — higher density, faster charging, and improved safety'),
    'V2L':             ('🏕️', "Vehicle-to-Load — power external devices directly from the car's battery"),
}


def _inject_tech_highlights(article_html: str, tech_tags: list[str]) -> str:
    """
    Inject a 'Key Technologies' visual block into the article HTML.

    The block is placed right after the 'Technology & Features' <h2> heading.
    If that heading isn't found, a standalone section is inserted before
    'Pricing & Availability' or 'Pros & Cons'.

    Args:
        article_html: Generated article HTML.
        tech_tags: List of detected tech tag names (from _auto_add_tech_tags).

    Returns:
        Modified HTML with tech-highlights block injected.
    """
    if not tech_tags:
        return article_html

    # Guard: require minimum article length to avoid polluting fallback/stub articles.
    # A proper generated article is always > 2000 chars of HTML; skip injection
    # on short/minimal content where the block would dominate the summary.
    plain_text_len = len(re.sub(r'<[^>]+>', '', article_html))
    if plain_text_len < 800:
        print(f"  ⏭️ Tech highlights: skipped (article too short: {plain_text_len} chars)")
        return article_html
    items = []
    for tag in tech_tags:
        desc = _TECH_DESCRIPTIONS.get(tag)
        if desc:
            icon, explanation = desc
            items.append((icon, tag, explanation))

    if not items:
        return article_html

    # Limit to 8 most relevant (avoid overwhelming the reader)
    items = items[:8]

    # Build HTML
    badges_html = '\n'.join(
        f'<div class="tech-item">'
        f'<span class="tech-icon">{icon}</span>'
        f'<div class="tech-info">'
        f'<span class="tech-name">{name}</span>'
        f'<span class="tech-desc">{desc}</span>'
        f'</div></div>'
        for icon, name, desc in items
    )

    block = (
        f'<div class="tech-highlights">\n'
        f'<div class="tech-highlights-label">KEY TECHNOLOGIES</div>\n'
        f'<div class="tech-grid">\n{badges_html}\n</div>\n'
        f'</div>\n'
    )

    # Strategy 1: Insert after "Technology & Features" h2 and its first <p>
    tech_h2 = re.search(
        r'(<h2[^>]*>.*?(?:Technology|Features|Tech).*?</h2>\s*(?:<p>.*?</p>\s*)?)',
        article_html, re.IGNORECASE | re.DOTALL
    )
    if tech_h2:
        insert_pos = tech_h2.end()
        article_html = article_html[:insert_pos] + '\n' + block + article_html[insert_pos:]
        print(f"  🔧 Tech highlights: injected {len(items)} items after 'Technology & Features'")
        return article_html

    # Strategy 2: Insert before Pricing or Pros & Cons
    for fallback_keyword in ['Pricing', 'Pros', 'How It Compares']:
        fallback_h2 = re.search(
            rf'<h2[^>]*>.*?{fallback_keyword}.*?</h2>',
            article_html, re.IGNORECASE
        )
        if fallback_h2:
            insert_pos = fallback_h2.start()
            section_heading = '<h2>Key Technologies</h2>\n'
            article_html = article_html[:insert_pos] + section_heading + block + '\n' + article_html[insert_pos:]
            print(f"  🔧 Tech highlights: injected {len(items)} items before '{fallback_keyword}'")
            return article_html

    # Strategy 3: Append before closing content
    article_html = article_html.rstrip() + '\n' + '<h2>Key Technologies</h2>\n' + block
    print(f"  🔧 Tech highlights: appended {len(items)} items at end")
    return article_html
