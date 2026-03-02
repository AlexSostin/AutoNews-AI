"""
Django signals for automatic notification creation.
Creates admin notifications when important events occur.
"""

from django.db.models.signals import post_save
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Comment, Subscriber, Article, PendingArticle, AdminNotification, VehicleSpecs, CarSpecification, TagLearningLog


@receiver(post_save, sender=Comment)
def notify_new_comment(sender, instance, created, **kwargs):
    """Create notification when a new comment is posted"""
    if created:
        AdminNotification.create_notification(
            notification_type='comment',
            title='New Comment',
            message=f'New comment on "{instance.article.title[:50]}..." by {instance.name}',
            link=f'/admin/articles/{instance.article.id}',
            priority='normal'
        )


@receiver(post_save, sender=Subscriber)
def notify_new_subscriber(sender, instance, created, **kwargs):
    """Create notification when a new subscriber joins"""
    if created:
        AdminNotification.create_notification(
            notification_type='subscriber',
            title='New Subscriber',
            message=f'{instance.email} subscribed to the newsletter',
            link='/admin/subscribers',
            priority='normal'
        )


@receiver(post_save, sender=Article)
def notify_new_article(sender, instance, created, **kwargs):
    """Create notification when a new article is published"""
    if created:
        AdminNotification.create_notification(
            notification_type='article',
            title='New Article Published',
            message=f'"{instance.title[:50]}..." has been published',
            link=f'/admin/articles/{instance.id}',
            priority='low'
        )


@receiver(post_save, sender=PendingArticle)
def notify_pending_article(sender, instance, created, **kwargs):
    """Create notification when a new video is pending review"""
    if created:
        AdminNotification.create_notification(
            notification_type='video_pending',
            title='Video Pending Review',
            message=f'New video "{instance.title[:50]}..." is waiting for review',
            link='/admin/youtube-channels/pending',
            priority='high'
        )
    elif instance.status == 'error':
        AdminNotification.create_notification(
            notification_type='video_error',
            title='Video Processing Error',
            message=f'Error processing video "{instance.title[:50]}..."',
            link='/admin/youtube-channels/pending',
            priority='high'
        )


# ============================================================================
# HUMAN REVIEW LEARNING SIGNAL
# Logs approve/reject decisions on auto-drafted articles for ML training.
# ============================================================================

@receiver(post_save, sender=Article)
def log_human_review_decision(sender, instance, created, **kwargs):
    """
    When an auto-drafted article is toggled published, log as 'human_approved'.
    This builds a labeled dataset: what the user approves vs rejects.
    """
    if created:
        return  # Only care about updates, not initial creation
    
    # Check if this article came from auto-publish (has a source_pending with is_auto_published=True)
    source = instance.source_pending.filter(is_auto_published=True).first()
    if not source:
        return  # Not an auto-drafted article, skip
    
    # Check if is_published just changed to True (draft → published = human approved)
    if instance.is_published and not instance.is_deleted:
        from .models import AutoPublishLog
        # Only log once — check if already logged
        if AutoPublishLog.objects.filter(
            published_article=instance,
            decision='human_approved'
        ).exists():
            return
        
        # Calculate review time (from draft creation to now)
        review_seconds = None
        if instance.created_at:
            from django.utils import timezone
            review_seconds = int((timezone.now() - instance.created_at).total_seconds())
        
        AutoPublishLog.objects.create(
            pending_article=source,
            published_article=instance,
            decision='human_approved',
            reason=f'Draft approved by admin (reviewed in {review_seconds}s)' if review_seconds else 'Draft approved by admin',
            quality_score=source.quality_score or 0,
            safety_score=getattr(source.rss_feed, 'safety_score', '') if source.rss_feed else '',
            feed_name=source.rss_feed.name if source.rss_feed else ('YouTube' if source.video_url else 'Unknown'),
            source_type=source.rss_feed.source_type if source.rss_feed else ('youtube' if source.video_url else ''),
            article_title=instance.title[:500],
            content_length=len(instance.content or ''),
            has_image=bool(instance.image),
            has_specs=hasattr(instance, 'car_specification'),
            tag_count=instance.tags.count(),
            category_name=instance.categories.first().name if instance.categories.exists() else '',
            source_is_youtube=bool(source.video_url),
            review_time_seconds=review_seconds,
        )
        import logging
        logging.getLogger('news').info(
            f"[LEARNING] ✅ Human approved: {instance.title[:50]} "
            f"(Q:{source.quality_score}, reviewed in {review_seconds}s)"
        )


