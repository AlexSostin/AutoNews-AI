import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from ai_engine.main import generate_article_from_youtube

# Instead of fetching heavy YouTube and generative models right now which costs API quota and takes 60 seconds
# We can just manually verify our changes in the respective files:

from bs4 import BeautifulSoup
from ai_engine.modules.article_post_processor import _repair_compare_grid

bad_html = """
<div class="compare-grid">
  <div class="compare-card featured">
    <div class="compare-badge">This Vehicle</div>
    <div class="compare-card-name">2026 Leapmotor C16</div>
    <div class="compare-row"><span class="k">Power</span><span class="v">Up to 295 hp</span></div>
  </div>
  <span class="k">Range</span><span class="v">Up to 1,200 km</span>
  <span class="k">Price</span><span class="v">$22,700</span>
  
  <div class="compare-card">
    <div class="compare-card-name">2026 Li Auto L8</div>
    <div class="compare-row"><span class="k">Power</span><span class="v">449 hp</span></div>
  </div>
  <span class="k">Range</span>
  <span class="v">1,315 km CLTC</span>
  <span class="k">Price</span><span class="v">~$46,000</span>
</div>
"""

repaired = _repair_compare_grid(bad_html)
print(f"Repaired HTML:\n{repaired}")
soup = BeautifulSoup(repaired, 'html.parser')
card = soup.find('div', class_='compare-card')
rows = card.find_all('div', class_='compare-row')
print(f"Num rows inside card: {len(rows)}")
if len(rows) == 2:
    print("✅ _repair_compare_grid works perfectly!")
else:
    print("❌ _repair_compare_grid failed to move rows inside card!")


# Test {{IMAGE_X}} replacement
from news.models import Article
from urllib.request import urlretrieve
from django.core.files.base import ContentFile
import tempfile

article = Article(title="Test", content="<p>Test</p>{{IMAGE_2}}<p>End</p>", slug="test-img-replace")
article.save()

from ai_engine.modules.image_placeholders import replace_inline_images_in_article

# Right now it has no image_2 uploaded.
replace_inline_images_in_article(article)
print(f"After no image: {article.content}")

if '{{IMAGE_2}}' not in article.content:
    print("✅ {{IMAGE_2}} removed from empty article")
    
# Now add a dummy image
article.content = "<p>Test</p>{{IMAGE_2}}<p>End</p>"
article.save()

article.image_2.save('dummy.jpg', ContentFile(b'dummydata'))
replace_inline_images_in_article(article)
print(f"After dummy image: {article.content}")

if '<figure' in article.content and 'dummy.jpg' in article.content:
    print("✅ {{IMAGE_2}} converted to figure!")

article.delete()
print("Tests completed!")
