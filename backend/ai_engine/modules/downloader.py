import os
import yt_dlp
import sys

# Import config - try multiple paths, fallback to defaults
try:
    from ai_engine.config import TRANSCRIPTS_DIR
except ImportError:
    try:
        from config import TRANSCRIPTS_DIR
    except ImportError:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        TRANSCRIPTS_DIR = os.path.join(BASE_DIR, 'ai_engine', 'output', 'transcripts')

# Import utils
try:
    from ai_engine.modules.utils import retry_on_failure, extract_video_id
except ImportError:
    try:
        from modules.utils import retry_on_failure, extract_video_id
    except ImportError:
        # Minimal fallback
        def retry_on_failure(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def extract_video_id(url):
            import re
            match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)', url)
            return match.group(1) if match else None

# FFmpeg path (empty on production Linux)
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '')


@retry_on_failure(max_retries=3, delay=10, exceptions=(Exception,))
def download_audio_and_thumbnail(youtube_url):
    """
    Downloads audio from YouTube video as MP3 and fetches the thumbnail.
    Returns tuple: (audio_file_path, thumbnail_file_path)
    """
    print(f"Downloading content from {youtube_url}...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(TRANSCRIPTS_DIR, '%(id)s.%(ext)s'),
        'writethumbnail': True,  # Download thumbnail
        'quiet': True,
        'ffmpeg_location': FFMPEG_PATH,  # Explicit ffmpeg path
    }

    thumbnail_path = None
    audio_path = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        video_id = info_dict.get("id", None)
        audio_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}.mp3")
        
        # yt-dlp saves thumbnail as video_id.jpg or .webp
        # We check for the file
        possible_exts = ['jpg', 'webp', 'png']
        for ext in possible_exts:
            t_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}.{ext}")
            if os.path.exists(t_path):
                thumbnail_path = t_path
                break
        
    print(f"Audio downloaded to {audio_path}")
    print(f"Thumbnail downloaded to {thumbnail_path}")
    return audio_path, thumbnail_path


def download_thumbnail_only(youtube_url):
    """
    Downloads ONLY the thumbnail from YouTube (no audio/video).
    Also extracts video info for transcriber.
    Returns tuple: (video_id, thumbnail_file_path, video_title)
    """
    print(f"Fetching video info from {youtube_url}...")
    
    ydl_opts = {
        'skip_download': True,  # Don't download video/audio!
        'writethumbnail': True,  # Only thumbnail
        'outtmpl': os.path.join(TRANSCRIPTS_DIR, '%(id)s.%(ext)s'),
        'quiet': True,
    }

    thumbnail_path = None
    video_id = None
    video_title = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)  # Downloads only thumbnail
        video_id = info_dict.get("id", None)
        video_title = info_dict.get("title", "Unknown Video")
        
        # Check for thumbnail file
        possible_exts = ['jpg', 'webp', 'png']
        for ext in possible_exts:
            t_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}.{ext}")
            if os.path.exists(t_path):
                thumbnail_path = t_path
                break
        
    print(f"✓ Thumbnail downloaded: {thumbnail_path}")
    print(f"✓ Video: {video_title}")
    return video_id, thumbnail_path, video_title


