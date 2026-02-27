import os
import sys
import django
import cloudinary.api
from difflib import SequenceMatcher

sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def main():
    print("Fetching Cloudinary resources...")
    # Fetch 1000 to be safe
    res = cloudinary.api.resources(type='upload', max_results=1000).get('resources', [])
    cld_ids = [r['public_id'] for r in res]
    
    articles = Article.objects.all()
    print(f"Checking {articles.count()} articles...")
    
    fixed = 0
    missing = 0
    
    for a in articles:
        modified = False
        
        for field in ['image', 'image_2', 'image_3']:
            img_val = str(getattr(a, field))
            if not img_val: continue
            
            # Extract core name from db value or slug
            base_name = os.path.basename(img_val)
            name_no_ext = os.path.splitext(base_name)[0]
            
            # Heuristic 1: Exact substring match
            matches = [cid for cid in cld_ids if name_no_ext in cid]
            
            # Heuristic 2: Match by first 30 chars of the name (ignoring random suffixes)
            if not matches and len(name_no_ext) > 30:
                short_name = name_no_ext[:30]
                matches = [cid for cid in cld_ids if short_name in cid]
                
            # Heuristic 3: Use the article slug core
            if not matches:
                # slug looks like '2026-byd-qin-l-dm-i-review-8e91bf'
                # drop the last hex part
                parts = a.slug.split('-')
                if len(parts) > 2:
                    core_slug = '-'.join(parts[:-1]) # e.g. 2026-byd-qin-l-dm-i-review
                    matches = [cid for cid in cld_ids if core_slug in cid]
            
            if matches:
                # Pick the most "nested" or longest one as that's what Cloudinary actually has
                best_match = max(matches, key=len)
                
                new_db_val = best_match
                if new_db_val.startswith('media/'):
                    new_db_val = new_db_val[6:] # Strip media/ from DB path
                    
                if not new_db_val.endswith(('.webp', '.jpg', '.jpeg', '.png', '.gif')):
                    new_db_val += '.webp'
                    
                if img_val != new_db_val:
                    print(f"Article {a.id} [{field}]:")
                    print(f"  Old: {img_val}")
                    print(f"  New: {new_db_val} (Matched with {best_match})")
                    setattr(a, field, new_db_val)
                    modified = True
            else:
                print(f"Article {a.id} [{field}]: No match found (Tried: {name_no_ext})")
                missing += 1
                
        if modified:
            a.save(update_fields=['image', 'image_2', 'image_3'])
            fixed += 1
            
    print(f"Fixed {fixed} articles. Still missing {missing} images completely.")

if __name__ == '__main__':
    main()
