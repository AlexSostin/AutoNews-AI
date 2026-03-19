"""
RSS Intelligence Module — Extract structured insights from RSS news items.

Features:
  1. Brand Detection: find brand mentions in titles → create Brand(is_visible=False)
  2. Model Discovery: "2026 Honda CR-V" → VehicleSpecs(article=None)
  3. Trending Topics: aggregate brand/topic mentions over time window
  4. Semantic Dedup: embedding similarity check before article generation
"""
import re
import logging
from datetime import timedelta
from collections import Counter
from django.utils import timezone
from django.utils.text import slugify

from news.auto_tags import KNOWN_BRANDS, BRAND_DISPLAY_NAMES

logger = logging.getLogger(__name__)

# Words that follow a brand but are NOT model names
GENERIC_MODEL_WORDS = frozenset({
    # Verbs / actions
    'review', 'reviews', 'preview', 'test', 'drive', 'reveals', 'revealed',
    'launches', 'launched', 'announces', 'announced', 'unveils', 'unveiled',
    'adds', 'added', 'approves', 'became', 'becomes', 'began', 'begins',
    'brings', 'brought', 'calls', 'cancels', 'celebrates', 'changes',
    'completes', 'confirms', 'considers', 'crashes', 'cuts', 'debuts',
    'delivers', 'demands', 'did', 'does', 'drops', 'enters', 'faces',
    'gave', 'goes', 'going', 'got', 'gathered', 'hears', 'hits', 'holds',
    'introduces', 'just', 'leads', 'loses', 'makes', 'need', 'needs',
    'offers', 'overcame', 'overtakes', 'partners', 'plans', 'puts',
    'recalls', 'recall', 'says', 'shows', 'takes', 'tops', 'tracks',
    'updates', 'wants', 'wins', 'won',
    # Pronouns / determiners / prepositions
    'the', 'new', 'all', 'its', 'first', 'also', 'only', 'that', 'this',
    'is', 'to', 'in', 'at', 'on', 'of', 'for', 'and', 'with', 'has',
    'will', 'may', 'could', 'gets', 'aims',
    # People / roles
    'ceo', 'cto', 'boss', 'chief', 'owner', 'owners', 'fans', 'buyers',
    'workers', 'employees', 'brand', 'ambassador',
    # Business / industry
    'factory', 'plant', 'dealer', 'dealers', 'sales', 'price', 'prices',
    'production', 'collaboration', 'alliance', 'annual', 'media',
    # Types — handled elsewhere
    'electric', 'hybrid', 'ev', 'suv', 'sedan', 'coupe', 'truck',
    'pickup', 'van', 'mpv', 'crossover', 'hatchback', 'wagon',
    # Descriptors / noise
    'after', 'bucks', 'clown', 'competitor', 'chip', 'demand',
    'engine', 'exterior', 'following', 'hands-free', 'ingenuity',
    'look', 'na', 'radical', 'rendered', 'run', 'shoe', 'still',
    'team', 'work',
})


# ─────────────────────────────────────────────────────────────────────────────
# Content type classification keywords
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    # High-value: deep editorial content — schedule for generation
    'review': [
        'review', 'test drive', 'first drive', 'road test', 'driven',
        'hands-on', 'deep dive', 'long-term', 'walkaround', 'walk-around',
    ],
    # High-value: new model / reveal — generate article
    'debut': [
        'debut', 'unveil', 'unveiled', 'reveal', 'revealed', 'world premiere',
        'first look', 'spy shots', 'leaked', 'new model', 'all-new',
        'next-gen', 'next generation', 'production version', 'concept',
        'launch', 'launched', 'introduces', 'introduced',
    ],
    # Medium: general news that's still relevant
    'news': [
        'new', 'announce', 'announced', 'update', 'updated', 'facelift',
        'refreshed', 'confirmed', 'price', 'spec', 'specs', 'features',
        'deliveries', 'sales', 'production', 'order', 'preorder',
    ],
    # Low: noise / recall / legal — keep for brand tracking, skip generation
    'noise': [
        'recall', 'lawsuit', 'fine', 'investigation', 'settlement',
        'crash', 'accident', 'fire', 'explosion', 'death', 'injury',
    ],
}


