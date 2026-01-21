from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth.models import User
from news.models import Category, Tag, Article, SiteSettings
import random


class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting database population...\n")

        # 1. Create Categories
        self.stdout.write("\n📁 Creating categories...")
        categories_data = [
            ('Новости', 'news', 'Последние новости автомобильной индустрии'),
            ('Обзоры', 'reviews', 'Детальные обзоры автомобилей'),
            ('Электромобили', 'evs', 'Всё о электрических автомобилях'),
            ('Технологии', 'technology', 'Новые технологии в автомобилях'),
            ('Классика', 'classics', 'Классические автомобили'),
            ('Спорт', 'motorsport', 'Автоспорт и гонки'),
        ]

        categories = []
        for name, slug, desc in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': desc}
            )
            categories.append(cat)
            self.stdout.write(f"{'✅ Created' if created else '✓ Exists'}: {name}")

        # 2. Create Tags
        self.stdout.write("\n🏷️ Creating tags...")
        tags_data = [
            'Tesla', 'BMW', 'Mercedes', 'Audi', 'Toyota',
            'Electric', 'Hybrid', 'SUV', 'Sedan', 'Sport',
            'Luxury', 'Budget', 'Off-road', 'City', 'Family'
        ]

        tags = []
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(
                slug=slugify(tag_name),
                defaults={'name': tag_name}
            )
            tags.append(tag)
            self.stdout.write(f"{'✅' if created else '✓'} {tag_name}")

        # 3. Create sample articles
        self.stdout.write("\n📰 Creating sample articles...")

        sample_articles = [
            {
                'title': 'Tesla Model 3 - революция в мире электромобилей',
                'excerpt': 'Детальный обзор самого популярного электромобиля',
                'content': '''# Tesla Model 3: Полный обзор

Tesla Model 3 стала самым продаваемым электромобилем в мире. В этом обзоре мы расскажем почему.

## Дизайн
Минималистичный дизайн интерьера с огромным центральным экраном.

## Технологии
- Автопилот
- Over-the-air обновления
- Запас хода до 600 км

## Производительность
- 0-100 км/ч за 3.1 секунды (Performance версия)
- Максимальная скорость 261 км/ч

## Цена
От $40,000 в базовой комплектации.''',
                'category': categories[2],  # EVs
                'tags_idx': [0, 5, 8],  # Tesla, Electric, Sedan
            },
            {
                'title': 'BMW M5 Competition 2026 - король седанов',
                'excerpt': 'Новая генерация спортивного седана от BMW',
                'content': '''# BMW M5 Competition 2026

## Двигатель
4.4L Twin-Turbo V8 с гибридной системой
- Мощность: 727 л.с.
- Крутящий момент: 1000 Нм

## Динамика
0-100 км/ч за 2.9 секунды

## Интерьер
Премиум материалы и спортивные сиденья.''',
                'category': categories[1],  # Reviews
                'tags_idx': [1, 9, 10],  # BMW, Sport, Luxury
            },
            {
                'title': 'Toyota Land Cruiser 300 - легенда внедорожников',
                'excerpt': 'Новое поколение легендарного внедорожника',
                'content': '''# Toyota Land Cruiser 300

## Надежность
Toyota Land Cruiser известен своей легендарной надежностью.

## Внедорожные возможности
- Полный привод
- Блокировки дифференциалов
- Пневмоподвеска

## Двигатель
3.5L Twin-Turbo V6 - 415 л.с.''',
                'category': categories[0],  # News
                'tags_idx': [4, 7, 12],  # Toyota, SUV, Off-road
            },
            {
                'title': 'Mercedes S-Class W223 - эталон роскоши',
                'excerpt': 'Самый технологичный седан в мире',
                'content': '''# Mercedes-Benz S-Class W223

## Технологии
- MBUX с AI ассистентом
- Дополненная реальность в навигации
- 12 подушек безопасности

## Комфорт
Массажные сиденья с функцией подогрева и вентиляции.

## Двигатель
От 3.0L до 6.0L V12''',
                'category': categories[1],  # Reviews
                'tags_idx': [2, 10, 8],  # Mercedes, Luxury, Sedan
            },
            {
                'title': 'Porsche 911 GT3 - чистокровный спорткар',
                'excerpt': 'Легендарный спорткар для трека и дороги',
                'content': '''# Porsche 911 GT3

## Двигатель
4.0L оппозитный 6-цилиндровый
- Мощность: 510 л.с.
- Обороты: до 9000 об/мин

## Трековые характеристики
Время круга Нюрбургринга: 6:55

## Аэродинамика
Огромное заднее антикрыло для прижимной силы.''',
                'category': categories[5],  # Motorsport
                'tags_idx': [9, 10],  # Sport, Luxury
            }
        ]

        # Get or create author (superuser)
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            self.stdout.write("⚠️ No superuser found, using first user or creating one...")
            author = User.objects.first()
            if not author:
                author = User.objects.create_user(
                    username='admin',
                    email='admin@autonews.ai',
                    password='changeme123',
                    is_staff=True,
                    is_superuser=True
                )

        for article_data in sample_articles:
            article, created = Article.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    'slug': slugify(article_data['title'][:50]),
                    'excerpt': article_data['excerpt'],
                    'content': article_data['content'],
                    'category': article_data['category'],
                    'author': author,
                    'is_published': True,
                    'views': random.randint(100, 5000),
                }
            )
            
            if created:
                article_tags = [tags[i] for i in article_data['tags_idx'] if i < len(tags)]
                article.tags.set(article_tags)
                self.stdout.write(f"✅ Created: {article.title[:50]}...")
            else:
                self.stdout.write(f"✓ Exists: {article.title[:50]}...")

        # 4. Create Site Settings
        self.stdout.write("\n⚙️ Creating site settings...")
        settings, created = SiteSettings.objects.get_or_create(
            id=1,
            defaults={
                'site_name': 'AutoNews',
                'site_description': 'Лучшие новости и обзоры автомобилей',
                'contact_email': 'info@autonews.ai',
                'contact_phone': '+1-234-567-8900',
                'footer_text': '© 2026 AutoNews. Все права защищены.',
            }
        )
        self.stdout.write(f"{'✅ Created' if created else '✓ Exists'}: Site Settings")

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("🎉 Database populated successfully!"))
        self.stdout.write("="*50)
        self.stdout.write(f"\n📊 Statistics:")
        self.stdout.write(f"  Categories: {Category.objects.count()}")
        self.stdout.write(f"  Tags: {Tag.objects.count()}")
        self.stdout.write(f"  Articles: {Article.objects.count()}")
        self.stdout.write(f"  Users: {User.objects.count()}")
        self.stdout.write("\n✅ Ready to go!")
