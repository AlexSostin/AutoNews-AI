import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ai_engine.main import generate_article_from_youtube

url = "https://www.youtube.com/watch?v=1B0n1S20g6c" # Random car review video
result = generate_article_from_youtube(url, provider='gemini')
print(f"Success: {result.get('success')}")
article_id = result.get('article_id')
if article_id:
    from news.models import Article
    a = Article.objects.get(id=article_id)
    print(f"Slug: {a.slug}")
    print(f"Title: {a.title}")
    # Verify tables
    if '<table' in a.content:
        print("✅ HTML Table found in content!")
    else:
        print("❌ HTML Table missing!")
    
    if '<div class="compare-grid">' in a.content:
        print("✅ Compare grid found!")
        # Let's count orphans
        if '<div class="compare-row">' in a.content:
            orphans = a.content.count('<div class="compare-row">') - a.content.count('compare-card') * a.content.split('<div class="compare-card"').__len__() # very rough estimation
            # Actually just look at parent structure
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(a.content, 'html.parser')
            for grid in soup.find_all('div', class_='compare-grid'):
                for child in list(grid.children):
                    if child.name == 'div' and 'compare-row' in child.get('class', []):
                        print("❌ Orphaned compare-row found inside compare-grid!")
                        break
                else:
                    print("✅ No orphaned compare-row inside compare-grid!")
            
            # Check for {{IMAGE_2}}
            if '{{IMAGE_2}}' in a.content:
                print("❌ {{IMAGE_2}} still in content text!")
            else:
                print("✅ {{IMAGE_2}} removed or replaced!")
