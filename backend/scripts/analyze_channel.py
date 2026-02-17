#!/usr/bin/env python3
"""
Standalone script — fetch YouTube channel videos and show 2026 titles.
No Django required. Just needs YOUTUBE_API_KEY env var.

Usage:
    railway run python3 scripts/analyze_channel.py
"""
import os
import sys
import requests

API_KEY = os.getenv('YOUTUBE_API_KEY')
if not API_KEY:
    print("❌ YOUTUBE_API_KEY not set")
    sys.exit(1)

BASE = "https://www.googleapis.com/youtube/v3"
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
MAX_VIDEOS = 200


def get_channel_id(channel_url):
    """Get channel ID from URL."""
    import re
    m = re.search(r'youtube\.com/channel/([a-zA-Z0-9_-]+)', channel_url)
    if m:
        return m.group(1)
    handle = None
    if '@' in channel_url:
        handle = channel_url.split('@')[1].split('/')[0]
    if handle:
        resp = requests.get(f"{BASE}/search", params={
            'part': 'id', 'q': handle, 'type': 'channel',
            'key': API_KEY, 'maxResults': 1
        })
        data = resp.json()
        if data.get('items'):
            return data['items'][0]['id']['channelId']
    return None


def main():
    # Try to get channel URL from DATABASE_URL if available
    db_url = os.getenv('DATABASE_URL')
    
    # Hardcoded fallback — check common channels
    # First try to get from DB
    channel_url = None
    channel_name = "Unknown"
    
    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT name, channel_url, channel_id FROM news_youtubechannel WHERE is_enabled = true LIMIT 1")
            row = cur.fetchone()
            if row:
                channel_name = row[0]
                channel_url = row[1]
                channel_id = row[2]
            conn.close()
        except Exception as e:
            print(f"⚠️ DB not available: {e}")
            print("   Pass channel URL as argument or set it below")
    
    if not channel_url:
        # Manual fallback
        if len(sys.argv) > 2:
            channel_url = sys.argv[2]
        else:
            print("❌ No channel found. Usage: python3 analyze_channel.py 2026 https://youtube.com/@ChannelName")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"📺 Channel: {channel_name}")
    print(f"   URL: {channel_url}")
    print(f"   Year filter: {YEAR}")
    print(f"{'='*70}\n")

    # Resolve channel ID
    if 'channel_id' not in dir() or not channel_id:
        channel_id = get_channel_id(channel_url)
    if not channel_id:
        print("❌ Could not resolve channel ID")
        sys.exit(1)

    # Get uploads playlist
    resp = requests.get(f"{BASE}/channels", params={
        'part': 'contentDetails,statistics', 'id': channel_id, 'key': API_KEY
    })
    data = resp.json()
    if not data.get('items'):
        print("❌ Channel not found")
        sys.exit(1)

    uploads = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    total = data['items'][0]['statistics'].get('videoCount', '?')
    print(f"  Total videos on channel: {total}")

    # Fetch videos with pagination
    all_videos = []
    next_page = None
    while len(all_videos) < MAX_VIDEOS:
        params = {
            'part': 'snippet,contentDetails', 'playlistId': uploads,
            'maxResults': min(50, MAX_VIDEOS - len(all_videos)),
            'key': API_KEY,
        }
        if next_page:
            params['pageToken'] = next_page

        resp = requests.get(f"{BASE}/playlistItems", params=params)
        page = resp.json()
        for item in page.get('items', []):
            s = item['snippet']
            vid = item['contentDetails']['videoId']
            pub = s['publishedAt'][:10]
            all_videos.append({
                'title': s['title'],
                'published': pub,
                'year': int(pub[:4]),
                'url': f"https://www.youtube.com/watch?v={vid}",
            })
        next_page = page.get('nextPageToken')
        if not next_page:
            break

    print(f"  Fetched: {len(all_videos)} videos")

    # Filter by year
    year_videos = [v for v in all_videos if v['year'] == YEAR]
    print(f"  Videos in {YEAR}: {len(year_videos)}\n")

    # Check against DB if available
    existing_urls = set()
    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT youtube_url FROM news_article WHERE youtube_url IS NOT NULL AND youtube_url != ''")
            existing_urls = {row[0] for row in cur.fetchall()}
            conn.close()
        except:
            pass

    has_article = [v for v in year_videos if v['url'] in existing_urls]
    missing = [v for v in year_videos if v['url'] not in existing_urls]

    if existing_urls:
        print(f"  ✅ Already have article ({len(has_article)}):")
        for v in has_article:
            print(f"     [{v['published']}] {v['title']}")

    print(f"\n  ❌ Missing — no article ({len(missing)}):")
    for v in missing:
        print(f"     [{v['published']}] {v['title']}")
        print(f"        {v['url']}")

    # Summary
    print(f"\n{'─'*70}")
    print(f"  📊 SUMMARY for {YEAR}:")
    print(f"     ✅ Have article:  {len(has_article)}")
    print(f"     ❌ Missing:       {len(missing)}")
    cov = (len(has_article) / len(year_videos) * 100) if year_videos else 0
    print(f"     📈 Coverage:      {cov:.0f}%")
    print(f"{'─'*70}\n")


if __name__ == '__main__':
    main()
