from django.core.management.base import BaseCommand
from news.models import Article
from ai_engine.modules.title_seo_generator import _generate_title_and_seo

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
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
        print("=== RESULT ===")
        print(res)
