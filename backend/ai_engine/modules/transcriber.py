import os
import yt_dlp
import sys
import re
import time
import requests

def transcribe_from_youtube(youtube_url, max_retries=3):
    """
    Gets transcript from YouTube subtitles (much faster and more reliable than audio transcription).
    Takes YouTube URL directly - no audio file needed!
    Returns the transcript text.
    
    Falls back to title + description if no subtitles available.
    
    Args:
        youtube_url: YouTube video URL
        max_retries: Number of retry attempts on failure
    """
    print(f"Getting transcript from YouTube subtitles...")
    
    # First, get video info (will use for fallback too)
    video_info = None
    for attempt in range(max_retries):
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'ru', 'zh'],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(youtube_url, download=False)
                break
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1}/{max_retries} to get video info failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    if not video_info:
        print("❌ Failed to get video info")
        return ""
    
    # Try to get subtitles/captions
    subtitles = video_info.get('subtitles', {})
    automatic_captions = video_info.get('automatic_captions', {})
    
    print(f"Available subtitles: {list(subtitles.keys())}")
    print(f"Available auto-captions: {list(automatic_captions.keys())[:10]}...")
    
    # Prefer manual subtitles, fallback to auto-generated
    transcript_text = None
    
    for lang in ['en', 'ru', 'zh', 'zh-Hans', 'zh-Hant']:
        try:
            if lang in subtitles and subtitles[lang]:
                # Get subtitle URL
                sub_url = subtitles[lang][0].get('url')
                if sub_url:
                    response = requests.get(sub_url, timeout=10)
                    transcript_text = response.text
                    print(f"Got manual subtitles in {lang}")
                    break
            elif lang in automatic_captions and automatic_captions[lang]:
                sub_url = automatic_captions[lang][0].get('url')
                if sub_url:
                    response = requests.get(sub_url, timeout=10)
                    transcript_text = response.text
                    print(f"Got auto-generated captions in {lang}")
                    break
        except Exception as e:
            print(f"Failed to get {lang} subtitles: {e}")
            continue
    
    if transcript_text:
        # Clean up subtitle formatting (remove timestamps, etc)
        # Remove WebVTT headers
        transcript_text = re.sub(r'WEBVTT.*?\n\n', '', transcript_text, flags=re.DOTALL)
        # Remove timestamp lines
        transcript_text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', transcript_text)
        # Remove position/alignment tags
        transcript_text = re.sub(r'<[^>]+>', '', transcript_text)
        # Clean up extra whitespace
        transcript_text = ' '.join(transcript_text.split())
        
        print(f"✓ Transcript complete. Length: {len(transcript_text)} characters")
        return transcript_text
    
    # Fallback: use video title and description
    print("⚠️ No subtitles available, using title + description as fallback")
    
    title = video_info.get('title', '') or ''
    description = video_info.get('description', '') or ''
    channel = video_info.get('channel', '') or video_info.get('uploader', '') or ''
    duration = video_info.get('duration', 0)
    
    # Build a comprehensive fallback text
    fallback_parts = []
    
    if title:
        fallback_parts.append(f"Video Title: {title}")
    
    if channel:
        fallback_parts.append(f"Channel: {channel}")
    
    if duration:
        minutes = duration // 60
        fallback_parts.append(f"Duration: {minutes} minutes")
    
    if description:
        # Clean up description - remove links and excessive whitespace
        clean_desc = re.sub(r'http\S+', '', description)
        clean_desc = re.sub(r'\n{3,}', '\n\n', clean_desc)
        clean_desc = clean_desc.strip()
        if len(clean_desc) > 50:
            fallback_parts.append(f"Description: {clean_desc}")
    
    fallback_text = '\n\n'.join(fallback_parts)
    
    print(f"✓ Using fallback text ({len(fallback_text)} chars)")
    return fallback_text

