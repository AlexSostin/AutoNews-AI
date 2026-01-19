import os
import yt_dlp
import sys

# Import config from ai_engine
try:
    from ai_engine.config import GEMINI_API_KEY
except ImportError:
    from config import GEMINI_API_KEY

def transcribe_from_youtube(youtube_url, max_retries=3):
    """
    Gets transcript from YouTube subtitles (much faster and more reliable than audio transcription).
    Takes YouTube URL directly - no audio file needed!
    Returns the transcript text.
    
    Args:
        youtube_url: YouTube video URL
        max_retries: Number of retry attempts on failure
    """
    print(f"Getting transcript from YouTube subtitles...")
    
    for attempt in range(max_retries):
        try:
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'ru'],
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Try to get subtitles/captions
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            # Prefer manual subtitles, fallback to auto-generated
            transcript_text = None
            
            for lang in ['en', 'ru']:
                if lang in subtitles:
                    # Get subtitle URL
                    sub_url = subtitles[lang][0]['url']
                    import requests
                    response = requests.get(sub_url)
                    transcript_text = response.text
                    print(f"Got manual subtitles in {lang}")
                    break
                elif lang in automatic_captions:
                    sub_url = automatic_captions[lang][0]['url']
                    import requests
                    response = requests.get(sub_url)
                    transcript_text = response.text
                    print(f"Got auto-generated captions in {lang}")
                    break
            
            if transcript_text:
                # Clean up subtitle formatting (remove timestamps, etc)
                import re
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
            else:
                raise Exception("No subtitles/captions available for this video")
        
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"   Retrying in 5 seconds...")
                import time
                time.sleep(5)
            else:
                print(f"❌ All {max_retries} attempts failed: {e}")
                # Final fallback: return video title and description
                try:
                    ydl_opts = {'skip_download': True, 'quiet': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(youtube_url, download=False)
                        fallback_text = f"{info.get('title', '')}. {info.get('description', '')}"
                        print(f"Using fallback: title + description ({len(fallback_text)} chars)")
                        return fallback_text
                except Exception as fallback_error:
                    print(f"Even fallback failed: {fallback_error}")
                    return ""
                return fallback_text
        except:
            return ""
