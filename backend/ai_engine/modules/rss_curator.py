"""
Smart RSS Curator — AI-powered editorial assistant.

Analyses all pending RSS news items in a 4-step pipeline:
  1. Scan:    load new/read RSSNewsItems from last N days
  2. Cluster: group by topic using TF-IDF cosine similarity
  3. Score:   compute FreshMotors Relevance Score (0-100)
  4. Suggest: optional AI summaries for top-scored items

The curator also learns from admin decisions (generate / skip / merge)
stored in CuratorDecisionLog to improve future scoring.
"""

import re
import logging
import hashlib
from collections import Counter
from datetime import timedelta
from typing import Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from django.utils import timezone

logger = logging.getLogger(__name__)

# Scoring weights
_BRAND_BONUS = 25
_TOPIC_BONUS = 15
_SPECS_BONUS = 10
_MULTI_SOURCE_BONUS = 15
_LLM_SCORE_MAX_BONUS = 15
_PREFERENCE_MAX_BONUS = 20
_DUPLICATE_PENALTY = -30
_LOW_EDITORIAL_PENALTY = -10

# Topic keywords that indicate strong FreshMotors relevance
_HIGH_VALUE_PATTERNS = re.compile(
    r'\b(?:new model|all[- ]?new|launch|reveal|unveil|debut|first look|'
    r'electric|ev\b|phev|plug-?in hybrid|battery|range|kwh|charging)\b',
    re.IGNORECASE,
)

# Specs indicators (numbers + automotive units)
_SPECS_PATTERN = re.compile(
    r'\b\d+\s*(?:kWh|km|hp|HP|kW|Nm|mph|kg|mm|seats?|miles?)\b',
    re.IGNORECASE,
)

