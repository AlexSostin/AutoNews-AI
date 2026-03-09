"""
Admin Telegram Notifications — FreshMotors
==========================================
Beautiful, informative alerts sent directly to admin's Telegram chat.

All functions call notify_admin_error() under the hood from telegram_publisher.
No separate bot needed — uses the same @freshmotors_bot.

Usage:
    from ai_engine.modules.notify_admin import (
        send_daily_report,
        notify_article_published,
        notify_ai_error,
        notify_system_health,
    )
"""
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('news')


def _send(message: str) -> dict:
    """Send a message to admin chat via telegram_publisher."""
    try:
        from ai_engine.modules.telegram_publisher import notify_admin_error
        return notify_admin_error(message)
    except Exception as e:
        logger.error(f"notify_admin._send failed: {e}")
        return {'ok': False}


def send_daily_report() -> dict:
    """
    📊 Daily Morning Report
    Sent every day at 09:00 UTC via Railway cron.
    Shows yesterday's content stats, top article, and system health.
    """
    try:
        from django.utils import timezone as tz
        from news.models import Article, PendingArticle

        now = tz.now()
        yesterday = now - timedelta(days=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        # Articles published yesterday
        published_yesterday = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=yesterday_start,
            created_at__lt=today_start,
        ).count()

        # Articles published today so far
        published_today = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=today_start,
        ).count()

        # Total published articles
        total_articles = Article.objects.filter(
            is_published=True,
            is_deleted=False,
        ).count()

        # Pending queue
        pending_count = PendingArticle.objects.filter(status='pending').count()

        # Top article yesterday (most viewed)
        top_article = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=yesterday_start,
            created_at__lt=today_start,
        ).order_by('-views').first()

        # Fact-check warnings (articles with unresolved warnings)
        from django.db.models import Q
        warning_count = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            content__contains='ai-fact-check-block',
        ).count()

        # Build message
        date_str = yesterday_start.strftime('%d %b %Y')
        top_line = ''
        if top_article:
            from django.conf import settings
            site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
            article_url = f"{site_url}/articles/{top_article.slug}"
            views_str = f"{top_article.views:,}" if top_article.views else '0'
            top_line = (
                f"\n\n🏆 <b>Top article yesterday:</b>\n"
                f"<a href=\"{article_url}\">{top_article.title[:60]}</a>\n"
                f"👁 {views_str} views"
            )

        warning_line = ''
        if warning_count > 0:
            warning_line = f"\n⚠️ <b>Fact-check warnings:</b> {warning_count} articles need review"

        status_emoji = '🟢' if published_yesterday >= 3 else ('🟡' if published_yesterday >= 1 else '🔴')

        message = (
            f"📊 <b>FreshMotors Daily Report</b>\n"
            f"📅 {date_str}\n"
            f"{'─' * 30}\n\n"
            f"{status_emoji} <b>Published yesterday:</b> {published_yesterday} articles\n"
            f"📝 <b>Published today:</b> {published_today} articles\n"
            f"📚 <b>Total on site:</b> {total_articles:,} articles\n"
            f"⏳ <b>Queue (pending):</b> {pending_count} articles"
            f"{top_line}"
            f"{warning_line}"
        )

        return _send(message)

    except Exception as e:
        logger.error(f"send_daily_report failed: {e}")
        return _send(f"⚠️ <b>Daily report failed</b>\n<code>{e}</code>")


def notify_article_published(article, auto: bool = True) -> dict:
    """
    ✅ Article Published notification
    Called from scheduler when auto-publish happens.
    Shows title, quality score, source type.
    """
    try:
        from django.conf import settings
        site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
        article_url = f"{site_url}/articles/{article.slug}"

        source = '🤖 Auto-published' if auto else '👤 Manually published'
        quality = getattr(article, 'quality_score', None)
        quality_str = f" · Quality: <b>{quality:.0f}/100</b>" if quality else ''

        message = (
            f"✅ <b>Article published!</b>\n\n"
            f"📰 <a href=\"{article_url}\">{article.title[:80]}</a>\n\n"
            f"{source}{quality_str}"
        )
        return _send(message)
    except Exception as e:
        logger.error(f"notify_article_published failed: {e}")
        return {'ok': False}


