import os
import sys
import django

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article, PendingArticle

def sanitize_url(url_str):
    if not url_str or not isinstance(url_str, str):
        return url_str
    
    # Check for duplicated "articles/" prefix
    # Common broken pattern: articles/articles/image.webp
    # Or even media/articles/articles/image.webp
    
    parts = url_str.split('/')
    filename = parts[-1]
    
    # We want it to be "articles/filename" or just "filename" (Django will add the prefix)
    # If it's a Cloudinary public ID, it might not have an extension if handled by storage
    
    # If it's a full URL, skip
    if url_str.startswith('http'):
        return url_str
        
    # Count occurrences of 'articles'
    if url_str.count('articles') > 1:
        print(f"  Fixing: {url_str} -> articles/{filename}")
        return f"articles/{filename}"
    
    # If it starts with 'media/articles/'
    if url_str.startswith('media/articles/'):
        new_url = url_str.replace('media/articles/', 'articles/')
        print(f"  Fixing prefix: {url_str} -> {new_url}")
        return new_url
        
    return url_str

def main():
    print("🚀 Starting Image URL Sanitization...")
    
    # 1. Articles
    articles = Article.objects.all()
    article_fix_count = 0
    
    for article in articles:
        modified = False
        
        # Check standard fields
        for field in ['image', 'image_2', 'image_3']:
            current_val = str(getattr(article, field))
            if not current_val: continue
            
            sanitized = sanitize_url(current_val)
            if sanitized != current_val:
                setattr(article, field, sanitized)
                modified = True
        
        if modified:
            # We use update_fields to avoid re-running optimization logic in save()
            # but Article.save() optimization logic now has protection too.
            # To be safe and fast, use save(update_fields=...)
            article.save(update_fields=['image', 'image_2', 'image_3'])
            article_fix_count += 1
            
    print(f"✅ Fixed {article_fix_count} Articles")

    # 2. Pending Articles
    # PendingArticle.featured_image is a URLField, PendingArticle.images is a JSONField
    pending = PendingArticle.objects.all()
    pending_fix_count = 0
    
    for p in pending:
        modified = False
        
        # Featured image
        if p.featured_image:
            sanitized = sanitize_url(p.featured_image)
            if sanitized != p.featured_image:
                p.featured_image = sanitized
                modified = True
                
        # Images list
        if p.images and isinstance(p.images, list):
            new_images = []
            for img in p.images:
                sanitized = sanitize_url(img)
                new_images.append(sanitized)
            
            if new_images != p.images:
                p.images = new_images
                modified = True
                
        if modified:
            p.save(update_fields=['featured_image', 'images'])
            pending_fix_count += 1
            
    print(f"✅ Fixed {pending_fix_count} PendingArticles")
    print("🏁 Sanitization complete.")

if __name__ == "__main__":
    main()
