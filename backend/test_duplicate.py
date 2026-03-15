from auto_news_site.wsgi import *
from news.models import Article
a = Article(title="2025 Avatr 11 EREV: The 1,065 km Range-Extended SUV Disrupting the Premium Market")
print("Contains '06':", "06" in a.title)