def classify_rss_item(title: str, excerpt: str = '') -> str:
    """
    Classify an RSS news item by content type.

    Returns one of: 'review' | 'debut' | 'news' | 'noise' | 'general'

    Priority order: review > debut > noise > news > general
    """
    text = f'{title} {excerpt}'.lower()

    for content_type in ('review', 'debut', 'noise', 'news'):
        keywords = CONTENT_TYPE_KEYWORDS[content_type]
        if any(kw in text for kw in keywords):
            return content_type

    return 'general'


# ============================================================
# Feature 1: Brand Detection
# ============================================================

def extract_brands_from_title(title: str) -> list[dict]:
    """
    Extract brand mentions from an RSS news item title.
    
    Returns list of dicts:
      [{'brand_key': 'tesla', 'display_name': 'Tesla', 'position': 5}, ...]
    """
    if not title:
        return []
    
    title_lower = title.lower()
    results = []
    
    # Sort by length descending to match "li auto" before "li", "land rover" before "land"
    sorted_brands = sorted(KNOWN_BRANDS, key=len, reverse=True)
    matched_positions = set()  # Avoid overlapping matches
    
    for brand in sorted_brands:
        pattern = rf'\b{re.escape(brand)}\b'
        match = re.search(pattern, title_lower)
        if match:
            start, end = match.start(), match.end()
            # Skip if this position already claimed by a longer brand
            if any(start >= ms and start < me for ms, me in matched_positions):
                continue
            matched_positions.add((start, end))
            display = BRAND_DISPLAY_NAMES.get(brand, brand.title())
            results.append({
                'brand_key': brand,
                'display_name': display,
                'position': start,
            })
    
    return results


def extract_model_from_title(title: str, brand_key: str) -> dict | None:
    """
    Extract a model name from title given a known brand.
    
    Pattern: "... {Brand} {Model} ..." where Model is 1-2 alphanumeric tokens.
    Example: "2026 Honda CR-V Hybrid Review" → {'model': 'CR-V', 'year': 2026}
    
    Returns dict or None.
    """
    if not title or not brand_key:
        return None
    
    title_lower = title.lower()
    
    # Match brand followed by 1-2 words that look like model names
    # Allow hyphens, numbers, and # (e.g., "Model 3", "CR-V", "#7")
    pattern = rf'\b{re.escape(brand_key)}\s+([\w#][\w#-]*(?:\s+[\w#][\w#-]*)?)\b'
    match = re.search(pattern, title_lower, re.IGNORECASE)
    if not match:
        return None
    
    raw_model = match.group(1).strip()
    model_parts = raw_model.split()
    
    # Filter out generic words from the start
    clean_parts = []
    for part in model_parts:
        if part.lower() in GENERIC_MODEL_WORDS:
            break  # Stop at first generic word
        clean_parts.append(part)
    
    if not clean_parts:
        return None
    
    model_name = ' '.join(clean_parts)
    
    # Skip if model is just a single letter
    if len(model_name) <= 1:
        return None
    
    # Extract year from surrounding context
    year_match = re.search(r'\b(202[0-9])\b', title)
    year = int(year_match.group(1)) if year_match else None
    
    # Title-case the model (but keep things like "CR-V", "iX3" as-is)
    if model_name.isalpha() and model_name.islower():
        model_name = model_name.title()
    else:
        # Preserve mixed case like "CR-V", "iX3"
        model_name = model_name.upper() if model_name.isupper() or '-' in model_name else model_name.title()
    
    return {
        'model': model_name,
        'year': year,
    }


# ============================================================
# Feature 1+2: Process RSS items for brand & model intelligence
# ============================================================

