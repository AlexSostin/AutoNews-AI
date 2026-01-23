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
            message=f'New comment on "{instance.article.title[:50]}..." by {instance.author}',
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
