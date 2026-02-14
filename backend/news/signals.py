"""
Django signals for automatic notification creation.
Creates admin notifications when important events occur.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Comment, Subscriber, Article, PendingArticle, AdminNotification


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
# Force rebuild 1769538478


# ============================================================================
# AUTO-INDEXING SIGNALS FOR VECTOR SEARCH
# ============================================================================

from django.db.models.signals import post_delete
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
    thread.start()


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
    thread.start()


@receiver(post_delete, sender=Article)
def auto_remove_from_vector_index(sender, instance, **kwargs):
    """
    Automatically remove article from vector index when deleted
    """
    _remove_from_vector_async(instance.id, instance.title)


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
        try:
            from news.spec_extractor import extract_specs_from_content, save_specs_for_article
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
        except Exception as e:
            logger.error(f"❌ Auto-spec extraction failed for [{article_id}]: {e}")

    thread = threading.Thread(target=_extract, daemon=True)
    thread.start()
