import os
import yt_dlp
import sys

# Import config from ai_engine
try:
    from ai_engine.config import TRANSCRIPTS_DIR
except ImportError:
    from config import TRANSCRIPTS_DIR

# Import utils
try:
    from ai_engine.modules.utils import retry_on_failure, extract_video_id
except ImportError:
    from modules.utils import retry_on_failure, extract_video_id


# FFmpeg path for Windows
FFMPEG_PATH = r"C:\Users\kille\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"

from modules.utils import retry_on_failure, extract_video_id


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
    """
    import subprocess
    
    print(f"Extracting {count} screenshots from {youtube_url}...")
    
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
            
            # Get direct video URL from formats
            formats = info_dict.get('formats', [])
            video_url = None
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('url'):
                    video_url = fmt['url']
                    break
            
            if not video_url:
                print("⚠ Could not get direct video URL")
                return screenshots
        
        # Calculate timestamps (avoid first/last 10%)
        start_offset = duration * 0.15
        end_offset = duration * 0.85
        usable_duration = end_offset - start_offset
        
        timestamps = []
        for i in range(count):
            # Distribute evenly
            position = start_offset + (usable_duration * (i + 1) / (count + 1))
            timestamps.append(int(position))
        
        print(f"Timestamps: {timestamps} seconds")
        
        # Extract screenshots using ffmpeg
        for i, timestamp in enumerate(timestamps):
            output_path = os.path.join(TRANSCRIPTS_DIR, f"{video_id}_screenshot_{i+1}.jpg")
            
            # Build ffmpeg command
            ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
            cmd = [
                ffmpeg_exe,
                '-ss', str(timestamp),  # Seek to timestamp
                '-i', video_url,  # Input URL
                '-vframes', '1',  # Extract 1 frame
                '-vf', 'scale=1280:-1',  # Scale to 1280px width
                '-q:v', '2',  # High quality
                '-y',  # Overwrite
                output_path
            ]
            
            try:
                print(f"Extracting screenshot {i+1}/{count} at {timestamp}s...")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    screenshots.append(output_path)
                    print(f"✓ Screenshot {i+1} saved: {output_path}")
                else:
                    print(f"⚠ Screenshot {i+1} failed or too small")
                    if result.stderr:
                        print(f"FFmpeg error: {result.stderr[:200]}")
                        
            except subprocess.TimeoutExpired:
                print(f"⚠ Screenshot {i+1} timed out")
            except Exception as e:
                print(f"⚠ Screenshot {i+1} error: {e}")
        
    except Exception as e:
        print(f"⚠ Error extracting screenshots: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Total screenshots extracted: {len(screenshots)}")
    return screenshots
