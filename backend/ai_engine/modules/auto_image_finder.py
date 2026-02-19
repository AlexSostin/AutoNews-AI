"""
Auto-image finder for articles.

Pipeline:  search press photos → pick best → (optional) AI generate from reference
Modes: search_first | ai_only | search_only | off
"""
import logging
import requests as http_requests
from django.core.files.base import ContentFile

logger = logging.getLogger('news')


def find_and_attach_image(article, pending_article=None):
    """
    Automatically find/generate an image and attach it to an Article.
    
    Uses the settings from AutomationSettings to determine the mode.
    Called by auto_publisher right after publish_article() creates the Article.
    
    Args:
        article: The published Article instance (must already be saved)
        pending_article: Optional PendingArticle for metadata (specs, title, etc.)
    
    Returns:
        dict: {'success': bool, 'method': str, 'error': str|None}
    """
    from news.models import AutomationSettings
    
    settings = AutomationSettings.load()
    mode = settings.auto_image_mode
    prefer_press = settings.auto_image_prefer_press
    
    if mode == 'off':
        return {'success': False, 'method': 'off', 'error': 'Auto-image disabled'}
    
    # If article already has an image, skip
    if article.image and str(article.image) and len(str(article.image)) > 5:
        logger.info(f"📸 Article already has image, skipping auto-image: {article.title[:50]}")
        return {'success': True, 'method': 'existing', 'error': None}
    
    # Build search query from article
    car_name = _get_car_name(article, pending_article)
    
    # --- Strategy: search_first or search_only ---
    if mode in ('search_first', 'search_only'):
        result = _try_search_photo(article, car_name, prefer_press)
        if result['success']:
            return result
        
        # If search_only, don't fallback to AI
        if mode == 'search_only':
            logger.info(f"📸 No photos found (search_only), skipping: {car_name}")
            return {'success': False, 'method': 'search_only', 'error': 'No suitable photos found'}
        
        # Fallback to AI generation
        logger.info(f"📸 No photos found, falling back to AI generation: {car_name}")
        return _try_ai_generate(article, car_name)
    
    # --- Strategy: ai_only ---
    if mode == 'ai_only':
        # Need a reference image first — try search to get one
        ref_result = _try_search_photo(article, car_name, prefer_press, save_to_article=False)
        if ref_result.get('image_url'):
            return _try_ai_generate(article, car_name, reference_url=ref_result['image_url'])
        else:
            logger.info(f"📸 No reference found for AI generation: {car_name}")
            return {'success': False, 'method': 'ai_only', 'error': 'No reference image found for AI generation'}
    
    return {'success': False, 'method': mode, 'error': f'Unknown mode: {mode}'}


def _get_car_name(article, pending_article=None):
    """Extract the best car name for image search."""
    # Try CarSpecification first
    try:
        spec = article.car_specification
        if spec and spec.make and spec.model:
            year = spec.year or ''
            return f"{year} {spec.make} {spec.model}".strip()
    except Exception:
        pass
    
    # Try pending_article specs
    if pending_article and pending_article.specs:
        specs = pending_article.specs
        make = specs.get('make', specs.get('Make', ''))
        model = specs.get('model', specs.get('Model', ''))
        year = specs.get('year', specs.get('Year', ''))
        if make and model:
            return f"{year} {make} {model}".strip()
    
    # Fallback to title
    import re
    title = article.title
    # Remove common noise words
    noise_words = ['EV', 'PHEV', 'BEV', 'SUV', 'Review', 'Test', 'Drive',
                   'Range', 'Specs', 'Price', 'vs', 'and', 'the', 'new', 'all-new']
    cleaned = title
    for word in noise_words:
        cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{2,4}(km|hp|kw|ps|mph|kph|kwh|mi)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if len(cleaned) > 5 else title


