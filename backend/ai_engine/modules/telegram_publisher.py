"""
Telegram Auto-Publisher — posts articles to @freshmotors_news channel.

Uses Telegram Bot API (not Telethon) for simplicity and reliability.
Bot token from the FreshMotors Telegram Bot project.

Usage:
    from ai_engine.modules.telegram_publisher import send_to_channel
    send_to_channel(article)  # Article model instance

Features:
    - UTM tracking on all article links (utm_source=telegram)
    - Inline keyboard button "Read full article →"
    - Error notifications to admin chat
    - Daily alert if no articles posted in 24h
"""
import re
import logging
import requests
from datetime import datetime, timezone, timedelta
from django.conf import settings

logger = logging.getLogger('news')

# Telegram Bot API base URL
BOT_API = 'https://api.telegram.org/bot{token}/{method}'


def _get_config():
    """Get Telegram configuration from Django settings."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    channel = getattr(settings, 'TELEGRAM_CHANNEL_ID', '')
    auto_post = getattr(settings, 'TELEGRAM_AUTO_POST', False)

    if not token:
        raise ValueError('TELEGRAM_BOT_TOKEN not configured in settings')
    if not channel:
        raise ValueError('TELEGRAM_CHANNEL_ID not configured in settings')

    return token, channel, auto_post


def _get_admin_id() -> str:
    """Get admin Telegram user ID for error/alert notifications."""
    return getattr(settings, 'TELEGRAM_ADMIN_ID', '')


def _call_api(token: str, method: str, data: dict) -> dict:
    """Make a Telegram Bot API call."""
    url = BOT_API.format(token=token, method=method)
    try:
        resp = requests.post(url, json=data, timeout=15)
        result = resp.json()
        if not result.get('ok'):
            logger.error(f"Telegram API error: {result.get('description', 'Unknown')}")
        return result
    except requests.RequestException as e:
        logger.error(f"Telegram API request failed: {e}")
        return {'ok': False, 'description': str(e)}


def _build_utm_url(article_url: str, medium: str = 'post') -> str:
    """
    Add UTM parameters to article URL for analytics tracking.
    utm_source=telegram tracks all traffic from Telegram.
    utm_medium distinguishes post vs button clicks.
    """
    separator = '&' if '?' in article_url else '?'
    return f"{article_url}{separator}utm_source=telegram&utm_medium={medium}&utm_campaign=channel"


def format_telegram_post(article) -> str:
    """
    Format an Article model instance into a beautiful Telegram post.

    Uses HTML formatting (Telegram supports HTML in messages).
    Article URL includes UTM parameters for analytics tracking.
    """
    title = article.title or 'New Article'
    summary = article.summary or ''
    slug = article.slug or ''
    site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
    article_url = f"{site_url}/articles/{slug}"
    # UTM link in post text (utm_medium=post)
    article_url_utm = _build_utm_url(article_url, medium='post')

    # Build specs line from CarSpecification if available
    specs_line = ''
    try:
        spec = article.carspecification
        parts = []
        if spec.range_km:
            parts.append(f"⚡ Range: {spec.range_km} km")
        elif spec.range_miles:
            parts.append(f"⚡ Range: {spec.range_miles} mi")
        if spec.horsepower:
            parts.append(f"🐎 {spec.horsepower} hp")
        if spec.price:
            price = str(spec.price).replace('$', '').strip()
            parts.append(f"💰 ${price}")
        elif spec.price_from:
            parts.append(f"💰 From ${spec.price_from}")
        if spec.zero_to_sixty:
            parts.append(f"🏎 0-60: {spec.zero_to_sixty}s")
        if parts:
            specs_line = '\n\n' + ' | '.join(parts)
    except Exception:
        pass

    # Build hashtags from tags
    hashtags = ''
    try:
        tags = list(article.tags.values_list('name', flat=True)[:5])
        if tags:
            clean_tags = []
            for tag in tags:
                clean = re.sub(r'[^a-zA-Z0-9]', '', tag.title())
                if clean and len(clean) > 1:
                    clean_tags.append(f"#{clean}")
            if clean_tags:
                hashtags = '\n\n' + ' '.join(clean_tags[:5])
    except Exception:
        pass

    # Trim summary to ~300 chars for Telegram
    if len(summary) > 300:
        summary = summary[:297] + '...'

    # Compose message with HTML formatting
    message = (
        f"🚗 <b>{_escape_html(title)}</b>\n\n"
        f"{_escape_html(summary)}"
        f"{specs_line}"
        f"\n\n🔗 <a href=\"{article_url_utm}\">Read full article</a>"
        f"{hashtags}"
    )

    return message


def _build_inline_keyboard(article_url: str) -> dict:
    """
    Build an inline keyboard with a 'Read full article →' button.
    Button URL uses utm_medium=button to distinguish from text link clicks.
    This appears below the post in the Telegram channel.
    """
    button_url = _build_utm_url(article_url, medium='button')
    return {
        'inline_keyboard': [[
            {'text': '📰 Read full article →', 'url': button_url}
        ]]
    }


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML mode."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def send_to_channel(article, force: bool = False) -> dict:
    """
    Send an article to the Telegram channel.

    Args:
        article: Article model instance
        force: If True, send even if TELEGRAM_AUTO_POST is False

    Returns:
        dict with 'ok', 'message_id', and other Telegram response data
    """
    token, channel, auto_post = _get_config()

    if not force and not auto_post:
        logger.info(f"📱 Telegram auto-post disabled. Use --force or enable TELEGRAM_AUTO_POST.")
        return {'ok': False, 'reason': 'auto_post_disabled'}

    message = format_telegram_post(article)

    site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
    article_url = f"{site_url}/articles/{article.slug or ''}"
    reply_markup = _build_inline_keyboard(article_url)

    # Try to send with photo if article has an image
    image_url = _get_article_image_url(article)

    if image_url:
        result = _call_api(token, 'sendPhoto', {
            'chat_id': channel,
            'photo': image_url,
            'caption': message,
            'parse_mode': 'HTML',
            'reply_markup': reply_markup,
        })
        # If photo fails (e.g. URL not accessible), fallback to text
        if not result.get('ok'):
            logger.warning(f"📱 Photo send failed, falling back to text-only")
            result = _call_api(token, 'sendMessage', {
                'chat_id': channel,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False,
                'reply_markup': reply_markup,
            })
    else:
        result = _call_api(token, 'sendMessage', {
            'chat_id': channel,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False,
            'reply_markup': reply_markup,
        })

    if result.get('ok'):
        msg_id = result.get('result', {}).get('message_id', '?')
        logger.info(f"📱 Telegram: posted to {channel} (msg_id={msg_id})")

        # Save telegram post info in generation_metadata
        try:
            if article.generation_metadata is None:
                article.generation_metadata = {}
            article.generation_metadata['telegram_post'] = {
                'message_id': msg_id,
                'channel': channel,
                'posted_at': datetime.now(timezone.utc).isoformat(),
            }
            article.save(update_fields=['generation_metadata'])
        except Exception as e:
            logger.warning(f"Failed to save telegram metadata: {e}")
    else:
        # Notify admin about the failure
        desc = result.get('description', 'Unknown error')
        logger.error(f"📱 Telegram post failed: {desc}")
        notify_admin_error(
            f"❌ <b>Telegram post failed</b>\n\n"
            f"Article: <b>{_escape_html(article.title or 'unknown')}</b>\n"
            f"Error: <code>{_escape_html(desc)}</code>"
        )

    return result


def _get_article_image_url(article) -> str:
    """Get the best image URL for the article."""
    try:
        if article.image:
            img = str(article.image)
            # Cloudinary URLs are already absolute
            if img.startswith('http'):
                return img
            # Local file — construct URL
            site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
            return f"{site_url}/media/{img}"
    except Exception:
        pass
    return ''


def notify_admin_error(message: str) -> dict:
    """
    Send an error notification directly to the admin's Telegram chat.
    Used for AI errors, failed posts, and critical alerts.

    Args:
        message: HTML-formatted error message
    """
    try:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        admin_id = _get_admin_id()
        if not token or not admin_id:
            logger.warning("Telegram admin notification skipped — token or admin_id not set")
            return {'ok': False, 'reason': 'no_admin_config'}

        return _call_api(token, 'sendMessage', {
            'chat_id': admin_id,
            'text': message,
            'parse_mode': 'HTML',
        })
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
        return {'ok': False, 'description': str(e)}


def check_and_alert_no_posts(hours: int = 24) -> bool:
    """
    Check if no articles have been posted to Telegram in the last N hours.
    If so, send an alert to the admin.

    Intended for use in a periodic task (e.g. daily cron / Celery beat).
    Returns True if alert was sent.
    """
    try:
        from news.models import Article

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Articles created in the last N hours
        recent_count = Article.objects.filter(
            created_at__gte=since,
            published=True,
        ).count()

        if recent_count == 0:
            msg = (
                f"⚠️ <b>FreshMotors Alert</b>\n\n"
                f"No articles have been published in the last <b>{hours} hours</b>.\n\n"
                f"Please check the AI generation pipeline."
            )
            notify_admin_error(msg)
            logger.warning(f"📱 Alert sent: no articles in last {hours}h")
            return True

        return False
    except Exception as e:
        logger.error(f"check_and_alert_no_posts failed: {e}")
        return False


def send_test_message(text: str = "🧪 Test message from FreshMotors bot!") -> dict:
    """Send a test message to verify bot + channel connection."""
    token, channel, _ = _get_config()
    return _call_api(token, 'sendMessage', {
        'chat_id': channel,
        'text': text,
        'parse_mode': 'HTML',
    })