def extract_video_screenshots(youtube_url, count=3):
    """
    Extracts multiple screenshots from a YouTube video at different timestamps.
    Returns list of screenshot file paths.
    Works on both Windows (with FFMPEG_PATH) and Linux (ffmpeg in PATH).
    """
    import subprocess
    import shutil
    
    print(f"📸 Extracting {count} screenshots from {youtube_url}...")
    
    # Find ffmpeg executable
    ffmpeg_exe = None
    if FFMPEG_PATH and os.path.exists(os.path.join(FFMPEG_PATH, 'ffmpeg.exe')):
        # Windows with explicit path
        ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
    elif shutil.which('ffmpeg'):
        # Linux/Mac or Windows with ffmpeg in PATH
        ffmpeg_exe = 'ffmpeg'
    else:
        print("⚠ FFmpeg not found, falling back to YouTube thumbnails")
        return get_youtube_thumbnails(youtube_url, count)
    
    print(f"✓ Using FFmpeg: {ffmpeg_exe}")
    
    ydl_opts = {
        'format': 'best[height<=720]',  # Lower quality for faster extraction
        'quiet': True,
    }
    
    screenshots = []
    
    try:
        # Get video info and direct URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_id = info_dict.get("id", None)
            duration = info_dict.get("duration", 300)  # Default 5 min if unknown
            
            # Get direct video URL from formats - prefer mp4
            formats = info_dict.get('formats', [])
            video_url = None
            
            # First try to find mp4 format
            for fmt in sorted(formats, key=lambda x: x.get('height', 0), reverse=True):
                if fmt.get('vcodec') != 'none' and fmt.get('url'):
                    if fmt.get('ext') == 'mp4' or 'mp4' in fmt.get('url', ''):
                        video_url = fmt['url']
                        print(f"✓ Found video format: {fmt.get('format_note', 'unknown')} ({fmt.get('height', '?')}p)")
                        break
            
            # Fallback to any video format
            if not video_url:
                for fmt in formats:
                    if fmt.get('vcodec') != 'none' and fmt.get('url'):
                        video_url = fmt['url']
                        break
            
            if not video_url:
                print("⚠ Could not get direct video URL, using thumbnails")
                return get_youtube_thumbnails(youtube_url, count)
        
        # Calculate timestamps (avoid first/last 15%)
        start_offset = duration * 0.15
        end_offset = duration * 0.85
        usable_duration = end_offset - start_offset
        
        timestamps = []
        for i in range(count):
            # Distribute evenly
            position = start_offset + (usable_duration * (i + 1) / (count + 1))
            timestamps.append(int(position))
        
        print(f"📍 Timestamps: {timestamps} seconds (video duration: {duration}s)")
        
        # Extract screenshots using ffmpeg
        for i, timestamp in enumerate(timestamps):
            output_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}_screenshot_{i+1}.jpg")
            
            # Build ffmpeg command (cross-platform)
            cmd = [
                ffmpeg_exe,
                '-ss', str(timestamp),  # Seek to timestamp (before -i for fast seek)
                '-i', video_url,  # Input URL
                '-vframes', '1',  # Extract 1 frame
                '-vf', 'scale=1280:-1',  # Scale to 1280px width
                '-q:v', '2',  # High quality JPEG
                '-y',  # Overwrite
                output_path
            ]
            
            try:
                print(f"  Extracting screenshot {i+1}/{count} at {timestamp}s...")
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=60,  # Increased timeout
                    check=False
                )
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    screenshots.append(output_path)
                    print(f"  ✓ Screenshot {i+1} saved ({os.path.getsize(output_path) // 1024}KB)")
                else:
                    print(f"  ⚠ Screenshot {i+1} failed or too small")
                    if result.stderr:
                        # Show only relevant error info
                        error_lines = [l for l in result.stderr.split('\n') if 'error' in l.lower()]
                        if error_lines:
                            print(f"    Error: {error_lines[0][:100]}")
                        
            except subprocess.TimeoutExpired:
                print(f"  ⚠ Screenshot {i+1} timed out")
            except Exception as e:
                print(f"  ⚠ Screenshot {i+1} error: {e}")
        
    except Exception as e:
        print(f"⚠ Error extracting screenshots: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to thumbnails
        return get_youtube_thumbnails(youtube_url, count)
    
    # If we got fewer screenshots than requested, supplement with thumbnails
    if len(screenshots) < count:
        print(f"⚠ Only got {len(screenshots)}/{count} screenshots, adding thumbnails...")
        thumbnails = get_youtube_thumbnails(youtube_url, count - len(screenshots))
        screenshots.extend(thumbnails)
    
    print(f"✓ Total screenshots: {len(screenshots)}")
    return screenshots


def get_youtube_thumbnails(youtube_url, count=3):
    """
    Fallback: Get YouTube thumbnail images (different quality/positions).
    Returns list of downloaded thumbnail paths.
    """
    import urllib.request
    
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return []
    
    # YouTube provides these thumbnail variants
    thumbnail_urls = [
        f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',  # Best quality
        f'https://i.ytimg.com/vi/{video_id}/sddefault.jpg',      # SD quality
        f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',      # HQ
        f'https://i.ytimg.com/vi/{video_id}/0.jpg',              # Frame at ~25%
        f'https://i.ytimg.com/vi/{video_id}/1.jpg',              # Frame at ~25%
        f'https://i.ytimg.com/vi/{video_id}/2.jpg',              # Frame at ~50%
        f'https://i.ytimg.com/vi/{video_id}/3.jpg',              # Frame at ~75%
    ]
    
    downloaded = []
    
    for i, url in enumerate(thumbnail_urls[:count + 3]):  # Try a few extra in case some fail
        if len(downloaded) >= count:
            break
            
        output_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}_thumb_{i+1}.jpg")
        
        try:
            urllib.request.urlretrieve(url, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                downloaded.append(output_path)
                print(f"  ✓ Downloaded thumbnail {len(downloaded)}")
        except Exception as e:
            pass  # Some thumbnails may not exist
    
    return downloaded
