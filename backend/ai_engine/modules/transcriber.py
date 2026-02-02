import os
import yt_dlp
import sys
import re
import time
import requests

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

def transcribe_from_youtube(youtube_url, max_retries=2):
    """
    Gets transcript from YouTube subtitles.
    Falls back to title + description if no subtitles available.
    """
    print(f"Getting transcript from YouTube subtitles...")
    
    video_info = None
    last_error = ""

    # Try yt-dlp first
    for attempt in range(max_retries):
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant', 'de', 'fr', 'es'],
                'quiet': True,
                'no_warnings': True,
                # Add common headers to avoid bot detection
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                }
            }
            
            # Cookie handling
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
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            if "Sign in to confirm you’re not a bot" in last_error:
                # If blocked, don't bother retrying immediately without change
                break
            if attempt < max_retries - 1:
                time.sleep(2)
    
    # If yt-dlp failed, try oEmbed for basic metadata
    if not video_info:
        print("❌ yt-dlp failed, trying oEmbed fallback for metadata...")
        video_info = _get_video_info_fallback(youtube_url)
        if not video_info:
            error_msg = f"Failed to get video info: {last_error}"
            print(f"❌ {error_msg}")
            return f"ERROR: {error_msg}"
    
    # Try to get subtitles/captions
    subtitles = video_info.get('subtitles', {}) if video_info else {}
    automatic_captions = video_info.get('automatic_captions', {}) if video_info else {}
    
    transcript_text = None
    
    # Priority order for subtitle languages
    langs = ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant', 'de', 'fr', 'es']
    for lang in langs:
        try:
            target = None
            if lang in subtitles:
                target = subtitles[lang]
            elif lang in automatic_captions:
                target = automatic_captions[lang]
                
            if target:
                # Find JSON or VTT format
                sub_url = None
                for sub in target:
                    if sub.get('ext') == 'json3': # Preferred format
                        sub_url = sub.get('url')
                        break
                
                if not sub_url:
                    sub_url = target[0].get('url')
                
                if sub_url:
                    response = requests.get(sub_url, timeout=10)
                    transcript_text = response.text
                    
                    # If it's json3, we need to extract text
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
                        except:
                            pass
                    break
        except Exception as e:
            continue
    
    if transcript_text and len(transcript_text) > 100:
        # Clean up VTT if we got it
        if "WEBVTT" in transcript_text:
            transcript_text = re.sub(r'WEBVTT.*?\n\n', '', transcript_text, flags=re.DOTALL)
            transcript_text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', transcript_text)
            transcript_text = re.sub(r'<[^>]+>', '', transcript_text)
        
        transcript_text = ' '.join(transcript_text.split())
        print(f"✓ Transcript complete. Length: {len(transcript_text)}")
        return transcript_text
    
    # Fallback: title + description
    print("⚠️ No valid subtitles available, using metadata fallback")
    title = video_info.get('title', 'Unknown Title')
    description = video_info.get('description', '')
    channel = video_info.get('channel', video_info.get('author', 'Unknown Channel'))
    
    fallback_parts = [f"Title: {title}", f"Channel: {channel}"]
    if description and len(description) > 10:
        clean_desc = re.sub(r'http\S+', '', description)
        fallback_parts.append(f"Description: {clean_desc.strip()}")
        
    fallback_text = '\n\n'.join(fallback_parts)
    
    # If even fallback is too short, return error string instead of empty
    if len(fallback_text) < 10:
        return f"ERROR: Metadata too short for video {youtube_url}"
        
    return fallback_text

