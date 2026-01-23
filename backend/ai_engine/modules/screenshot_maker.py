import os
import hashlib
import requests
import yt_dlp


def get_image_hash_from_bytes(data):
    """Get MD5 hash from bytes"""
    return hashlib.md5(data).hexdigest()


def extract_screenshots_simple(youtube_url, output_dir, num_screenshots=3):
    """
    Extract screenshots from YouTube video.
    Uses YouTube thumbnails (reliable) - gets unique thumbnails only.
    
    Args:
        youtube_url: YouTube video URL
        output_dir: Directory to save screenshots
        num_screenshots: Number of screenshots to extract (default 3)
    
    Returns:
        List of screenshot file paths (may be less than requested if not enough unique thumbnails)
    """
    print(f"📸 Extracting unique screenshots from YouTube video...")
    
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
            thumbnails = info.get('thumbnails', [])
            
            print(f"  Video ID: {video_id}")
            print(f"  Found {len(thumbnails)} thumbnail options")
            
            if not thumbnails:
                print("  ❌ No thumbnails available")
                return []
            
            # Sort thumbnails by quality and uniqueness
            # Prefer: maxresdefault > sddefault > hqdefault > mqdefault > default
            def get_quality_score(thumb):
                url = thumb.get('url', '')
                width = thumb.get('width', 0)
                height = thumb.get('height', 0)
                
                # Priority by name (unique thumbnails have higher priority)
                if 'maxresdefault' in url:
                    return 1000000 + width * height
                if 'sddefault' in url:
                    return 500000 + width * height
                if 'hqdefault' in url or 'hq720' in url:
                    return 200000 + width * height
                if 'mqdefault' in url:
                    return 100000 + width * height
                if 'default' in url:
                    return 50000 + width * height
                
                # Fallback to resolution
                return width * height
            
            sorted_thumbs = sorted(thumbnails, key=get_quality_score, reverse=True)
            
            # Download unique thumbnails only
            for thumb in sorted_thumbs:
                if len(screenshots) >= num_screenshots:
                    break
                    
                thumb_url = thumb.get('url')
                if not thumb_url:
                    continue
                
                # Skip very small thumbnails
                width = thumb.get('width', 0)
                if width > 0 and width < 300:
                    continue
                
                try:
                    response = requests.get(thumb_url, timeout=15)
                    
                    if response.status_code == 200 and len(response.content) > 5000:
                        # Check for duplicates by hash
                        img_hash = get_image_hash_from_bytes(response.content)
                        
                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)
                            
                            output_filename = f"{video_id}_screenshot_{len(screenshots)+1}.jpg"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            with open(output_path, 'wb') as f:
                                f.write(response.content)
                            
                            screenshots.append(output_path)
                            size = f"{thumb.get('width', '?')}x{thumb.get('height', '?')}"
                            print(f"  ✓ Unique screenshot {len(screenshots)} saved: {output_filename} ({size}, {len(response.content)//1024}KB)")
                        else:
                            print(f"  ⚠ Skipping duplicate thumbnail (hash: {img_hash[:8]}...)")
                            
                except requests.RequestException as e:
                    print(f"  ⚠ Error downloading thumbnail: {e}")
                    continue
            
            if screenshots:
                print(f"✓ Got {len(screenshots)} unique screenshot(s)")
            else:
                print("⚠️ No unique screenshots could be downloaded")
            
            return screenshots
    
    except Exception as e:
        print(f"❌ Screenshot extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


# Backwards compatibility alias
def extract_screenshots(youtube_url, output_dir, num_screenshots=3):
    return extract_screenshots_simple(youtube_url, output_dir, num_screenshots)
