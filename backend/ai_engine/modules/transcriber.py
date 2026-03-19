import os
import re
import time
import requests
import logging

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _get_video_info_fallback(youtube_url):
    """
    Get basic video info using oEmbed if yt-dlp is blocked.
    This is less likely to be blocked but only gives title and author.
    """
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={youtube_url}&format=json"
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title'),
                'author': data.get('author_name'),
                'channel': data.get('author_name'),
                'description': 'Description not available via oEmbed'
            }
    except Exception as e:
        print(f"⚠️ oEmbed fallback failed: {e}")
    return None


# ══════════════════════════════════════════════════════════════════
#  Tier 1: youtube-transcript-api (free, no API key, no cookies)
# ══════════════════════════════════════════════════════════════════

def _fetch_via_transcript_api(video_id: str) -> str | None:
    """
    Fetch transcript using youtube-transcript-api v1.2.4+.
    Instance-based API: api.fetch(video_id, languages=[...]).
    Most reliable method — no CAPTCHA, no cookies needed.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        preferred_langs = ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant', 'de', 'fr', 'es']

        # Try fetching with preferred languages (lib picks best match)
        transcript = None
        try:
            transcript = api.fetch(video_id, languages=preferred_langs)
        except Exception as e:
            # If no preferred lang found, try fetching ANY available transcript
            err_str = str(e)
            if 'NoTranscript' in err_str or 'not find' in err_str:
                try:
                    transcript_list = api.list(video_id)
                    available = list(transcript_list)
                    if available:
                        # Fetch the first available transcript
                        transcript = api.fetch(video_id, languages=[available[0].language_code])
                except Exception:
                    pass
            else:
                raise

        if not transcript:
            return None

        # Extract text from snippets
        text_parts = [seg.text for seg in transcript.snippets if seg.text.strip()]
        full_text = ' '.join(text_parts)

        # Clean up common artifacts
        full_text = re.sub(r'\[.*?\]', '', full_text)  # Remove [Music], [Applause] etc.
        full_text = ' '.join(full_text.split())  # Normalize whitespace

        lang = getattr(transcript, 'language_code', '?')
        if len(full_text) > 100:
            print(f"  ✅ Tier 1 (youtube-transcript-api): {len(full_text)} chars, lang={lang}")
            return full_text

    except ImportError:
        logger.warning("youtube-transcript-api not installed")
    except Exception as e:
        err_msg = str(e)
        if 'TranscriptsDisabled' in err_msg:
            print(f"  ⚠️ Tier 1: Transcripts disabled for this video")
        elif 'NoTranscript' in err_msg:
            print(f"  ⚠️ Tier 1: No transcript found")
        else:
            print(f"  ⚠️ Tier 1 failed: {err_msg[:100]}")

    return None


# ══════════════════════════════════════════════════════════════════
#  Tier 2: yt-dlp subtitle extraction (existing method)
# ══════════════════════════════════════════════════════════════════

def _fetch_via_ytdlp(youtube_url: str, max_retries: int = 2) -> tuple[str | None, dict | None]:
    """
    Fetch transcript via yt-dlp. Returns (transcript_text, video_info).
    May hit CAPTCHA — that's why this is tier 2.
    """
    import yt_dlp

    video_info = None
    last_error = ""

    for attempt in range(max_retries):
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant', 'de', 'fr', 'es'],
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                }
            }

            # Cookie handling (if available)
            cookies_content = os.getenv('YOUTUBE_COOKIES_CONTENT')
            if cookies_content:
                try:
                    cookies_path = '/tmp/cookies_yt.txt'
                    with open(cookies_path, 'w') as f:
                        f.write(cookies_content)
                    ydl_opts['cookiefile'] = cookies_path
                except Exception as e:
                    print(f"⚠️ Failed to write cookies: {e}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(youtube_url, download=False)
                break
        except Exception as e:
            last_error = str(e)
            print(f"  ⚠️ yt-dlp attempt {attempt + 1} failed: {e}")
            if "Sign in to confirm you're not a bot" in last_error:
                break
            if attempt < max_retries - 1:
                time.sleep(2)

    if not video_info:
        return None, None

    # Try to get subtitles/captions
    subtitles = video_info.get('subtitles', {})
    automatic_captions = video_info.get('automatic_captions', {})

    transcript_text = None
    langs = ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant', 'de', 'fr', 'es']

    for lang in langs:
        try:
            target = None
            if lang in subtitles:
                target = subtitles[lang]
            elif lang in automatic_captions:
                target = automatic_captions[lang]

            if target:
                sub_url = None
                for sub in target:
                    if sub.get('ext') == 'json3':
                        sub_url = sub.get('url')
                        break
                if not sub_url:
                    sub_url = target[0].get('url')

                if sub_url:
                    response = requests.get(sub_url, timeout=10)
                    transcript_text = response.text

                    if 'json3' in sub_url or (response.headers.get('Content-Type') and 'json' in response.headers.get('Content-Type')):
                        try:
                            import json
                            data = json.loads(transcript_text)
                            segments = []
                            for event in data.get('events', []):
                                if 'segs' in event:
                                    text = ''.join([s.get('utf8', '') for s in event['segs']])
                                    if text.strip():
                                        segments.append(text.strip())
                            transcript_text = ' '.join(segments)
                        except Exception:
                            pass
                    break
        except Exception:
            continue

    if transcript_text and len(transcript_text) > 100:
        # Clean up VTT if we got it
        if "WEBVTT" in transcript_text:
            transcript_text = re.sub(r'WEBVTT.*?\n\n', '', transcript_text, flags=re.DOTALL)
            transcript_text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', transcript_text)
            transcript_text = re.sub(r'<[^>]+>', '', transcript_text)
        transcript_text = ' '.join(transcript_text.split())

        # Validate: reject CAPTCHA/error page content
        captcha_indicators = ['captcha', 'automated queries', 'unusual traffic',
                              'sorry about that', 'verify you are a human']
        if any(c in transcript_text.lower() for c in captcha_indicators):
            print(f"  ⚠️ Tier 2: yt-dlp returned CAPTCHA content, rejecting")
            return None, video_info

        print(f"  ✅ Tier 2 (yt-dlp): {len(transcript_text)} chars")
        return transcript_text, video_info

    return None, video_info


# ══════════════════════════════════════════════════════════════════
#  Main entry point
# ══════════════════════════════════════════════════════════════════

def transcribe_from_youtube(youtube_url, max_retries=2):
    """
    Gets transcript from YouTube using multi-tier approach:
      Tier 1: youtube-transcript-api (most reliable, no CAPTCHA)
      Tier 2: yt-dlp subtitle extraction (may hit bot detection)
      Tier 3: Metadata fallback (title + description only)
    """
    print(f"Getting transcript from YouTube subtitles...")

    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return f"ERROR: Could not extract video ID from {youtube_url}"

    # ── Tier 1: youtube-transcript-api ──
    transcript = _fetch_via_transcript_api(video_id)
    if transcript and len(transcript) > 100:
        print(f"✓ Transcript complete. Length: {len(transcript)}")
        return transcript

    # ── Tier 2: yt-dlp ──
    print(f"  📝 Tier 1 failed, trying yt-dlp (Tier 2)...")
    transcript, video_info = _fetch_via_ytdlp(youtube_url, max_retries)
    if transcript and len(transcript) > 100:
        print(f"✓ Transcript complete. Length: {len(transcript)}")
        return transcript

    # If yt-dlp didn't give us video_info either, try oEmbed
    if not video_info:
        print("  ❌ yt-dlp failed, trying oEmbed for metadata...")
        video_info = _get_video_info_fallback(youtube_url)
        if not video_info:
            return f"ERROR: Failed to get video info for {youtube_url}"

    # ── Tier 3: Metadata fallback ──
    print("  ⚠️ No valid subtitles from any tier, using metadata fallback")
    title = video_info.get('title', 'Unknown Title')
    description = video_info.get('description', '')
    channel = video_info.get('channel', video_info.get('author', 'Unknown Channel'))

    fallback_parts = [f"Title: {title}", f"Channel: {channel}"]
    if description and len(description) > 10:
        clean_desc = re.sub(r'http\S+', '', description)
        fallback_parts.append(f"Description: {clean_desc.strip()}")

    fallback_text = '\n\n'.join(fallback_parts)

    if len(fallback_text) < 10:
        return f"ERROR: Metadata too short for video {youtube_url}"

    return fallback_text
