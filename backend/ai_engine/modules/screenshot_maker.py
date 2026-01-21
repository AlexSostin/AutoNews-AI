import os
import yt_dlp
import sys
import hashlib
import subprocess
from io import BytesIO

def get_image_hash(image_path):
    """Get simple hash of image file to detect duplicates"""
    try:
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def extract_screenshots(youtube_url, output_dir, num_screenshots=3):
    """
    Extracts multiple screenshots from a YouTube video at different timestamps.
    Returns list of screenshot file paths.
    
    Args:
        youtube_url: YouTube video URL
        output_dir: Directory to save screenshots
        num_screenshots: Number of screenshots to extract (default 3)
    
    Returns:
        List of screenshot file paths
    """
    print(f"📸 Extracting {num_screenshots} screenshots from video...")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    screenshots = []
    
    try:
        # First, get video duration
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            duration = info.get('duration', 0)
            video_id = info.get('id', 'video')
            
            if duration == 0:
                print("❌ Could not get video duration")
                return []
            
            print(f"  Video duration: {duration}s")
            
            # Calculate timestamps for screenshots
            # Skip first 10% and last 10% to avoid intros/outros
            start_time = int(duration * 0.1)
            end_time = int(duration * 0.9)
            interval = (end_time - start_time) // num_screenshots
            
            timestamps = [start_time + (i * interval) for i in range(num_screenshots)]
            
            print(f"  Screenshot timestamps: {timestamps}")
            
            # Extract screenshots at each timestamp
            for i, timestamp in enumerate(timestamps):
                output_filename = f"{video_id}_screenshot_{i+1}.jpg"
                output_path = os.path.join(output_dir, output_filename)
                
                # Use yt-dlp to extract frame at specific timestamp
                screenshot_opts = {
                    'skip_download': True,
                    'quiet': True,
                    'format': 'best',
                    'outtmpl': output_path,
                    'external_downloader': 'ffmpeg',
                    'external_downloader_args': [
                        '-ss', str(timestamp),
                        '-frames:v', '1'
                    ],
                }
                
                try:
                    # Download best quality video frame
                    with yt_dlp.YoutubeDL(screenshot_opts) as ydl_screen:
                        # Download the video temporarily to extract frame
                        temp_opts = {
                            'format': 'best[height<=1080]',
                            'outtmpl': os.path.join(output_dir, f'temp_{video_id}.%(ext)s'),
                            'quiet': True,
                        }
                        
                        # Alternative approach: download segment and extract frame
                        import subprocess
                        
                        # Get direct video URL
                        formats = info.get('formats', [])
                        video_url = None
                        for fmt in formats:
                            if fmt.get('vcodec') != 'none' and fmt.get('height', 0) >= 720:
                                video_url = fmt.get('url')
                                break
                        
                        if not video_url:
                            video_url = info.get('url')
                        
                        if video_url:
                            # Use ffmpeg to extract screenshot
                            cmd = [
                                'ffmpeg',
                                '-ss', str(timestamp),
                                '-i', video_url,
                                '-vframes', '1',
                                '-q:v', '2',
                                '-y',
                                output_path
                            ]
                            
                            result = subprocess.run(cmd, capture_output=True, timeout=30)
                            
                            if result.returncode == 0 and os.path.exists(output_path):
                                screenshots.append(output_path)
                                print(f"  ✓ Screenshot {i+1} saved: {output_filename}")
                            else:
                                print(f"  ⚠️ Failed to extract screenshot {i+1}")
                        
                except Exception as e:
                    print(f"  ⚠️ Error extracting screenshot {i+1}: {e}")
                    continue
            
            if screenshots:
                print(f"✓ Successfully extracted {len(screenshots)} screenshots")
            else:
                print("⚠️ No screenshots extracted, will use fallback")
            
            return screenshots
    
    except Exception as e:
        print(f"❌ Screenshot extraction failed: {e}")
        return []


