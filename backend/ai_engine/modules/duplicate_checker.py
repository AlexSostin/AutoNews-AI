"""
Duplicate detection for article generation.

Checks if an article already exists by YouTube URL, car make/model,
or pending queue status to prevent creating duplicates.

Policy: We allow multiple articles about the same car model as long as
they are from different videos and spaced at least 3 days apart.
Only exact YouTube URL duplicates are hard-blocked.

Trim awareness: "BYD Tang DM-p" and "BYD Tang PHEV 7-seater" are
DIFFERENT cars and should NOT block each other. We only block if the
trims are clearly the same (or both unknown).
"""
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# How many days apart articles about the same car must be
SAME_CAR_COOLDOWN_DAYS = 3

# Trim keywords that indicate different powertrain/tier variants.
# If two articles share NONE of these keywords (or share the SAME ones), they conflict.
# If they have DIFFERENT keywords → different variant → allow.
TRIM_VARIANT_KEYWORDS = [
    'dm-p', 'dm-i', 'dm-s', 'dm-o',        # BYD DM family
    'phev', 'hev', 'mhev', 'rev',            # Hybrid types
    'ev', 'bev', 'fcev',                      # Electric types
    'ice', 'petrol', 'diesel',                # ICE types
    '4wd', 'awd', 'rwd', 'fwd',              # Drivetrain
    'pro', 'plus', 'ultra', 'max',            # Tier suffixes
    'long range', 'standard range',           # Range variants
    '6-seater', '7-seater', '5-seater',      # Seating config
    'walk-around', 'walkaround', 'review',   # Video type (helps distinguish)
]


import re as _re


def _extract_trim_keywords(text: str) -> set:
    """Extract variant-distinguishing keywords from a title or trim string.
    Uses word-boundary matching so 'ev' does NOT match inside 'rev' or 'preview'.
    """
    text_lower = (text or '').lower()
    found = set()
    for kw in TRIM_VARIANT_KEYWORDS:
        # Escape special regex chars (e.g. hyphens in 'dm-p')
        pattern = r'(?<![a-z0-9])' + _re.escape(kw) + r'(?![a-z0-9])'
        if _re.search(pattern, text_lower):
            found.add(kw)
    return found


def _trims_conflict(new_trim: str, new_title: str,
                    existing_trim: str, existing_title: str) -> bool:
    """
    Return True if the two car entries appear to be the SAME trim variant
    (i.e., they should be considered duplicates of each other).

    Rules:
    - Both have variant keywords AND they are disjoint → False (different variants, allow)
    - Neither has any variant keywords → True (conservative, block — same unknown trim)
    - Overlapping keywords → True (same variant, block)
    """
    new_kw = _extract_trim_keywords(new_trim) | _extract_trim_keywords(new_title)
    ex_kw = _extract_trim_keywords(existing_trim) | _extract_trim_keywords(existing_title)

    if new_kw and ex_kw and new_kw.isdisjoint(ex_kw):
        # Both sides have distinct variant markers → clearly different cars
        return False

    return True  # Same variant (or no variant info to distinguish) → conflict


def check_duplicate(youtube_url):
    """
    Check if we already have an article from this YouTube video URL.
    Returns the existing Article instance or None.
    """
    import django
    import sys
    import os
    if not django.apps.apps.ready:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
        django.setup()

    from news.models import Article

    existing = Article.objects.filter(youtube_url=youtube_url, is_deleted=False).first()
    if existing:
        print(f"⚠️  Статья уже существует: {existing.slug} (ID: {existing.id})")
        return existing
    return None


