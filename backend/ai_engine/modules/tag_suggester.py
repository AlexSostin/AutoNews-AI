"""
Tag Learning System — learns from user's tag choices to suggest tags for new articles.

Phase 1 (now): Keyword-based matching from historical data
Phase 2 (future): TF-IDF + cosine similarity
Phase 3 (future): Fine-tuned classifier

How it works:
1. When user publishes an article with tags, we record: title_keywords → tags
2. When new PendingArticle is created, we extract keywords from title
3. We find historical articles with similar keywords  
4. We return the most frequently used tags for those keywords, weighted by overlap
"""
import re
import logging
from collections import Counter

logger = logging.getLogger('news')

# Common stop words to ignore in titles
STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'and', 'but',
    'or', 'nor', 'not', 'so', 'yet', 'for', 'of', 'in', 'on', 'at', 'to',
    'by', 'up', 'out', 'off', 'over', 'into', 'with', 'from', 'than',
    'that', 'this', 'these', 'those', 'it', 'its', 'we', 'our', 'you',
    'your', 'they', 'their', 'what', 'which', 'who', 'whom', 'how', 'why',
    'when', 'where', 'new', 'all', 'just', 'first', 'also', 'more', 'most',
    'very', 'really', 'already', 'still', 'here', 'now', 'review',
}

# Year pattern (2020-2030)
YEAR_PATTERN = re.compile(r'\b(20[2-3]\d)\b')

# Known body type keywords that map to tag names
BODY_TYPE_KEYWORDS = {
    'suv': 'SUV', 'crossover': 'SUV', 'cuv': 'SUV',
    'sedan': 'Sedan', 'saloon': 'Sedan',
    'coupe': 'Coupe', 'coupé': 'Coupe',
    'hatchback': 'Hatchback', 'hatch': 'Hatchback',
    'wagon': 'Wagon', 'estate': 'Wagon', 'touring': 'Wagon',
    'pickup': 'Pickup', 'truck': 'Pickup',
    'van': 'Van', 'minivan': 'MPV', 'mpv': 'MPV',
    'convertible': 'Convertible', 'roadster': 'Convertible', 'cabriolet': 'Convertible',
    'supercar': 'Supercar', 'hypercar': 'Supercar',
    'fastback': 'Fastback',
}

# Powertrain keywords
POWERTRAIN_KEYWORDS = {
    'electric': 'Electric', 'ev': 'EV', 'bev': 'EV',
    'hybrid': 'Hybrid', 'phev': 'Plug-in Hybrid', 'plug-in': 'Plug-in Hybrid',
    'hydrogen': 'Hydrogen', 'fcev': 'Hydrogen',
    'diesel': 'Diesel',
    'v8': 'V8', 'v6': 'V6', 'v10': 'V10', 'v12': 'V12',
    'turbo': 'Turbo', 'turbocharged': 'Turbo',
    'awd': 'AWD', '4wd': '4WD', 'rwd': 'RWD', 'fwd': 'FWD',
}


def extract_keywords(title):
    """Extract meaningful keywords from an article title.
    
    Returns a set of lowercase keywords (brands, years, body types, etc.)
    """
    if not title:
        return set()
    
    # Normalize
    title_lower = title.lower()
    
    # Extract words
    words = re.findall(r'[a-zA-Z0-9\-]+', title_lower)
    
    # Filter stop words and short words
    keywords = set()
    for word in words:
        if word in STOP_WORDS or len(word) < 2:
            continue
        keywords.add(word)
    
    # Also extract years
    years = YEAR_PATTERN.findall(title)
    keywords.update(years)
    
    return keywords