def extract_screenshots_simple(youtube_url, output_dir, num_screenshots=3):
    """
    Extract real frames from YouTube video at different timestamps.
    Falls back to thumbnails if ffmpeg extraction fails.
    Returns list of unique screenshot file paths.
    """
    print(f"📸 Extracting {num_screenshots} screenshots from video...")
    
    os.makedirs(output_dir, exist_ok=True)
    screenshots = []
    seen_hashes = set()
    
    try:
        # Get video info
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_id = info.get('id', 'video')
            duration = info.get('duration', 0)
            
            # Try to extract real frames using ffmpeg first
            if duration > 30:
                print(f"  Video duration: {duration}s, extracting real frames...")
                
                # Get best video format URL
                formats = info.get('formats', [])
                video_url = None
                
                # Find good quality video stream
                for fmt in sorted(formats, key=lambda x: x.get('height', 0), reverse=True):
                    if (fmt.get('vcodec') != 'none' and 
                        fmt.get('acodec') == 'none' and  # Video only for faster download
                        720 <= fmt.get('height', 0) <= 1080):
                        video_url = fmt.get('url')
                        print(f"  Using format: {fmt.get('height')}p")
                        break
                
                # Fallback to any video format
                if not video_url:
                    for fmt in formats:
                        if fmt.get('vcodec') != 'none' and fmt.get('height', 0) >= 480:
                            video_url = fmt.get('url')
                            break
                
                if video_url:
                    # Calculate timestamps: skip intro (15%) and outro (15%)
                    start_time = int(duration * 0.15)
                    end_time = int(duration * 0.85)
                    
                    # Extract more frames than needed to pick unique ones
                    num_to_extract = num_screenshots * 2
                    interval = (end_time - start_time) // num_to_extract
                    
                    timestamps = [start_time + (i * interval) for i in range(num_to_extract)]
                    print(f"  Timestamps to try: {timestamps[:6]}...")
                    
                    for i, timestamp in enumerate(timestamps):
                        if len(screenshots) >= num_screenshots:
                            break
                            
                        output_filename = f"{video_id}_frame_{timestamp}s.jpg"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        try:
                            # Extract frame using ffmpeg
                            cmd = [
                                'ffmpeg',
                                '-ss', str(timestamp),
                                '-i', video_url,
                                '-vframes', '1',
                                '-q:v', '2',  # High quality JPEG
                                '-y',
                                output_path
                            ]
                            
                            result = subprocess.run(
                                cmd, 
                                capture_output=True, 
                                timeout=15,
                                stderr=subprocess.DEVNULL
                            )
                            
                            if result.returncode == 0 and os.path.exists(output_path):
                                # Check for duplicates
                                img_hash = get_image_hash(output_path)
                                
                                if img_hash and img_hash not in seen_hashes:
                                    seen_hashes.add(img_hash)
                                    
                                    # Rename to sequential
                                    final_filename = f"{video_id}_screenshot_{len(screenshots)+1}.jpg"
                                    final_path = os.path.join(output_dir, final_filename)
                                    os.rename(output_path, final_path)
                                    
                                    screenshots.append(final_path)
                                    print(f"  ✓ Frame at {timestamp}s saved: {final_filename}")
                                else:
                                    # Duplicate, remove
                                    os.remove(output_path)
                                    print(f"  ⚠ Frame at {timestamp}s is duplicate, skipping")
                        except subprocess.TimeoutExpired:
                            print(f"  ⚠ Timeout extracting frame at {timestamp}s")
                        except Exception as e:
                            print(f"  ⚠ Error at {timestamp}s: {str(e)[:50]}")
                            continue
            
            # Fallback: use thumbnails if we don't have enough frames
            if len(screenshots) < num_screenshots:
                print(f"  Need {num_screenshots - len(screenshots)} more images, trying thumbnails...")
                
                thumbnails = info.get('thumbnails', [])
                
                # Sort by quality (prefer maxres, then hq)
                thumb_priority = ['maxresdefault', 'sddefault', 'hqdefault', 'mqdefault']
                sorted_thumbs = sorted(
                    thumbnails,
                    key=lambda t: (
                        -next((i for i, p in enumerate(thumb_priority) if p in t.get('url', '')), 99),
                        -t.get('width', 0) * t.get('height', 0)
                    )
                )
                
                import requests
                
                for thumb in sorted_thumbs:
                    if len(screenshots) >= num_screenshots:
                        break
                        
                    thumb_url = thumb.get('url')
                    if not thumb_url:
                        continue
                    
                    try:
                        response = requests.get(thumb_url, timeout=10)
                        
                        if response.status_code == 200:
                            # Check for duplicates
                            img_hash = hashlib.md5(response.content).hexdigest()
                            
                            if img_hash not in seen_hashes:
                                seen_hashes.add(img_hash)
                                
                                output_filename = f"{video_id}_screenshot_{len(screenshots)+1}.jpg"
                                output_path = os.path.join(output_dir, output_filename)
                                
                                with open(output_path, 'wb') as f:
                                    f.write(response.content)
                                
                                screenshots.append(output_path)
                                size = f"{thumb.get('width', '?')}x{thumb.get('height', '?')}"
                                print(f"  ✓ Thumbnail saved: {output_filename} ({size})")
                    except Exception as e:
                        print(f"  ⚠ Thumbnail error: {e}")
                        continue
            
            if screenshots:
                print(f"✓ Successfully extracted {len(screenshots)} unique screenshots")
            else:
                print("⚠️ No screenshots extracted")
            
            return screenshots
    
    except Exception as e:
        print(f"❌ Screenshot extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []
