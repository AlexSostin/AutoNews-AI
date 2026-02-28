import os
import requests
from datetime import datetime, timedelta
import re

class YouTubeClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        if not self.api_key:
            print("⚠️ Warning: YOUTUBE_API_KEY not found in environment variables")

    def _get_channel_id(self, channel_url):
        """Extract or fetch channel ID from URL"""
        # 1. Try to find channel ID in URL (if it's already an ID)
        match = re.search(r'youtube\.com/channel/([a-zA-Z0-9_-]+)', channel_url)
        if match:
            return match.group(1)
            
        # 2. If it's a handle (@Username) or custom URL (/c/), use forHandle API
        handle = None
        if '@' in channel_url:
            handle = channel_url.split('@')[1].split('/')[0]
        elif 'youtube.com/c/' in channel_url:
            handle = channel_url.split('/c/')[1].split('/')[0]
        elif 'youtube.com/user/' in channel_url:
            username = channel_url.split('/user/')[1].split('/')[0]
            # /user/ URLs — try forHandle first, then fallback to search
            channel_id = self._resolve_handle(username)
            if channel_id:
                return channel_id
            return self._search_channel_id(username)

        if handle:
            channel_id = self._resolve_handle(handle)
            if channel_id:
                return channel_id
            # Fallback to search if forHandle fails
            print(f"⚠️ forHandle failed for '{handle}', falling back to search")
            return self._search_channel_id(handle)
            
        return None

    def _resolve_handle(self, handle):
        """Resolve a YouTube handle to channel ID using Channels API forHandle param.
        Costs only 1 quota unit vs 100 for search."""
        if not self.api_key:
            return None

        # Ensure handle has @ prefix
        if not handle.startswith('@'):
            handle = f'@{handle}'

        url = f"{self.base_url}/channels"
        params = {
            'part': 'id',
            'forHandle': handle,
            'key': self.api_key,
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    channel_id = data['items'][0]['id']
                    print(f"✅ Resolved handle '{handle}' → {channel_id}")
                    return channel_id
            else:
                print(f"⚠️ forHandle API returned {response.status_code} for '{handle}'")
        except Exception as e:
            print(f"Error resolving handle '{handle}': {e}")

        return None

    def _search_channel_id(self, query):
        """Search for channel ID by query — fallback only (costs 100 quota units)"""
        if not self.api_key:
            return None
            
        url = f"{self.base_url}/search"
        params = {
            'part': 'id,snippet',
            'q': query,
            'type': 'channel',
            'key': self.api_key,
            'maxResults': 1
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    return data['items'][0]['id']['channelId']
        except Exception as e:
            print(f"Error searching channel: {e}")
            
        return None

    def get_latest_videos(self, channel_identifier, max_results=5):
        """
        Get latest videos from a channel.
        channel_identifier can be a URL or ID.
        """
        if not self.api_key:
            raise Exception("YOUTUBE_API_KEY is required")

        # Determine channel ID
        channel_id = channel_identifier
        
        if 'youtube.com' in channel_identifier or 'youtu.be' in channel_identifier:
            channel_id = self._get_channel_id(channel_identifier)
        elif not channel_identifier.startswith('UC'):
            # If it's not a URL and not a standard UC-ID, try searching as handle/name
            print(f"Input '{channel_identifier}' is not a URL or Channel ID. Searching...")
            channel_id = self._search_channel_id(channel_identifier)
            
        if not channel_id:
            print(f"Could not resolve channel ID for {channel_identifier}")
            raise Exception(f"Could not resolve Channel ID for '{channel_identifier}'. Please check the URL.")

        # Get channel's "uploads" playlist ID
        url = f"{self.base_url}/channels"
        params = {
            'part': 'contentDetails',
            'id': channel_id,
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"Error fetching channel info: {response.text}")
                raise Exception(f"YouTube API Error: {response.status_code} - {response.text}")
                
            data = response.json()
            if not data.get('items'):
                print(f"Channel not found: {channel_id}")
                raise Exception(f"Channel not found on YouTube (ID: {channel_id})")
                
            uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Fetch videos from uploads playlist
            return self._get_playlist_items(uploads_playlist_id, max_results)
            
        except Exception as e:
            print(f"Error getting videos: {e}")
            raise e

    def _get_playlist_items(self, playlist_id, max_results):
        url = f"{self.base_url}/playlistItems"
        params = {
            'part': 'snippet,contentDetails',
            'playlistId': playlist_id,
            'maxResults': max_results,
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                raise Exception(f"Error fetching playlist: {response.status_code}")
                
            data = response.json()
            videos = []
            
            for item in data.get('items', []):
                snippet = item['snippet']
                video_id = item['contentDetails']['videoId']
                published_at = snippet['publishedAt']
                
                videos.append({
                    'id': video_id,
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'thumbnail': snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url'],
                    'published_at': published_at,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
                
            return videos
            
        except Exception as e:
            print(f"Error fetching playlist items: {e}")
            raise e
