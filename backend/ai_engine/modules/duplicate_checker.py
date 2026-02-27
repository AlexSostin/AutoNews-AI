"""
Duplicate detection for article generation.

Checks if an article already exists by YouTube URL, car make/model,
or pending queue status to prevent creating duplicates.

Policy: We allow multiple articles about the same car model as long as
they are from different videos and spaced at least 3 days apart.
Only exact YouTube URL duplicates are hard-blocked.
"""
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# How many days apart articles about the same car must be
SAME_CAR_COOLDOWN_DAYS = 3


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
    
    existing = Article.objects.filter(youtube_url=youtube_url).first()
    if existing:
        print(f"⚠️  Статья уже существует: {existing.slug} (ID: {existing.id})")
        return existing
    return None


def check_car_duplicate(specs, send_progress=None):
    """
    Check if a RECENT article about the same car (make + model) already exists.
    
    Only blocks if an article about the same car was created within the last
    SAME_CAR_COOLDOWN_DAYS days. Older articles are fine — news sites need fresh content.
    
    Returns a dict with {is_duplicate, reason, existing_id, error} or None if no duplicate.
    
    Checks in order:
    1. CarSpecification for recent, published, non-deleted articles (same make+model)
    2. All recent non-deleted articles by title containing make+model
    3. PendingArticle for same car (status='pending' only)
    """
    car_make = specs.get('make')
    car_model = specs.get('model')
    
    if not car_make or car_make == 'Not specified' or not car_model or car_model == 'Not specified':
        return None
    
    try:
        from news.models import CarSpecification, PendingArticle as PA, Article as ART
        from django.utils import timezone
        
        cutoff = timezone.now() - timedelta(days=SAME_CAR_COOLDOWN_DAYS)
        trim = specs.get('trim', 'Not specified')
        
        # Check 1: CarSpecification for RECENT, PUBLISHED, NON-DELETED articles
        existing = CarSpecification.objects.filter(
            make__iexact=car_make,
            model__iexact=car_model,
            article__is_published=True,
            article__is_deleted=False,
            article__created_at__gte=cutoff,
        )
        if trim and trim != 'Not specified':
            existing = existing.filter(trim__iexact=trim)
        
        if existing.exists():
            article = existing.first().article
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
        
        # Check 2: ALL recent non-deleted articles by title containing make+model
        draft_articles = ART.objects.filter(
            created_at__gte=cutoff,
            is_deleted=False,
        ).filter(
            title__icontains=car_model,
        ).filter(
            title__icontains=car_make,
        )
        if draft_articles.exists():
            article = draft_articles.first()
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
        
        # Check 3: PendingArticle for same car (only status='pending')
        pending_same_car = PA.objects.filter(
            status='pending',
            title__icontains=car_model,
        )
        if car_make:
            pending_same_car = pending_same_car.filter(title__icontains=car_make)
        if pending_same_car.exists():
            pending_art = pending_same_car.first()
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