def _try_search_photo(article, car_name, prefer_press=True, save_to_article=True):
    """
    Search for a photo and optionally save it to the article.
    
    If prefer_press is True, picks the first editorial/press photo (green-highlighted).
    Otherwise picks the highest-resolution photo.
    
    Returns dict with success, method, image_url, error.
    """
    try:
        from ai_engine.modules.searcher import search_car_images
    except ImportError:
        return {'success': False, 'method': 'search', 'error': 'searcher module not available'}
    
    query = f"{car_name} press photo official"
    results = search_car_images(query, max_results=15)
    
    if not results:
        return {'success': False, 'method': 'search', 'error': 'No search results'}
    
    # Pick best photo
    selected = None
    
    if prefer_press:
        # First try: editorial/press photos (green-highlighted ones)
        press_photos = [r for r in results if r.get('is_press')]
        if press_photos:
            selected = press_photos[0]
            logger.info(f"📸 Found press photo: {selected['source']}")
    
    if not selected:
        # Fallback: pick the largest photo by resolution
        results_sorted = sorted(results, key=lambda x: -(x.get('width', 0) * x.get('height', 0)))
        selected = results_sorted[0]
        logger.info(f"📸 Using largest photo: {selected.get('width', '?')}x{selected.get('height', '?')}")
    
    image_url = selected['url']
    
    if not save_to_article:
        return {'success': True, 'method': 'search', 'image_url': image_url, 'error': None}
    
    # Download and save to article
    return _download_and_save(article, image_url, method='search')


def _try_ai_generate(article, car_name, reference_url=None):
    """
    Generate an AI image using Gemini and save to article.
    Needs a reference image — either from article.image or from reference_url.
    """
    try:
        from ai_engine.modules.image_generator import generate_car_image
    except ImportError:
        return {'success': False, 'method': 'ai_generate', 'error': 'image_generator module not available'}
    
    # Determine reference URL
    ref_url = reference_url
    if not ref_url:
        if article.image and str(article.image):
            img_str = str(article.image)
            if img_str.startswith('http'):
                ref_url = img_str
    
    if not ref_url:
        # Try to find a reference via search first
        try:
            from ai_engine.modules.searcher import search_car_images
            results = search_car_images(f"{car_name} press photo", max_results=5)
            if results:
                ref_url = results[0]['url']
        except Exception:
            pass
    
    if not ref_url:
        return {'success': False, 'method': 'ai_generate', 'error': 'No reference image available'}
    
    logger.info(f"🎨 Generating AI image for: {car_name}")
    result = generate_car_image(ref_url, car_name, style='scenic_road')
    
    if not result.get('success'):
        error = result.get('error', 'Unknown error')
        logger.warning(f"🎨 AI generation failed: {error}")
        
        # Fallback: if we have a reference URL, just use that as the photo
        if reference_url:
            logger.info(f"📸 Falling back to reference photo instead of AI")
            return _download_and_save(article, reference_url, method='ai_fallback_to_search')
        
        return {'success': False, 'method': 'ai_generate', 'error': error}
    
    # Save AI-generated image
    import base64
    try:
        image_bytes = base64.b64decode(result['image_data'])
        ext = 'png' if 'png' in result.get('mime_type', '') else 'jpg'
        filename = f"auto_ai_{article.id}_{car_name[:30].replace(' ', '_')}.{ext}"
        image_file = ContentFile(image_bytes, name=filename)
        article.image.save(filename, image_file, save=True)
        
        logger.info(f"✅ AI image saved for: {article.title[:50]}")
        return {'success': True, 'method': 'ai_generate', 'error': None}
    except Exception as e:
        logger.error(f"❌ Failed to save AI image: {e}")
        return {'success': False, 'method': 'ai_generate', 'error': str(e)}


def _download_and_save(article, image_url, method='search'):
    """Download an image URL and save it as the article's featured image."""
    try:
        resp = http_requests.get(image_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*,*/*;q=0.8',
        })
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        if 'image' not in content_type:
            return {'success': False, 'method': method, 'error': f'Not an image: {content_type}'}
        
        ext = 'jpg'
        if 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'
        
        slug_short = article.slug[:60] if article.slug else f'article_{article.id}'
        filename = f"auto_{slug_short}.{ext}"
        image_file = ContentFile(resp.content, name=filename)
        article.image.save(filename, image_file, save=True)
        
        logger.info(f"✅ Auto-image saved ({method}): {article.title[:50]}")
        return {'success': True, 'method': method, 'error': None}
        
    except http_requests.RequestException as e:
        logger.warning(f"❌ Image download failed: {e}")
        return {'success': False, 'method': method, 'error': str(e)}
    except Exception as e:
        logger.error(f"❌ Image save failed: {e}")
        return {'success': False, 'method': method, 'error': str(e)}
