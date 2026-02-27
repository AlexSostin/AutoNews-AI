"""
AI Auto News Generator — Orchestrator.

This is the main entry point for article generation. It orchestrates the
generation pipeline and provides two workflows:

1. generate_article_from_youtube() — Direct publish (legacy/manual flow)
2. create_pending_article() — PendingArticle creation (new flow used by scheduler)

All heavy logic has been extracted into focused modules:
- modules/title_utils.py — Title validation/extraction
- modules/duplicate_checker.py — Duplicate detection
- modules/content_generator.py — Article generation pipeline
- modules/ab_variants.py — A/B title variant generation
"""
import argparse
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import config
try:
    from ai_engine.config import GROQ_API_KEY
except ImportError:
    try:
        from config import GROQ_API_KEY
    except ImportError:
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Import publisher
try:
    from ai_engine.modules.publisher import publish_article
except ImportError:
    from modules.publisher import publish_article

# ═══════════════════════════════════════════════════════════════════════════
# Backward-compatible re-exports
# All existing `from ai_engine.main import X` continue to work unchanged.
# ═══════════════════════════════════════════════════════════════════════════
try:
    from ai_engine.modules.title_utils import (
        GENERIC_SECTION_HEADERS, _is_generic_header, _contains_non_latin,
        validate_title, extract_title,
    )
    from ai_engine.modules.duplicate_checker import check_duplicate, check_car_duplicate
    from ai_engine.modules.content_generator import _generate_article_content
    from ai_engine.modules.ab_variants import generate_title_variants
except ImportError:
    from modules.title_utils import (
        GENERIC_SECTION_HEADERS, _is_generic_header, _contains_non_latin,
        validate_title, extract_title,
    )
    from modules.duplicate_checker import check_duplicate, check_car_duplicate
    from modules.content_generator import _generate_article_content
    from modules.ab_variants import generate_title_variants


# ═══════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main(youtube_url):
    print(f"Starting pipeline for: {youtube_url}")
    
    article_html = "<h2>2026 Future Car Review</h2><p>This is a generated article with a mockup image.</p>"
    
    title = extract_title(article_html)
    publish_article(title, article_html)
    
    print("Pipeline finished.")


# ═══════════════════════════════════════════════════════════════════════════
# Workflow 1: Direct Publish (legacy/manual)
# ═══════════════════════════════════════════════════════════════════════════

def generate_article_from_youtube(youtube_url, task_id=None, provider='gemini', is_published=True):
    """Generate and publish immediately (LEGACY/MANUAL flow)"""
    
    # 0. Check duplicate first
    existing = check_duplicate(youtube_url)
    if existing:
        return {
            'success': False,
            'error': f'Article already exists: {existing.title}',
            'article_id': existing.id,
            'duplicate': True
        }
        
    result = _generate_article_content(youtube_url, task_id, provider)
    
    if not result['success']:
        return result
        
    # Publish to DB
    print(f"📤 Publishing article... (Published: {is_published})")
    article = publish_article(
        title=result['title'],
        content=result['content'],
        summary=result['summary'],
        category_name=result['category_name'],
        youtube_url=youtube_url,
        image_paths=result['image_paths'],
        tag_names=result['tag_names'],
        specs=result['specs'],
        is_published=is_published,
        meta_keywords=result['meta_keywords'],
        author_name=result.get('author_name', ''),
        author_channel_url=result.get('author_channel_url', ''),
        generation_metadata=result.get('generation_metadata')
    )
    
    print(f"✅ Article created! ID: {article.id}, Slug: {article.slug}")
    
    # Generate A/B title variants
    generate_title_variants(article, provider=provider)
    
    # Deep specs enrichment — auto-fill VehicleSpecs card (/cars/{brand}/{model})
    try:
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        generate_deep_vehicle_specs(
            article,
            specs=result.get('specs'),
            web_context=result.get('web_context', ''),
            provider=provider
        )
    except Exception as e:
        print(f"⚠️ Deep specs enrichment failed: {e}")
    
    return {
        'success': True,
        'article_id': article.id,
        'title': result['title'],
        'slug': article.slug,
        'category': result['category_name'],
        'tags': result['tag_names']
    }


