import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append('/home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/backend')
django.setup()

from news.models import Article
from ai_engine.modules.title_seo_generator import _generate_title_and_seo

article = Article.objects.get(slug='2026-byd-song-l-dm-i-massive-1630-km-range-suv-launches-with-19700-starting-pric-cea58a')

cs = getattr(article, 'carspecification', None)
specs_dict = {}
if cs:
    specs_dict = {
        'make': cs.make,
        'model': cs.model,
        'year': cs.release_date,
        'horsepower': cs.horsepower,
        'price': cs.price,
    }

print("Running generator...")
res = _generate_title_and_seo(article.content, specs_dict)
print(res)

