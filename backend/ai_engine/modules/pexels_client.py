"""
Pexels API Client for Automotive Image Search

Free API with generous limits:
- 200 requests/hour
- 20,000 requests/month
- No credit card required

Documentation: https://www.pexels.com/api/documentation/
"""
import os
import re
import requests
import hashlib
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuration
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY', '')
PEXELS_API_URL = 'https://api.pexels.com/v1'
PEXELS_ENABLED = bool(PEXELS_API_KEY)

# Image quality settings
IMAGE_SIZE = 'large'  # large, medium, small, original
RESULTS_PER_PAGE = 5  # Get multiple options to choose best one

# Rate limiting
REQUEST_CACHE = {}  # Simple in-memory cache
CACHE_DURATION = timedelta(hours=24)


class PexelsClient:
    """Client for Pexels API image search"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or PEXELS_API_KEY
        if not self.api_key:
            logger.warning('Pexels API key not configured')
        
        self.headers = {
            'Authorization': self.api_key
        }
    
    def search_photos(self, query: str, per_page: int = RESULTS_PER_PAGE) -> Optional[Dict]:
        """
        Search for photos on Pexels.
        
        Args:
            query: Search query (e.g., "Tesla Model 3 electric car")
            per_page: Number of results to return
            
        Returns:
            API response dict or None if error
        """
        if not self.api_key:
            logger.error('Pexels API key not configured')
            return None
        
        # Check cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in REQUEST_CACHE:
            cached_data, cached_time = REQUEST_CACHE[cache_key]
            if datetime.now() - cached_time < CACHE_DURATION:
                logger.info(f'Using cached Pexels result for: {query}')
                return cached_data
        
        try:
            url = f'{PEXELS_API_URL}/search'
            params = {
                'query': query,
                'per_page': per_page,
                'orientation': 'landscape',  # Better for articles
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the result
            REQUEST_CACHE[cache_key] = (data, datetime.now())
            
            logger.info(f'Pexels search successful: {query} - {data.get("total_results", 0)} results')
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f'Pexels API error: {e}')
            return None
    
    def get_best_photo_url(self, search_results: Dict, size: str = IMAGE_SIZE) -> Optional[str]:
        """
        Extract the best photo URL from search results.
        
        Args:
            search_results: Pexels API response
            size: Image size (large, medium, small, original)
            
        Returns:
            Image URL or None
        """
        if not search_results or 'photos' not in search_results:
            return None
        
        photos = search_results.get('photos', [])
        if not photos:
            return None
        
        # Get first photo (most relevant)
        photo = photos[0]
        
        # Get URL for requested size
        src = photo.get('src', {})
        image_url = src.get(size) or src.get('large') or src.get('original')
        
        if image_url:
            logger.info(f'Selected Pexels image: {image_url}')
        
        return image_url


def extract_keywords(title: str, content: str = '', brand: str = '') -> str:
    """
    Extract smart keywords from article title and content.
    
    Args:
        title: Article title
        content: Article content (optional)
        brand: Brand name (optional)
        
    Returns:
        Optimized search query
    """
    # Common automotive keywords to enhance search
    automotive_terms = ['car', 'vehicle', 'automobile', 'automotive']
    
    # Extract brand if not provided
    if not brand:
        # Common automotive brands
        brands = [
            'Tesla', 'Ford', 'Toyota', 'BMW', 'Mercedes', 'Audi', 'Volkswagen',
            'Honda', 'Nissan', 'Chevrolet', 'Porsche', 'Ferrari', 'Lamborghini',
            'Lexus', 'Mazda', 'Hyundai', 'Kia', 'Volvo', 'Jaguar', 'Land Rover'
        ]
        
        for b in brands:
            if b.lower() in title.lower():
                brand = b
                break
    
    # Build query
    query_parts = []
    
    # Add brand if found
    if brand:
        query_parts.append(brand)
    
    # Extract model/key terms from title
    # Remove common words
    stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    words = re.findall(r'\b[A-Z][a-z]+\b|\b[A-Z]+\b|\b\d+\b', title)
    
    # Add significant words (capitalized or numbers)
    for word in words[:3]:  # Limit to 3 words
        if word.lower() not in stop_words and word.lower() != brand.lower():
            query_parts.append(word)
    
    # Add automotive context if not already present
    query_lower = ' '.join(query_parts).lower()
    if not any(term in query_lower for term in automotive_terms):
        query_parts.append('car')
    
    query = ' '.join(query_parts)
    
    logger.info(f'Extracted keywords: "{query}" from title: "{title}"')
    return query


def search_automotive_image(title: str, brand: str = '', content: str = '') -> Optional[str]:
    """
    Search for relevant automotive image using Pexels API.
    
    Args:
        title: Article title
        brand: Brand name (optional)
        content: Article content (optional)
        
    Returns:
        Image URL or None if not found
    """
    if not PEXELS_ENABLED:
        logger.warning('Pexels API not enabled (missing API key)')
        return None
    
    client = PexelsClient()
    
    # Extract smart keywords
    query = extract_keywords(title, content, brand)
    
    # Search with primary query
    results = client.search_photos(query)
    image_url = client.get_best_photo_url(results)
    
    if image_url:
        return image_url
    
    # Fallback: Try with just brand + "car"
    if brand:
        fallback_query = f'{brand} car'
        logger.info(f'Trying fallback query: {fallback_query}')
        results = client.search_photos(fallback_query)
        image_url = client.get_best_photo_url(results)
        
        if image_url:
            return image_url
    
    # Final fallback: Generic automotive
    logger.info('Trying generic automotive query')
    results = client.search_photos('luxury car automotive')
    image_url = client.get_best_photo_url(results)
    
    return image_url


def test_pexels_connection():
    """Test Pexels API connection"""
    if not PEXELS_ENABLED:
        print('❌ Pexels API key not configured')
        print('Set PEXELS_API_KEY in your .env file')
        return False
    
    print('🔍 Testing Pexels API connection...')
    
    # Test search
    image_url = search_automotive_image('Tesla Model 3 Electric Car', brand='Tesla')
    
    if image_url:
        print(f'✅ Pexels API working!')
        print(f'📸 Found image: {image_url}')
        return True
    else:
        print('❌ Pexels API test failed')
        return False


if __name__ == '__main__':
    # Test the module
    test_pexels_connection()