# ═══════════════════════════════════════════════════════════════════════════
# Workflow 2: Pending Article (new scheduler flow)
# ═══════════════════════════════════════════════════════════════════════════

def create_pending_article(youtube_url, channel_id, video_title, video_id, provider='gemini'):
    """Generate article and save as PendingArticle (NEW flow)"""
    
    # Setup Django
    import django
    if not django.apps.apps.ready:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
        django.setup()
        
    from news.models import PendingArticle, YouTubeChannel, Category, Article
    from django.utils import timezone
    
    # 1. Check if article exists (only non-deleted)
    existing = Article.objects.filter(youtube_url=youtube_url, is_deleted=False).exists()
    if existing:
        print(f"Skipping {youtube_url} - already exists")
        return {'success': False, 'reason': 'exists', 'error': 'Article already exists in the database'}
        
    # 2. Check if already pending for this video_id (skip if rejected/published — allows re-generation)
    if video_id:
        pending_exists = PendingArticle.objects.filter(
            video_id=video_id
        ).exclude(status__in=['rejected', 'published', 'auto_failed']).exists()
        if pending_exists:
            print(f"Skipping {youtube_url} - PendingArticle already exists for video_id={video_id}")
            return {'success': False, 'reason': 'pending', 'error': 'Article is already in the pending queue'}
    
    # 3. Generate content
    result = _generate_article_content(youtube_url, task_id=None, provider=provider, video_title=video_title)
    
    if not result['success']:
        return result

    # 4. Get Channel and Category
    try:
        channel = YouTubeChannel.objects.get(id=channel_id)
        default_category = channel.default_category
    except YouTubeChannel.DoesNotExist:
        channel = None
        default_category = None
        
    # Find category by name if no default
    if not default_category and result['category_name']:
         try:
             default_category = Category.objects.get(name__iexact=result['category_name'])
         except Category.DoesNotExist:
             pass

    # 5. Create PendingArticle (with race-condition safety)
    # Ensure video_id and video_title are present (DB requirements)
    final_video_title = result.get('video_title') or video_title or "Untitled YouTube Video"
    
    if not video_id:
        # Try to extract from URL
        id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
        video_id = id_match.group(1) if id_match else f"ext_{int(timezone.now().timestamp())}"

    try:
        # Re-check right before create to minimize race window
        if video_id and PendingArticle.objects.filter(
            video_id=video_id
        ).exclude(status__in=['rejected', 'published', 'auto_failed']).exists():
            print(f"Skipping {youtube_url} - duplicate detected after content generation")
            return {'success': False, 'reason': 'pending', 'error': 'Duplicate detected'}

        pending = PendingArticle.objects.create(
            youtube_channel=channel,
            video_url=youtube_url,
            video_id=video_id,
            video_title=final_video_title[:500],
            title=result['title'],
            content=result['content'],
            excerpt=result['summary'],
            suggested_category=default_category,
            images=result['image_paths'],  # JSON field
            featured_image=result['image_paths'][0] if result['image_paths'] else '',
            image_source='youtube',
            author_name=result.get('author_name', ''),
            author_channel_url=result.get('author_channel_url', ''),
            
            # Save structured data for draft safety
            specs=result['specs'],
            tags=result['tag_names'],
            
            status='pending'
        )
    except Exception as e:
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            print(f"Skipping {youtube_url} - DB unique constraint caught duplicate")
            return {'success': False, 'reason': 'pending', 'error': 'Duplicate video_id'}
        raise
    
    print(f"✅ Created PendingArticle: {pending.title}")
    return {'success': True, 'pending_id': pending.id}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto News Generator")
    parser.add_argument("url", help="YouTube Video URL")
    args = parser.parse_args()
    
    main(args.url)