def process_rss_intelligence(queryset=None, dry_run=False):
    """
    Scan RSS news item titles for brand and model intelligence.
    
    - Creates Brand(is_visible=False) for newly discovered brands
    - Creates VehicleSpecs(article=None, source='rss_discovery') for new models
    - Returns summary stats
    
    Args:
        queryset: RSSNewsItem queryset (default: all new/read items from last 7 days)
        dry_run: If True, don't create anything, just report findings
    
    Returns:
        dict with stats: brands_found, brands_created, models_found, models_created
    """
    from news.models import RSSNewsItem, Brand, VehicleSpecs, BrandAlias
    
    if queryset is None:
        cutoff = timezone.now() - timedelta(days=7)
        queryset = RSSNewsItem.objects.filter(
            created_at__gte=cutoff,
            status__in=['new', 'read'],
        )
    
    stats = {
        'items_scanned': 0,
        'brands_found': Counter(),     # brand_display_name → count
        'brands_created': [],          # list of new brand names
        'models_found': Counter(),     # "Brand Model" → count
        'models_created': [],          # list of new "Brand Model" strings
    }
    
    for item in queryset.iterator():
        stats['items_scanned'] += 1
        
        brands = extract_brands_from_title(item.title)
        
        for brand_info in brands:
            display_name = brand_info['display_name']
            brand_key = brand_info['brand_key']
            stats['brands_found'][display_name] += 1
            
            if not dry_run:
                # Resolve through aliases first
                resolved = BrandAlias.resolve(display_name)
                
                # Check if brand exists (case-insensitive)
                brand_obj = Brand.objects.filter(name__iexact=resolved).first()
                if not brand_obj:
                    brand_obj = Brand.objects.create(
                        name=resolved,
                        slug=slugify(resolved),
                        is_visible=False,  # Hidden until article exists
                    )
                    stats['brands_created'].append(resolved)
                    logger.info(f'🆕 Created draft brand: {resolved}')
            
            # Try to extract model (tracking only — no VehicleSpecs stub created)
            model_info = extract_model_from_title(item.title, brand_key)
            if model_info and model_info['model']:
                model_label = f"{display_name} {model_info['model']}"
                stats['models_found'][model_label] += 1
                # NOTE: We intentionally do NOT create VehicleSpecs here.
                # Stubs without real specs pollute sibling/predecessor matching.
                # VehicleSpecs are created only when an article is generated
                # and the AI extracts actual technical data.
    
    return stats


# ============================================================
# Feature 3: Trending Topics
# ============================================================

def get_trending_brands(days: int = 7, min_mentions: int = 2) -> list[dict]:
    """
    Get trending brands from RSS news items in the last N days.
    
    Returns sorted list:
      [{'brand': 'Tesla', 'count': 42, 'velocity': 2.1, 'rank': 1}, ...]
    
    velocity = mentions this period / mentions previous period
    """
    from news.models import RSSNewsItem
    
    now = timezone.now()
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    
    # Current period
    current_items = RSSNewsItem.objects.filter(
        created_at__gte=current_start,
    ).values_list('title', flat=True)
    
    current_counts = Counter()
    for title in current_items:
        for brand_info in extract_brands_from_title(title):
            current_counts[brand_info['display_name']] += 1
    
    # Previous period (for velocity calculation)
    previous_items = RSSNewsItem.objects.filter(
        created_at__gte=previous_start,
        created_at__lt=current_start,
    ).values_list('title', flat=True)
    
    previous_counts = Counter()
    for title in previous_items:
        for brand_info in extract_brands_from_title(title):
            previous_counts[brand_info['display_name']] += 1
    
    # Build trending list
    trending = []
    for brand, count in current_counts.most_common():
        if count < min_mentions:
            continue
        
        prev = previous_counts.get(brand, 0)
        velocity = round(count / prev, 1) if prev > 0 else None  # None = "new this period"
        
        trending.append({
            'brand': brand,
            'count': count,
            'previous_count': prev,
            'velocity': velocity,
            'trending_up': count > prev,
        })
    
    # Sort by count descending
    trending.sort(key=lambda x: x['count'], reverse=True)
    
    # Add rank
    for i, item in enumerate(trending, 1):
        item['rank'] = i
    
    return trending