# Low-editorial topics
_LOW_EDITORIAL_PATTERNS = re.compile(
    r'\b(?:recall(?:s|ed)?|class[- ]action|lawsuit|sales figures|'
    r'q[1-4] results|quarterly|earnings|appoints|ceo|cto)\b',
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """Remove HTML tags."""
    return re.sub(r'<[^>]+>', ' ', text).strip()


def _clean(text: str) -> str:
    """Clean text for TF-IDF."""
    text = _strip_html(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


# ============================================================
# Step 1: Scan
# ============================================================

def _scan_items(days: int = 7):
    """Load pending RSS items from DB."""
    from news.models import RSSNewsItem

    cutoff = timezone.now() - timedelta(days=days)
    return list(
        RSSNewsItem.objects.filter(
            status__in=['new', 'read'],
            created_at__gte=cutoff,
        )
        .select_related('rss_feed')
        .order_by('-created_at')
    )


# ============================================================
# Step 2: Cluster
# ============================================================

def _cluster_items(items: list, threshold: float = 0.45) -> List[List[int]]:
    """
    Cluster RSS items by title+excerpt similarity using TF-IDF + AgglomerativeClustering.

    Returns list of groups, each group is a list of indices into `items`.
    Single-item clusters are kept as-is.
    """
    if len(items) <= 1:
        return [[0]] if items else []

    texts = [_clean(f"{item.title} {item.excerpt}") for item in items]

    vectorizer = TfidfVectorizer(
        max_features=3000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # All texts empty after stop-words removal
        return [[i] for i in range(len(items))]

    # Distance matrix = 1 - cosine_similarity
    sim = cosine_similarity(tfidf_matrix)
    distance = 1 - sim
    np.fill_diagonal(distance, 0)
    distance = np.clip(distance, 0, None)  # numerical safety

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,  # threshold is similarity, not distance
        metric='precomputed',
        linkage='average',
    )

    labels = clustering.fit_predict(distance)

    # Group indices by label
    groups: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        groups.setdefault(int(label), []).append(idx)

    return list(groups.values())


# ============================================================
# Step 3: Score
# ============================================================

def _get_known_brands_set() -> set:
    """Get brand names from DB (cached)."""
    from news.models import Brand
    return set(
        Brand.objects.values_list('name', flat=True)
    )


def _compute_preference_score(item_title: str, item_excerpt: str) -> float:
    """
    Compare RSS item to historically approved items using TF-IDF.
    Returns 0-20 bonus points based on similarity to past approvals.
    """
    from news.models import CuratorDecisionLog

    approved = list(
        CuratorDecisionLog.objects.filter(
            decision__in=['generate', 'merge'],
        ).values_list('title_text', flat=True)[:200]
    )

    if len(approved) < 5:
        return 0  # Not enough training data

    try:
        item_text = _clean(f"{item_title} {item_excerpt}")
        approved_texts = [_clean(t) for t in approved]
        all_texts = approved_texts + [item_text]

        vectorizer = TfidfVectorizer(
            max_features=3000, stop_words='english', ngram_range=(1, 2),
        )
        matrix = vectorizer.fit_transform(all_texts)

        sims = cosine_similarity(matrix[-1:], matrix[:-1]).flatten()
        max_sim = float(sims.max()) if len(sims) > 0 else 0

        if max_sim >= 0.6:
            return _PREFERENCE_MAX_BONUS
        elif max_sim >= 0.3:
            return round((max_sim - 0.3) / 0.3 * _PREFERENCE_MAX_BONUS)
        return 0
    except Exception as e:
        logger.debug(f'Preference scoring failed: {e}')
        return 0


def _check_duplicate(title: str, excerpt: str) -> Optional[dict]:
    """Check if content is too similar to an already-published article."""
    try:
        from news.rss_intelligence import check_semantic_duplicates
        text = _strip_html(f"{title} {excerpt}")
        similar = check_semantic_duplicates(text, threshold=0.65, max_results=1)
        if similar:
            return similar[0]
    except Exception as e:
        logger.debug(f'Duplicate check failed: {e}')
    return None


def _score_item(item, known_brands: set) -> Dict:
    """
    Compute FreshMotors Relevance Score (0-100) for an RSS item.
    Returns dict with total score and breakdown.
    """
    from news.rss_intelligence import extract_brands_from_title

    title = item.title or ''
    excerpt = item.excerpt or ''
    combined = f"{title} {excerpt}"

    breakdown = {}
    total = 0

    # 1. Brand in catalog (+25)
    brands = extract_brands_from_title(title)
    detected_brand = brands[0]['display_name'] if brands else None
    if detected_brand and any(
        b.lower() == detected_brand.lower() for b in known_brands
    ):
        breakdown['brand_match'] = _BRAND_BONUS
        total += _BRAND_BONUS

    # 2. High-value topic (+15)
    if _HIGH_VALUE_PATTERNS.search(combined):
        breakdown['topic_bonus'] = _TOPIC_BONUS
        total += _TOPIC_BONUS

    # 3. Has specs data (+10)
    has_specs = bool(_SPECS_PATTERN.search(combined))
    if has_specs:
        breakdown['specs_data'] = _SPECS_BONUS
        total += _SPECS_BONUS

    # 4. Multi-source (+15)
    sc = getattr(item, 'source_count', 1) or 1
    if sc >= 3:
        breakdown['multi_source'] = _MULTI_SOURCE_BONUS
        total += _MULTI_SOURCE_BONUS
    elif sc == 2:
        breakdown['multi_source'] = 7
        total += 7

    # 5. LLM pre-score (0-15)
    llm = getattr(item, 'llm_score', None)
    if llm is not None and llm > 0:
        llm_bonus = min(round(llm / 100 * _LLM_SCORE_MAX_BONUS), _LLM_SCORE_MAX_BONUS)
        breakdown['llm_score'] = llm_bonus
        total += llm_bonus

    # 6. User preference (0-20)
    pref_bonus = _compute_preference_score(title, excerpt)
    if pref_bonus > 0:
        breakdown['preference'] = pref_bonus
        total += pref_bonus

    # 7. Duplicate penalty (-30)
    dup = _check_duplicate(title, excerpt)
    duplicate_of = None
    if dup:
        breakdown['duplicate_penalty'] = _DUPLICATE_PENALTY
        total += _DUPLICATE_PENALTY
        duplicate_of = dup.get('article_id')

    # 8. Low-editorial penalty (-10)
    if _LOW_EDITORIAL_PATTERNS.search(combined):
        breakdown['low_editorial'] = _LOW_EDITORIAL_PENALTY
        total += _LOW_EDITORIAL_PENALTY

    total = max(0, min(100, total))

    return {
        'score': total,
        'breakdown': breakdown,
        'brand': detected_brand,
        'has_specs': has_specs,
        'duplicate_of': duplicate_of,
    }


# ============================================================
# Step 4: AI Suggest
# ============================================================

def _generate_cluster_summary(cluster_items: list, provider: str = 'gemini') -> dict:
    """
    Ask AI to generate a cluster topic name and editorial suggestion.
    Returns {'topic': str, 'suggestion': str, 'merge_reason': str | None}.
    """
    titles = [item['title'] for item in cluster_items[:5]]
    titles_text = '\n'.join(f'- {t}' for t in titles)

    prompt = f"""You are an automotive news editor for FreshMotors.net (Chinese EVs, new models, tech).

Below are {len(titles)} RSS headlines about the same topic:

{titles_text}

Return JSON (no markdown):
{{
  "topic": "<short cluster topic, 3-6 words, e.g. 'BYD Seal 06 European Launch'>",
  "suggestion": "<1 sentence: why this is worth writing about for FreshMotors audience>",
  "merge_recommended": <true if a combined roundup article would be better than separate articles>
}}"""

    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        import json

        ai = get_ai_provider(provider)
        raw = ai.generate_text(prompt, max_tokens=200, temperature=0.3)

        # Parse JSON from response
        raw = raw.strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)
        return {
            'topic': data.get('topic', titles[0][:50]),
            'suggestion': data.get('suggestion', ''),
            'merge_recommended': data.get('merge_recommended', len(cluster_items) >= 3),
        }
    except Exception as e:
        logger.warning(f'Cluster summary generation failed: {e}')
        # Fallback: use first title as topic
        return {
            'topic': titles[0][:60] if titles else 'Unknown Topic',
            'suggestion': '',
            'merge_recommended': len(cluster_items) >= 3,
        }


# ============================================================
# Main Pipeline
# ============================================================

def curate(
    days: int = 7,
    max_results: int = 20,
    include_ai_summary: bool = True,
    provider: str = 'gemini',
) -> dict:
    """
    Run the 4-step Smart RSS Curator pipeline.

    Returns structured dict with clusters, scores, and recommendations.
    """
    logger.info(f'[Curator] Starting analysis (days={days}, ai={include_ai_summary})')

    # Step 1: Scan
    items = _scan_items(days=days)
    if not items:
        return {
            'success': True,
            'items_scanned': 0,
            'clusters': [],
            'stats': {
                'total_clusters': 0,
                'recommended': 0,
                'skippable': 0,
                'duplicates_found': 0,
            },
        }

    logger.info(f'[Curator] Step 1: Scanned {len(items)} items')

    # Step 2: Cluster
    cluster_groups = _cluster_items(items)
    logger.info(f'[Curator] Step 2: Found {len(cluster_groups)} clusters')

    # Step 3: Score all items
    known_brands = _get_known_brands_set()
    scored_items = {}  # item.id → score_data
    for item in items:
        scored_items[item.id] = _score_item(item, known_brands)

    logger.info(f'[Curator] Step 3: Scored {len(scored_items)} items')

    # Build cluster result objects
    clusters = []
    duplicates_found = 0

    for group_idx, group_indices in enumerate(cluster_groups):
        cluster_id = f'cluster_{group_idx}'

        cluster_items_data = []
        for idx in group_indices:
            item = items[idx]
            score_data = scored_items.get(item.id, {})

            if score_data.get('duplicate_of'):
                duplicates_found += 1

            cluster_items_data.append({
                'id': item.id,
                'title': item.title,
                'excerpt': (item.excerpt or '')[:200],
                'source_url': item.source_url or '',
                'image_url': item.image_url or '',
                'feed_name': item.rss_feed.name if item.rss_feed else '',
                'published_at': item.published_at.isoformat() if item.published_at else None,
                'brand': score_data.get('brand'),
                'score': score_data.get('score', 0),
                'score_breakdown': score_data.get('breakdown', {}),
                'has_specs': score_data.get('has_specs', False),
                'duplicate_of': score_data.get('duplicate_of'),
                'source_count': getattr(item, 'source_count', 1) or 1,
                'llm_score': getattr(item, 'llm_score', None),
                'is_favorite': getattr(item, 'is_favorite', False),
                'ai_summary': '',  # filled in step 4
            })

        # Sort items within cluster by score desc
        cluster_items_data.sort(key=lambda x: x['score'], reverse=True)

        # Max score in cluster determines cluster ranking
        max_score = max((ci['score'] for ci in cluster_items_data), default=0)
        merge_suggested = len(cluster_items_data) >= 2

        clusters.append({
            'id': cluster_id,
            'topic': '',  # filled in step 4
            'items': cluster_items_data,
            'max_score': max_score,
            'merge_suggested': merge_suggested,
            'merge_reason': (
                f'{len(cluster_items_data)} sources covering this topic — consider a roundup article'
                if merge_suggested else ''
            ),
        })

    # Sort clusters by max_score desc
    clusters.sort(key=lambda c: c['max_score'], reverse=True)

    # Trim to max_results
    clusters = clusters[:max_results]

    # Step 4: AI summaries for top clusters
    if include_ai_summary:
        for cluster in clusters[:10]:  # Only top 10 get AI summaries
            ai_result = _generate_cluster_summary(cluster['items'], provider=provider)
            cluster['topic'] = ai_result['topic']

            # Also override merge_suggested if AI says so
            if ai_result.get('merge_recommended'):
                cluster['merge_suggested'] = True

            # Set AI suggestion on the first item
            if cluster['items'] and ai_result.get('suggestion'):
                cluster['items'][0]['ai_summary'] = ai_result['suggestion']
    else:
        # Use detected brand + first title as fallback topic
        for cluster in clusters:
            first = cluster['items'][0] if cluster['items'] else None
            if first:
                brand = first.get('brand') or ''
                title_short = first['title'][:50]
                cluster['topic'] = f"{brand + ': ' if brand else ''}{title_short}"

    logger.info(f'[Curator] Step 4: Generated summaries for {min(len(clusters), 10)} clusters')

    # Stats
    recommended = sum(1 for c in clusters if c['max_score'] >= 60)
    skippable = len(clusters) - recommended

    return {
        'success': True,
        'items_scanned': len(items),
        'clusters': clusters,
        'stats': {
            'total_clusters': len(clusters),
            'recommended': recommended,
            'skippable': skippable,
            'duplicates_found': duplicates_found,
        },
    }
