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


def extract_video_screenshots(youtube_url, output_dir=None, count=1):
    """
    Downloads the best quality YouTube thumbnail (maxresdefault).
    Only downloads 1 high-quality image to avoid duplicates.
    
    Returns list with single thumbnail path.
    """
    if output_dir is None:
        output_dir = TRANSCRIPTS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print("⚠️ Could not extract video ID from URL")
        return []
    
    print(f"📸 Downloading best quality YouTube thumbnail for video {video_id}...")
    
    # Try only the BEST quality thumbnail to avoid duplicates
    # YouTube numbered thumbnails often don't exist or return same image
    thumbnail_urls = [
        f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",  # 1920x1080 - BEST!
        f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",      # 640x480 - Fallback
        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",      # 480x360 - Last resort
    ]
    
    
    
    thumbnails = []
    
    import requests
    from PIL import Image
    from io import BytesIO
    
    # Try each URL until we get one good quality image
    for url in thumbnail_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and len(response.content) > 10000:  # Min 10KB for quality
                # Verify it's a valid image
                try:
                    img = Image.open(BytesIO(response.content))
                    width, height = img.size
                    
                    # We want at least 640px width for quality
                    if width >= 640:
                        # Save thumbnail
                        output_filename = f"{video_id}_cover.jpg"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        
                        thumbnails.append(output_path)
                        print(f"  ✓ High-quality thumbnail downloaded: {width}x{height} ({len(response.content)//1024}KB)")
                        break  # Got one good image, stop here!
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            continue
    
    if thumbnails:
        print(f"✓ Downloaded best quality thumbnail")
    else:
        print("⚠️ No thumbnail could be downloaded")
    
    return thumbnails



    """
    Extracts multiple screenshots from a YouTube video at different timestamps.
    Downloads short video segments and extracts frames from them.
    Returns list of screenshot file paths.
    
    Args:
        youtube_url: YouTube video URL
        output_dir: Directory to save screenshots (optional, defaults to TRANSCRIPTS_DIR)
        count: Number of screenshots to extract
    """
    import subprocess
    import shutil
    import tempfile
    
    if output_dir is None:
        output_dir = TRANSCRIPTS_DIR
    
    print(f"📸 Extracting {count} screenshots from {youtube_url}...")
    
    # Find ffmpeg executable
    ffmpeg_exe = None
    if FFMPEG_PATH and os.path.exists(os.path.join(FFMPEG_PATH, 'ffmpeg.exe')):
        ffmpeg_exe = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
    elif shutil.which('ffmpeg'):
        ffmpeg_exe = 'ffmpeg'
    else:
        print("⚠ FFmpeg not found, falling back to YouTube thumbnails")
        return get_youtube_thumbnails(youtube_url, output_dir=output_dir, count=count)
    
    print(f"✓ Using FFmpeg: {ffmpeg_exe}")
    
    screenshots = []
    video_id = extract_video_id(youtube_url)
    
    try:
        # Get video duration first
        ydl_opts = {'skip_download': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            duration = info.get('duration', 300)
            video_id = info.get('id', video_id)
        
        print(f"✓ Video duration: {duration} seconds")
        
        # Calculate 3 different timestamps (25%, 50%, 75% of video)
        timestamps = [
            int(duration * 0.25),
            int(duration * 0.50),
            int(duration * 0.75)
        ]
        
        print(f"📍 Target timestamps: {timestamps} seconds")
        
        # Download short segments and extract frames
        for i, timestamp in enumerate(timestamps[:count]):
            try:
                # Create temp file for video segment
                temp_video = os.path.join(output_dir, f"{video_id}_segment_{i}.mp4")
                output_image = os.path.join(output_dir, f"{video_id}_frame_{i+1}.jpg")
                
                # Download 2-second segment at timestamp using yt-dlp
                print(f"  Downloading segment {i+1}/{count} at {timestamp}s...")
                
                ydl_opts_download = {
                    'format': 'best[height<=1080][ext=mp4]/best[height<=1080]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',  # Up to 1080p
                    'outtmpl': temp_video,
                    'quiet': True,
                    'no_warnings': True,
                    # Download only specific section
                    'download_ranges': lambda info, ydl: [{'start_time': timestamp, 'end_time': timestamp + 2}],
                    'force_keyframes_at_cuts': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                    ydl.download([youtube_url])
                
                # Check if video was downloaded
                if os.path.exists(temp_video) and os.path.getsize(temp_video) > 1000:
                    # Extract first frame from segment with high quality
                    cmd = [
                        ffmpeg_exe,
                        '-i', temp_video,
                        '-vframes', '1',
                        '-vf', 'scale=1920:-1',  # Scale to 1920px width (FullHD)
                        '-q:v', '1',  # Highest JPEG quality (1-31, lower is better)
                        '-y',
                        output_image
                    ]
                    
                    subprocess.run(cmd, capture_output=True, timeout=30)
                    
                    if os.path.exists(output_image) and os.path.getsize(output_image) > 1000:
                        screenshots.append(output_image)
                        print(f"  ✓ Frame {i+1} extracted ({os.path.getsize(output_image) // 1024}KB)")
                    
                    # Clean up temp video
                    try:
                        os.remove(temp_video)
                    except:
                        pass
                else:
                    print(f"  ⚠ Segment {i+1} download failed")
                    
            except Exception as e:
                print(f"  ⚠ Error extracting frame {i+1}: {e}")
                continue
        
        # If we got screenshots, return them
        if screenshots:
            print(f"✓ Extracted {len(screenshots)} unique frames")
            return screenshots
            
    except Exception as e:
        print(f"⚠ Error in video extraction: {e}")
        import traceback
        traceback.print_exc()
    
    # Fallback to thumbnails if extraction failed
    print("⚠ Falling back to YouTube thumbnails")
    return get_youtube_thumbnails(youtube_url, output_dir=output_dir, count=count)


def get_youtube_thumbnails(youtube_url, output_dir=None, count=3):
    """
    Fallback: Get YouTube thumbnail images (different quality/positions).
    Returns list of downloaded thumbnail paths.
    
    Args:
        youtube_url: YouTube video URL
        output_dir: Directory to save thumbnails (optional, defaults to TRANSCRIPTS_DIR)
        count: Number of thumbnails to download
    """
    import urllib.request
    
    if output_dir is None:
        output_dir = TRANSCRIPTS_DIR
    
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
            
        output_path = os.path.join(output_dir, f"{video_id}_thumb_{i+1}.jpg")
        
        try:
            urllib.request.urlretrieve(url, output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                downloaded.append(output_path)
                print(f"  ✓ Downloaded thumbnail {len(downloaded)}")
        except Exception as e:
            pass  # Some thumbnails may not exist
    
    return downloaded
