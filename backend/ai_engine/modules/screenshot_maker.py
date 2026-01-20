import os
import yt_dlp
import sys

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
    Simplified version using yt-dlp's built-in thumbnail extraction.
    Returns list of screenshot file paths.
    """
    print(f"📸 Extracting thumbnails from video...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        ydl_opts = {
            'skip_download': True,
            'writethumbnail': True,
            'outtmpl': os.path.join(output_dir, '%(id)s_thumb.%(ext)s'),
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Get all available thumbnails
            thumbnails = info.get('thumbnails', [])
            
            if not thumbnails:
                print("❌ No thumbnails available")
                return []
            
            # Filter for high quality thumbnails only (width >= 1280)
            high_quality = [t for t in thumbnails if t.get('width', 0) >= 1280]
            
            # If no high quality, use best available
            if not high_quality:
                high_quality = sorted(thumbnails, key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)[:num_screenshots]
            
            # Download top quality thumbnails
            screenshots = []
            video_id = info.get('id', 'video')
            
            # Get only high quality thumbnails
            for i in range(min(num_screenshots, len(high_quality))):
                thumb = high_quality[i]
                thumb_url = thumb.get('url')
                
                if thumb_url:
                    import requests
                    response = requests.get(thumb_url, timeout=10)
                    
                    if response.status_code == 200:
                        output_filename = f"{video_id}_screenshot_{i+1}.jpg"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        
                        screenshots.append(output_path)
                        print(f"  ✓ Screenshot {i+1} saved: {output_filename} ({thumb.get('width')}x{thumb.get('height')})")
            
            # If we need more screenshots but don't have enough high quality ones, use the same one
            while len(screenshots) < num_screenshots and screenshots:
                duplicate_path = screenshots[0]
                base, ext = os.path.splitext(duplicate_path)
                new_path = f"{os.path.dirname(base)}/{video_id}_screenshot_{len(screenshots)+1}{ext}"
                
                import shutil
                shutil.copy(duplicate_path, new_path)
                screenshots.append(new_path)
                print(f"  ✓ Screenshot {len(screenshots)} saved (duplicate): {os.path.basename(new_path)}")
            
            if screenshots:
                print(f"✓ Successfully extracted {len(screenshots)} screenshots")
                return screenshots
            else:
                print("⚠️ No screenshots extracted")
                return []
    
    except Exception as e:
        print(f"❌ Screenshot extraction failed: {e}")
        return []
