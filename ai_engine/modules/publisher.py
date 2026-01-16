import os
import sys
import django

# Setup Django Environment
# Assuming this script is run from project root or configured via PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article, Category, Tag

from django.core.files import File

def publish_article(title, content, category_name="Reviews", image_path=None):
    """
    Publishes the article to the Django database.
    """
    print(f"Publishing article: {title}")
    
    # Get or Create Category
    category, created = Category.objects.get_or_create(name=category_name)
    
    # Create Article
    # Note: Slug is auto-generated in Model save()
    article = Article(
        title=title,
        content=content,
        category=category,
        is_published=True # Auto publish for now
    )
    
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as f:
            article.image.save(os.path.basename(image_path), File(f), save=False)
            
    article.save()
    
    print(f"Article published successfully! Slug: {article.slug}")
    return article