# ============================================================================
# TAG LEARNING SIGNAL
# Records title→tags mapping when articles are published/updated.
# ============================================================================

@receiver(post_save, sender=Article)
def learn_tag_choices(sender, instance, **kwargs):
    """Record tag choices for the learning system whenever a published article is saved."""
    if not instance.is_published or instance.is_deleted:
        return
    
    # Run in background to avoid blocking
    article_id = instance.id
    
    def _record():
        try:
            from ai_engine.modules.tag_suggester import record_tag_choice
            article = Article.objects.get(id=article_id)
            record_tag_choice(article)
        except Exception as e:
            import logging
            logging.getLogger('news').error(f"[TAG-LEARN] Failed to record tags for [{article_id}]: {e}")
    
    thread = threading.Thread(target=_record, daemon=True)
    transaction.on_commit(lambda: thread.start())


# ============================================================================
# AUTO-INDEXING SIGNALS FOR VECTOR SEARCH
# ============================================================================

import logging
import threading

logger = logging.getLogger(__name__)


def _remove_from_vector_async(article_id, title=""):
    """Remove article from vector index in background thread (non-blocking)"""
    def _remove():
        try:
            from ai_engine.modules.vector_search import get_vector_engine
            engine = get_vector_engine()
            engine.remove_article(article_id)
            logger.info(f"🗑️ Removed article from vector index: {title} (ID: {article_id})")
        except Exception as e:
            logger.error(f"Failed to remove article {article_id} from vector index: {e}")
    
    thread = threading.Thread(target=_remove, daemon=True)
    transaction.on_commit(lambda: thread.start())


@receiver(post_save, sender=Article)
def auto_index_article_vector(sender, instance, created, **kwargs):
    """
    Automatically index article for vector search when saved
    Only indexes published, non-deleted articles
    """
    # Only index published articles
    if not instance.is_published or instance.is_deleted:
        # If article was unpublished/deleted, remove from index
        if not created:
            _remove_from_vector_async(instance.id, instance.title)
        return
    
    # Index the article in background thread
    def _index():
        try:
            from ai_engine.modules.vector_search import get_vector_engine
            
            engine = get_vector_engine()
            
            # Prepare metadata
            metadata = {
                'slug': instance.slug,
                'is_published': instance.is_published,
                'created_at': instance.created_at.isoformat() if instance.created_at else None,
            }
            
            # Add categories
            if instance.categories.exists():
                metadata['categories'] = [cat.slug for cat in instance.categories.all()]
            
            # Add tags
            if instance.tags.exists():
                metadata['tags'] = [tag.slug for tag in instance.tags.all()]
            
            # Index the article
            engine.index_article(
                article_id=instance.id,
                title=instance.title,
                content=instance.content,
                summary=instance.summary or "",
                metadata=metadata
            )
            
            action = "📊 Indexed" if created else "🔄 Re-indexed"
            logger.info(f"{action} article for vector search: {instance.title} (ID: {instance.id})")
            
        except Exception as e:
            logger.error(f"Failed to auto-index article {instance.id} for vector search: {e}")
    
    thread = threading.Thread(target=_index, daemon=True)
    transaction.on_commit(lambda: thread.start())


@receiver(post_delete, sender=Article)
def auto_remove_from_vector_index(sender, instance, **kwargs):
    """
    Automatically remove article from vector index when deleted
    """
    _remove_from_vector_async(instance.id, instance.title)


# ============================================================================
# AUTO-REBUILD TF-IDF CONTENT RECOMMENDER
# Rebuilds local ML model when articles change (debounced via Redis)
# ============================================================================