def get_trending_topics(days: int = 7, min_mentions: int = 3) -> list[dict]:
    """
    Get trending topics (non-brand) from RSS titles.
    Extracts fuel types, body types, tech keywords.
    
    Returns: [{'topic': 'EV', 'group': 'Fuel Types', 'count': 15}, ...]
    """
    from news.models import RSSNewsItem
    from news.auto_tags import TAG_ALIASES, TAG_GROUP_MAP
    
    cutoff = timezone.now() - timedelta(days=days)
    titles = RSSNewsItem.objects.filter(
        created_at__gte=cutoff,
    ).values_list('title', flat=True)
    
    topic_counts = Counter()
    
    topic_patterns = {
        r'\belectric\b|\bev\b|\bbev\b': 'EV',
        r'\bhybrid\b': 'Hybrid',
        r'\bphev\b|\bplug-in hybrid\b': 'PHEV',
        r'\bhydrogen\b': 'Hydrogen',
        r'\bsuv\b': 'SUV',
        r'\bsedan\b': 'Sedan',
        r'\bcrossover\b': 'Crossover',
        r'\bautonomous\b|\bself-driving\b': 'Autonomous',
        r'\brecall\b': 'Recall',
        r'\bprice cut\b|\bprice drop\b': 'Price Cut',
        r'\bnew model\b|\ball-new\b|\ball new\b': 'New Model',
        r'\bfast charg\b': 'Fast Charging',
        r'\bsafety\b|\bcrash test\b': 'Safety',
        r'\bsales\b|\bdeliveries\b': 'Sales',
    }
    
    for title in titles:
        title_lower = title.lower()
        for pattern, topic in topic_patterns.items():
            if re.search(pattern, title_lower):
                topic_counts[topic] += 1
    
    results = []
    for topic, count in topic_counts.most_common():
        if count < min_mentions:
            continue
        group = TAG_GROUP_MAP.get(topic, 'Topics')
        results.append({
            'topic': topic,
            'group': group,
            'count': count,
        })
    
    return results


# ============================================================
# Feature 4: Semantic Dedup Check
# ============================================================

def check_semantic_duplicates(text: str, threshold: float = 0.85, max_results: int = 3) -> list[dict]:
    """
    Check if content is semantically similar to existing published articles.
    
    Uses Gemini embeddings + cosine similarity against ArticleEmbedding table.
    
    Args:
        text: Content to check (plain text)
        threshold: Similarity threshold (0.85 = 85%)
        max_results: Max similar articles to return
    
    Returns:
        List of similar articles: [{'article_id': 1, 'title': '...', 'similarity': 0.92}]
    """
    try:
        import numpy as np
        from news.models import ArticleEmbedding
        
        # Generate embedding for new content
        from ai_engine.modules.ai_provider import get_light_provider
        ai = get_light_provider()
        
        # Use first 2000 chars for embedding (same as article indexing)
        text_preview = text[:2000] if text else ''
        if not text_preview or len(text_preview) < 50:
            return []
        
        new_embedding = ai.generate_embedding(text_preview)
        if not new_embedding:
            return []
        
        new_vec = np.array(new_embedding, dtype=np.float32)
        new_norm = np.linalg.norm(new_vec)
        if new_norm == 0:
            return []
        
        # Load recent article embeddings (limit to last 500 for performance)
        embeddings = ArticleEmbedding.objects.select_related('article').order_by(
            '-article__created_at'
        )[:500]
        
        similar = []
        for emb in embeddings:
            stored_vec = np.array(emb.embedding_vector, dtype=np.float32)
            stored_norm = np.linalg.norm(stored_vec)
            if stored_norm == 0:
                continue
            
            # Cosine similarity
            cos_sim = float(np.dot(new_vec, stored_vec) / (new_norm * stored_norm))
            
            if cos_sim >= threshold:
                similar.append({
                    'article_id': emb.article_id,
                    'title': emb.article.title,
                    'similarity': round(cos_sim, 3),
                    'slug': emb.article.slug if hasattr(emb.article, 'slug') else '',
                })
        
        # Sort by similarity descending
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:max_results]
    
    except ImportError:
        logger.warning('numpy not available — skipping semantic dedup check')
        return []
    except Exception as e:
        logger.warning(f'Semantic dedup check failed: {e}')
        return []

