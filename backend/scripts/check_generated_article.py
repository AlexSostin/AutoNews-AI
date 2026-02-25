import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article

article = Article.objects.get(id=3)

print('='*70)
print('СГЕНЕРИРОВАННАЯ СТАТЬЯ (ID: 3)')
print('='*70)
print(f'\nНазвание: {article.title}')
print(f'Slug: {article.slug}')
print(f'Категория: {article.category.name if article.category else "Нет"}')
print(f'YouTube URL: {article.youtube_url or "Нет"}')
print(f'Опубликована: {article.is_published}')
print(f'Создана: {article.created_at}')

print(f'\n--- Описание (summary) ---')
print(article.summary[:300] if article.summary else 'Пусто')

print(f'\n--- Контент (первые 500 символов) ---')
print(article.content[:500] if article.content else 'Пусто')

print(f'\n--- Теги ---')
tags = article.tags.all()
if tags:
    for tag in tags:
        print(f'  - {tag.name}')
else:
    print('  Нет тегов')