@receiver(post_save, sender=Article)
def rebuild_content_recommender(sender, instance, **kwargs):
    """Rebuild TF-IDF model when a published article is saved (debounced 5 min)."""
    if not instance.is_published or instance.is_deleted:
        return
    
    def _rebuild():
        try:
            from django.core.cache import cache
            lock_key = 'content_recommender_rebuild_lock'
            if cache.get(lock_key):
                return  # Already rebuilt recently
            cache.set(lock_key, True, timeout=300)  # 5 min debounce
            
            from ai_engine.modules.content_recommender import build
            result = build()
            if result.get('success') and not result.get('skipped'):
                logger.info(f"🧠 Content Recommender rebuilt: {result.get('article_count')} articles")
        except Exception as e:
            logger.error(f"❌ Content Recommender rebuild failed: {e}")
    
    thread = threading.Thread(target=_rebuild, daemon=True)
    transaction.on_commit(lambda: thread.start())

# ============================================================================
# AUTO-CREATE CAR SPECIFICATIONS ON ARTICLE PUBLISH
# ============================================================================

@receiver(post_save, sender=Article)
def auto_create_car_specs(sender, instance, **kwargs):
    """
    Automatically create CarSpecification when an article is published
    and doesn't have one yet. Uses AI to extract specs from content.
    Runs in background thread to avoid blocking the save.
    """
    # Only process published, non-deleted articles
    if not instance.is_published or instance.is_deleted:
        return

    # Skip if article already has a CarSpecification
    from news.models import CarSpecification
    if CarSpecification.objects.filter(article=instance).exists():
        return

    # Skip known non-car articles
    from news.spec_extractor import SKIP_ARTICLE_IDS
    if instance.id in SKIP_ARTICLE_IDS:
        return

    # Run AI extraction in background thread
    article_id = instance.id

    def _extract():
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from news.spec_extractor import extract_specs_from_content, save_specs_for_article
                # Re-check in case specs were created between signal fire and thread start
                if CarSpecification.objects.filter(article_id=article_id).exists():
                    logger.info(f"ℹ️ Specs already exist for [{article_id}], skipping")
                    return
                article = Article.objects.get(id=article_id)
                specs = extract_specs_from_content(article)
                if specs and specs.get('make') and specs['make'] != 'Not specified':
                    result = save_specs_for_article(article, specs)
                    if result:
                        logger.info(f"🚗 Auto-created CarSpecification for [{article_id}] {result.make} {result.model}")
                    else:
                        logger.warning(f"⚠️ Could not save specs for [{article_id}]")
                else:
                    logger.info(f"ℹ️ No car specs extracted for [{article_id}] (not a car article?)")
                return  # Success - exit retry loop
            except Exception as e:
                error_str = str(e)
                if '429' in error_str and attempt < max_retries - 1:
                    wait = 30 * (attempt + 1)  # 30s, 60s, 90s
                    logger.warning(f"⏳ Gemini rate limit for [{article_id}], retry in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                else:
                    logger.error(f"❌ Auto-spec extraction failed for [{article_id}]: {e}")
                    return

    thread = threading.Thread(target=_extract, daemon=True)
    transaction.on_commit(lambda: thread.start())


# ============================================================================
# SYNC VEHICLE SPECS → CAR SPECIFICATION (CATALOG)
# ============================================================================

@receiver(post_save, sender=VehicleSpecs)
def sync_vehicle_specs_to_car_spec(sender, instance, **kwargs):
    """
    When VehicleSpecs is saved, auto-create/update CarSpecification
    so the car appears in the /cars catalog.
    Only syncs if VehicleSpecs has an article linked.
    """
    if not instance.article:
        return

    # Build update fields from VehicleSpecs
    updates = {}

    if instance.make:
        # Resolve brand aliases + sub-brand extraction
        # e.g. 'DongFeng VOYAH' → 'VOYAH' (simple alias)
        # e.g. make='BYD', model='Denza D9' → make='DENZA', model='D9' (sub-brand rule)
        from .models import BrandAlias
        model_name = instance.model_name or ''
        resolved_make, resolved_model = BrandAlias.resolve_with_model(instance.make, model_name)
        updates['make'] = resolved_make
        # Also normalize the VehicleSpecs make/model if alias was resolved
        vs_updates = {}
        if resolved_make != instance.make:
            vs_updates['make'] = resolved_make
        if resolved_model != model_name:
            vs_updates['model_name'] = resolved_model
            updates['model'] = resolved_model
        if vs_updates:
            VehicleSpecs.objects.filter(pk=instance.pk).update(**vs_updates)
            logger.info(f"🏷️ Resolved brand: '{instance.make} {model_name}' → '{resolved_make} {resolved_model}'")
    if instance.model_name:
        updates['model'] = instance.model_name
    if instance.trim_name:
        updates['trim'] = instance.trim_name
    if instance.drivetrain:
        updates['drivetrain'] = instance.drivetrain

    # Engine description from fuel_type + battery
    engine_parts = []
    if instance.fuel_type:
        engine_parts.append(instance.fuel_type)
    if instance.battery_kwh:
        engine_parts.append(f"{instance.battery_kwh} kWh")
    if instance.drivetrain:
        engine_parts.append(instance.drivetrain)
    if engine_parts:
        updates['engine'] = ' / '.join(engine_parts)

    if instance.power_hp:
        updates['horsepower'] = f"{instance.power_hp} HP"
    if instance.torque_nm:
        updates['torque'] = f"{instance.torque_nm} Nm"
    if instance.acceleration_0_100:
        updates['zero_to_sixty'] = f"{instance.acceleration_0_100}s"
    if instance.top_speed_kmh:
        updates['top_speed'] = f"{instance.top_speed_kmh} km/h"
    if instance.price_from:
        currency = instance.currency or ''
        price_str = f"{instance.price_from:,} {currency}".strip()
        if instance.price_to and instance.price_to != instance.price_from:
            price_str = f"{instance.price_from:,} - {instance.price_to:,} {currency}".strip()
        # Add USD estimate if available and currency is not USD
        extra = instance.extra_specs or {}
        if currency != 'USD' and extra.get('price_usd_est'):
            price_str = f"${extra['price_usd_est']:,} (est.) / {price_str}"
        updates['price'] = price_str

    if not updates.get('make'):
        return  # No make = nothing useful to sync

    # model_name for CarSpec (legacy full name)
    model_name = f"{updates.get('make', '')} {updates.get('model', '')}".strip()
    if instance.trim_name:
        model_name += f" {instance.trim_name}"

    try:
        # Check if CarSpec exists and has a locked make
        existing = CarSpecification.objects.filter(article=instance.article).first()
        if existing and existing.is_make_locked:
            # Don't overwrite make/model/model_name — admin manually set these
            updates.pop('make', None)
            updates.pop('model', None)
            model_name = None  # Don't overwrite
            logger.info(f"🔒 Make locked for [{instance.article_id}] — skipping make/model overwrite")

        if model_name:
            defaults = {'model_name': model_name, **updates}
        else:
            defaults = {**updates}

        car_spec, created = CarSpecification.objects.update_or_create(
            article=instance.article,
            defaults=defaults,
        )
        action = "Created" if created else "Updated"
        logger.info(f"🔄 {action} CarSpecification for article [{instance.article_id}] from VehicleSpecs")
    except Exception as e:
        logger.error(f"❌ Failed to sync VehicleSpecs → CarSpecification for article [{instance.article_id}]: {e}")


# ============================================================================
# AUTO-SYNC CARSPECIFICATION FIELDS → ARTICLE TAGS
# ============================================================================

@receiver(post_save, sender=CarSpecification)
def sync_car_spec_tags(sender, instance, **kwargs):
    """
    When CarSpecification is saved, auto-add relevant tags to the article:
    - Drivetrain (AWD/FWD/RWD/4WD) from specs.drivetrain
    This catches drivetrain data regardless of source (AI, admin edit, VehicleSpecs sync).
    """
    try:
        from .models import Tag
        article = instance.article
        
        # --- Drivetrain tag ---
        dt = (instance.drivetrain or '').strip().upper()
        if dt in ('AWD', 'FWD', 'RWD', '4WD'):
            # Check if article already has a drivetrain tag
            existing_dt_tags = article.tags.filter(
                group__name='Drivetrain'
            )
            if not existing_dt_tags.exists():
                # Find the tag in DB
                tag = Tag.objects.filter(
                    group__name='Drivetrain',
                    name__iexact=dt
                ).first()
                if tag:
                    article.tags.add(tag)
                    logger.info(f"🏷️ Auto-synced drivetrain tag '{dt}' to article [{article.id}]")
                else:
                    logger.warning(f"⚠️ Drivetrain tag '{dt}' not found in DB")
    except Exception as e:
        logger.error(f"❌ Failed to sync CarSpec tags for article: {e}")