def check_car_duplicate(specs, send_progress=None, exclude_article_id=None):
    """
    Check if a RECENT article about the same car (make + model + trim) already exists.

    Only blocks if an article about the same car AND same trim variant was created
    within the last SAME_CAR_COOLDOWN_DAYS days.
    Different trims (e.g. DM-p vs PHEV 7-seater) are treated as separate articles.

    Returns a dict with {is_duplicate, reason, existing_id, error} or None if no duplicate.

    Checks in order:
    1. CarSpecification — recent published non-deleted articles (same make+model+trim)
    2. Article title   — recent non-deleted articles containing make+model (trim-aware)
    3. PendingArticle  — status='pending', same make+model in title (trim-aware)
    """
    car_make = specs.get('make')
    car_model = specs.get('model')

    if not car_make or car_make == 'Not specified' or not car_model or car_model == 'Not specified':
        return None

    new_trim = specs.get('trim') or ''
    # Prefer an explicit title from specs; fall back to make+model+trim
    new_title = specs.get('title') or f"{car_make} {car_model} {new_trim}".strip()

    try:
        from news.models import CarSpecification, PendingArticle as PA, Article as ART
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=SAME_CAR_COOLDOWN_DAYS)
        trim = specs.get('trim', 'Not specified')

        # ── Check 1: CarSpecification (published articles) ────────────────────────
        existing_specs = CarSpecification.objects.filter(
            make__iexact=car_make,
            model__iexact=car_model,
            article__is_published=True,
            article__is_deleted=False,
            article__created_at__gte=cutoff,
        )
        if exclude_article_id:
            existing_specs = existing_specs.exclude(article_id=exclude_article_id)
        if trim and trim != 'Not specified':
            existing_specs = existing_specs.filter(trim__iexact=trim)

        for spec in existing_specs:
            article = spec.article
            if not _trims_conflict(new_trim, new_title, spec.trim or '', article.title):
                print(f"ℹ️ Same make/model but different trim — allowing: "
                      f"{car_make} {car_model} | new={new_trim!r} vs existing={spec.trim!r}")
                continue
            msg = (f"⚠️ Duplicate detected: {car_make} {car_model} "
                   f"already exists (Article #{article.id}: \"{article.title}\", "
                   f"created {article.created_at:%Y-%m-%d}) — cooldown {SAME_CAR_COOLDOWN_DAYS}d")
            print(msg)
            if send_progress:
                send_progress(4, 100, f"⚠️ Skipped — duplicate of article #{article.id}")
            return {
                'is_duplicate': True, 'reason': 'duplicate',
                'existing_article_id': article.id, 'error': msg,
            }

        # ── Check 2: Article title search (includes drafts) ───────────────────────
        draft_articles = ART.objects.filter(
            created_at__gte=cutoff,
            is_deleted=False,
            title__icontains=car_model,
        ).filter(title__icontains=car_make)
        if exclude_article_id:
            draft_articles = draft_articles.exclude(id=exclude_article_id)

        for article in draft_articles:
            if not _trims_conflict(new_trim, new_title, '', article.title):
                print(f"ℹ️ Same make/model but different trim in article title — allowing: "
                      f"#{article.id} \"{article.title}\"")
                continue
            msg = (f"⚠️ Duplicate detected: {car_make} {car_model} "
                   f"already exists as article (#{article.id}: \"{article.title}\", "
                   f"created {article.created_at:%Y-%m-%d}) — cooldown {SAME_CAR_COOLDOWN_DAYS}d")
            print(msg)
            if send_progress:
                send_progress(4, 100, f"⚠️ Skipped — duplicate of article #{article.id}")
            return {
                'is_duplicate': True, 'reason': 'duplicate',
                'existing_article_id': article.id, 'error': msg,
            }

        # ── Check 3: PendingArticle queue ─────────────────────────────────────────
        pending_same_car = PA.objects.filter(
            status='pending',
            title__icontains=car_model,
        )
        if car_make:
            pending_same_car = pending_same_car.filter(title__icontains=car_make)

        for pending_art in pending_same_car:
            if not _trims_conflict(new_trim, new_title, '', pending_art.title):
                print(f"ℹ️ Same make/model but different trim in pending queue — allowing: "
                      f"#{pending_art.id} \"{pending_art.title}\"")
                continue
            msg = (f"⚠️ Duplicate detected: {car_make} {car_model} "
                   f"already pending (PendingArticle #{pending_art.id}: \"{pending_art.title}\")")
            print(msg)
            if send_progress:
                send_progress(4, 100, f"⚠️ Skipped — same car already pending #{pending_art.id}")
            return {
                'is_duplicate': True, 'reason': 'duplicate_pending',
                'existing_pending_id': pending_art.id, 'error': msg,
            }

    except Exception as e:
        print(f"⚠️ Duplicate check failed (continuing anyway): {e}")

    return None
