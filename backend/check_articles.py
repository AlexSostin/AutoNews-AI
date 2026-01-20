import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article

total = Article.objects.count()
published = Article.objects.filter(is_published=True).count()
draft = Article.objects.filter(is_published=False).count()

print(f'\n{"="*60}')
print(f'Всего статей в базе: {total}')
print(f'Опубликованных: {published}')
print(f'Черновиков: {draft}')
print(f'{"="*60}\n')

print('Последние 10 статей (по дате создания):\n')
for i, article in enumerate(Article.objects.order_by('-created_at')[:10], 1):
    status = '✓ Опубликована' if article.is_published else '✗ Черновик'
    print(f'{i}. {article.title[:60]}')
    print(f'   ID: {article.id} | {status} | Создана: {article.created_at.strftime("%Y-%m-%d %H:%M")}')
    print(f'   Категория: {article.category.name if article.category else "Нет"}')
    print()