def suggest_tags(title, max_suggestions=8):
    """Suggest tags for a new article based on historical patterns.
    
    Returns list of tag name strings, ordered by confidence.
    """
    from news.models import TagLearningLog, Tag
    
    keywords = extract_keywords(title)
    if not keywords:
        return []
    
    # Strategy 1: Direct keyword → tag matches (body types, powertrain)
    direct_tags = set()
    title_lower = title.lower()
    
    for keyword, tag_name in {**BODY_TYPE_KEYWORDS, **POWERTRAIN_KEYWORDS}.items():
        # Use word-boundary to avoid 'ev' matching 'rev', 'v8' matching 'tv80' etc.
        if re.search(r'\b' + re.escape(keyword) + r'\b', title_lower):
            direct_tags.add(tag_name)
    
    # Strategy 2: Brand matching - check if any keyword matches a Manufacturers tag
    manufacturer_tags = Tag.objects.filter(
        group__name='Manufacturers'
    ).values_list('name', flat=True)
    
    manufacturer_map = {m.lower(): m for m in manufacturer_tags}
    
    # Check extracted keywords against brand names (exact match)
    for keyword in keywords:
        if keyword in manufacturer_map:
            direct_tags.add(manufacturer_map[keyword])
    
    # Also check for compound brand names using word-boundary regex
    # (prevents "seat" in "6-seater", "ev" in "rev", etc.)
    for brand_lower, brand_name in manufacturer_map.items():
        # Skip short brand names (≤3 chars) that were already checked as keywords
        if len(brand_lower) <= 3:
            continue
        # Use word-boundary regex for longer brand names
        pattern = r'\b' + re.escape(brand_lower) + r'\b'
        if re.search(pattern, title_lower):
            direct_tags.add(brand_name)
    
    # Strategy 3: Historical pattern matching
    # Find learning logs where keywords overlap with our new title
    historical_tags = Counter()
    
    all_logs = TagLearningLog.objects.all().only(
        'title_keywords', 'final_tags'
    )
    
    for log in all_logs:
        log_keywords = set(log.title_keywords) if log.title_keywords else set()
        
        # Calculate keyword overlap (Jaccard-like)
        overlap = keywords & log_keywords
        if not overlap:
            continue
        
        # Weight by overlap ratio
        weight = len(overlap) / max(len(keywords), len(log_keywords))
        
        # Only consider if meaningful overlap (at least 2 keywords match
        # or overlap ratio > 0.3)
        if len(overlap) < 2 and weight < 0.3:
            continue
        
        # Add tags weighted by overlap
        for tag_name in (log.final_tags or []):
            historical_tags[tag_name] += weight
    
    # Combine: direct matches get highest weight
    combined = Counter()
    for tag in direct_tags:
        combined[tag] = 10.0  # High confidence for direct matches
    
    for tag, weight in historical_tags.items():
        combined[tag] += weight
    
    # Get the top suggestions
    suggestions = [tag for tag, _ in combined.most_common(max_suggestions)]
    
    # Filter to only tags that actually exist in DB
    existing_tags = set(Tag.objects.filter(
        name__in=suggestions
    ).values_list('name', flat=True))
    
    final = [t for t in suggestions if t in existing_tags]
    
    logger.info(
        f"[TAG-SUGGEST] '{title[:50]}' → keywords={list(keywords)[:10]} → "
        f"direct={list(direct_tags)} historical={len(historical_tags)} → "
        f"suggestions={final}"
    )
    
    return final


def record_tag_choice(article):
    """Record the title→tags mapping from a published article for learning.
    
    Called when user publishes/approves an article.
    """
    from news.models import TagLearningLog
    
    keywords = list(extract_keywords(article.title))
    tag_names = list(article.tags.values_list('name', flat=True))
    
    if not keywords or not tag_names:
        return
    
    # Update or create (one record per article)
    log, created = TagLearningLog.objects.update_or_create(
        article=article,
        defaults={
            'title': article.title[:500],
            'title_keywords': keywords,
            'final_tags': tag_names,
        }
    )
    
    action = "Recorded" if created else "Updated"
    logger.info(
        f"[TAG-LEARN] {action}: '{article.title[:50]}' → {tag_names}"
    )
    return log
