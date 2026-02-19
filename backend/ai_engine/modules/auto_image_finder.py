"""
Auto-image finder for articles.

Logic:
  1. Search for ANY car photo (press or not) as a REFERENCE
  2. Use that reference to generate an AI image via Gemini
  3. Save only the AI-generated image (never the found photo — copyright)
  4. If no reference found at all → skip, do nothing
"""
import logging
import base64
import requests as http_requests
from django.core.files.base import ContentFile

logger = logging.getLogger('news')


def find_and_attach_image(article, pending_article=None):
    """
    Find a reference photo online, then generate an AI image from it.
    
    Flow:
      search_car_images() → pick best reference → generate_car_image() → save
    
    Args:
        article: The published Article instance (must already be saved)
        pending_article: Optional PendingArticle for metadata (specs, title)
    
    Returns:
        dict: {'success': bool, 'method': str, 'error': str|None}
    """
    from news.models import AutomationSettings
    
    settings = AutomationSettings.load()
    
    if settings.auto_image_mode == 'off':
        return {'success': False, 'method': 'off', 'error': 'Auto-image disabled'}
    
    # If article already has an image, skip
    if article.image and str(article.image) and len(str(article.image)) > 5:
        logger.info(f"[AUTO-IMAGE] Article already has image, skipping: {article.title[:50]}")
        return {'success': True, 'method': 'existing', 'error': None}
    
    # Build search query
    car_name = _get_car_name(article, pending_article)
    
    # Step 1: Find a reference photo (any photo — green or yellow)
    reference_url = _find_reference_photo(car_name, settings.auto_image_prefer_press)
    
    if not reference_url:
        logger.info(f"[AUTO-IMAGE/SEARCH] No reference found for: {car_name}")
        return {'success': False, 'method': 'no_reference', 'error': f'No reference photo found for {car_name}'}
    
    # Step 2: Generate AI image from reference
    return _generate_ai_image(article, car_name, reference_url)


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
    
    # Fallback to cleaned title
    import re
    title = article.title
    noise_words = ['EV', 'PHEV', 'BEV', 'SUV', 'Review', 'Test', 'Drive',
                   'Range', 'Specs', 'Price', 'vs', 'and', 'the', 'new', 'all-new']
    cleaned = title
    for word in noise_words:
        cleaned = re.sub(rf'\b{word}\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{2,4}(km|hp|kw|ps|mph|kph|kwh|mi)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if len(cleaned) > 5 else title


def _find_reference_photo(car_name, prefer_press=True):
    """
    Search for any car photo to use as reference for AI generation.
    
    Tries press (green) photos first if prefer_press=True,
    then falls back to ANY photo (yellow/unknown) — they're all usable as AI references.
    
    Returns: image URL string or None
    """
    try:
        from ai_engine.modules.searcher import search_car_images
    except ImportError:
        logger.warning("[AUTO-IMAGE/SEARCH] searcher module not available")
        return None
    
    query = f"{car_name} press photo official"
    results = search_car_images(query, max_results=15)
    
    if not results:
        # Try a broader search
        results = search_car_images(f"{car_name} car photo", max_results=10)
    
    if not results:
        return None
    
    # Pick best reference
    if prefer_press:
        # Try press/editorial first (green-highlighted)
        press = [r for r in results if r.get('is_press')]
        if press:
            logger.info(f"[AUTO-IMAGE/SEARCH] Using press photo as reference: {press[0].get('source', '?')}")
            return press[0]['url']
    
    # Fall back to any photo — yellow zone is fine as reference for AI
    # Sort by resolution (biggest = best quality reference)
    results_sorted = sorted(results, key=lambda x: -(x.get('width', 0) * x.get('height', 0)))
    selected = results_sorted[0]
    logger.info(f"[AUTO-IMAGE/SEARCH] Using photo as reference: {selected.get('width', '?')}x{selected.get('height', '?')} from {selected.get('source', '?')}")
    return selected['url']


def _generate_ai_image(article, car_name, reference_url):
    """
    Generate a photorealistic AI image from a reference photo and save to article.
    """
    try:
        from ai_engine.modules.image_generator import generate_car_image
    except ImportError:
        return {'success': False, 'method': 'ai_generate', 'error': 'image_generator module not available'}
    
    logger.info(f"[AUTO-IMAGE/AI] Generating image for: {car_name}")
    result = generate_car_image(reference_url, car_name, style='scenic_road')
    
    if not result.get('success'):
        error = result.get('error', 'Unknown error')
        logger.warning(f"[AUTO-IMAGE/AI] Generation failed: {error}")
        return {'success': False, 'method': 'ai_generate', 'error': error}
    
    # Save the AI-generated image to article
    try:
        image_bytes = base64.b64decode(result['image_data'])
        ext = 'png' if 'png' in result.get('mime_type', '') else 'jpg'
        slug_short = article.slug[:50] if article.slug else f'article_{article.id}'
        filename = f"ai_{slug_short}.{ext}"
        image_file = ContentFile(image_bytes, name=filename)
        article.image.save(filename, image_file, save=True)
        
        logger.info(f"[AUTO-IMAGE/AI] ✅ Saved for: {article.title[:50]} ({len(image_bytes)} bytes)")
        return {'success': True, 'method': 'ai_generate', 'error': None}
    except Exception as e:
        logger.error(f"[AUTO-IMAGE/AI] ❌ Failed to save: {e}", exc_info=True)
        return {'success': False, 'method': 'ai_generate', 'error': str(e)}
