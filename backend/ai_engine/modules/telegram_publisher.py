"""
Telegram Auto-Publisher — posts articles to @freshmotors_news channel.

Uses Telegram Bot API (not Telethon) for simplicity and reliability.
Bot token from the FreshMotors Telegram Bot project.

Usage:
    from ai_engine.modules.telegram_publisher import send_to_channel
    send_to_channel(article)  # Article model instance
"""
import re
import logging
import requests
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


def format_telegram_post(article) -> str:
    """
    Format an Article model instance into a beautiful Telegram post.

    Uses Telegram MarkdownV2 formatting for rich text.
    Returns plain text with HTML formatting (Telegram supports HTML in messages).
    """
    title = article.title or 'New Article'
    summary = article.summary or ''
    slug = article.slug or ''
    site_url = getattr(settings, 'SITE_URL', 'https://www.freshmotors.net')
    article_url = f"{site_url}/articles/{slug}"

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
            # Clean tag names for hashtags (remove spaces, special chars)
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
        f"\n\n🔗 <a href=\"{article_url}\">Read full article</a>"
        f"{hashtags}"
    )

    return message


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

    # Try to send with photo if article has an image
    image_url = _get_article_image_url(article)

    if image_url:
        result = _call_api(token, 'sendPhoto', {
            'chat_id': channel,
            'photo': image_url,
            'caption': message,
            'parse_mode': 'HTML',
        })
        # If photo fails (e.g. URL not accessible), fallback to text
        if not result.get('ok'):
            logger.warning(f"📱 Photo send failed, falling back to text-only")
            result = _call_api(token, 'sendMessage', {
                'chat_id': channel,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False,
            })
    else:
        result = _call_api(token, 'sendMessage', {
            'chat_id': channel,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False,
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
                'posted_at': str(article.created_at),
            }
            article.save(update_fields=['generation_metadata'])
        except Exception as e:
            logger.warning(f"Failed to save telegram metadata: {e}")
    else:
        desc = result.get('description', 'Unknown error')
        logger.error(f"📱 Telegram post failed: {desc}")

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


def send_test_message(text: str = "🧪 Test message from FreshMotors bot!") -> dict:
    """Send a test message to verify bot + channel connection."""
    token, channel, _ = _get_config()
    return _call_api(token, 'sendMessage', {
        'chat_id': channel,
        'text': text,
        'parse_mode': 'HTML',
    })