def notify_telegram_posted(article, msg_id: str) -> dict:
    """
    📱 Telegram post sent notification — lets admin know what went to channel.
    """
    try:
        from django.conf import settings
        site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
        article_url = f"{site_url}/articles/{article.slug}"

        message = (
            f"📱 <b>Posted to Telegram!</b>\n\n"
            f"📰 <a href=\"{article_url}\">{article.title[:70]}</a>\n"
            f"🆔 Message ID: <code>{msg_id}</code>"
        )
        return _send(message)
    except Exception as e:
        logger.error(f"notify_telegram_posted failed: {e}")
        return {'ok': False}


def notify_ai_error(error: str, context: str = '', article_title: str = '') -> dict:
    """
    🚨 AI Generation Error
    Called when article generation fails (quota, network, etc.)
    """
    title_line = f"\n📰 Article: <b>{article_title[:60]}</b>" if article_title else ''
    ctx_line = f"\n📍 Context: <code>{context[:100]}</code>" if context else ''

    message = (
        f"🚨 <b>AI Generation Error</b>"
        f"{title_line}"
        f"{ctx_line}\n\n"
        f"❌ Error:\n<code>{error[:300]}</code>"
    )
    return _send(message)


def notify_quota_exceeded(provider: str = 'gemini') -> dict:
    """🔑 API Quota exceeded — sent once per quota hit."""
    message = (
        f"🔑 <b>Quota exceeded: {provider.upper()}</b>\n\n"
        f"AI generation is paused until quota resets.\n"
        f"⏰ Gemini resets at midnight Pacific Time.\n\n"
        f"💡 <i>No action needed — will auto-resume.</i>"
    )
    return _send(message)


def notify_system_health() -> dict:
    """
    🩺 System Health Check
    Run periodically — checks DB, Redis, pending queue, fact-check warnings.
    """
    try:
        from django.db import connection
        from django.core.cache import cache
        from news.models import Article, PendingArticle

        issues = []
        ok_items = []

        # DB check
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            ok_items.append("✅ Database: OK")
        except Exception as e:
            issues.append(f"❌ Database: {e}")

        # Redis check
        try:
            cache.set('_health_check', '1', 10)
            assert cache.get('_health_check') == '1'
            ok_items.append("✅ Redis: OK")
        except Exception as e:
            issues.append(f"❌ Redis: {e}")

        # Pending queue health
        pending = PendingArticle.objects.filter(status='pending').count()
        if pending > 50:
            issues.append(f"⚠️ Pending queue high: {pending} articles")
        else:
            ok_items.append(f"✅ Pending queue: {pending} articles")

        # Fact-check warnings
        warnings = Article.objects.filter(
            is_published=True,
            content__contains='ai-fact-check-block',
        ).count()
        if warnings > 0:
            issues.append(f"⚠️ Unresolved fact-check warnings: {warnings} articles")

        status_emoji = '🟢' if not issues else '🔴'
        status_text = 'All systems OK' if not issues else f"{len(issues)} issue(s) detected"

        all_lines = ok_items + issues
        details = '\n'.join(all_lines)

        message = (
            f"🩺 <b>System Health</b>\n"
            f"{status_emoji} <b>{status_text}</b>\n"
            f"{'─' * 28}\n"
            f"{details}"
        )
        return _send(message)

    except Exception as e:
        return _send(f"🩺 <b>Health check failed</b>\n<code>{e}</code>")


def notify_no_posts_alert(hours: int = 24) -> dict:
    """⏰ Alert when no articles published in N hours."""
    message = (
        f"⏰ <b>No articles published!</b>\n\n"
        f"🔴 No articles published in the last <b>{hours} hours</b>.\n\n"
        f"Please check:\n"
        f"• Railway backend logs\n"
        f"• RSS/YouTube scanner status\n"
        f"• AI generation quota\n\n"
        f"<i>Check <b>Automation</b> panel on the admin site.</i>"
    )
    return _send(message)
