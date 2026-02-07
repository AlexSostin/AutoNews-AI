"""
Management command to add popular automotive RSS feeds.
"""
from django.core.management.base import BaseCommand
from news.models import RSSFeed, Category


class Command(BaseCommand):
    help = 'Add popular automotive brand RSS feeds'

    def handle(self, *args, **options):
        # Get or create categories
        news_cat, _ = Category.objects.get_or_create(
            name='News',
            defaults={'slug': 'news'}
        )
        ev_cat, _ = Category.objects.get_or_create(
            name='Electric Vehicles',
            defaults={'slug': 'electric-vehicles'}
        )
        luxury_cat, _ = Category.objects.get_or_create(
            name='Luxury',
            defaults={'slug': 'luxury'}
        )

        # RSS Feeds to add
        feeds = [
            {
                'name': 'Ford Media Center',
                'feed_url': 'https://media.ford.com/content/fordmedia/fna/us/en/news.rss',
                'category': news_cat,
                'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Ford_logo_flat.svg/200px-Ford_logo_flat.svg.png',
            },
            {
                'name': 'Toyota USA Newsroom',
                'feed_url': 'https://pressroom.toyota.com/feed/atom',
                'category': news_cat,
                'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Toyota.svg/200px-Toyota.svg.png',
            },
            {
                'name': 'Teslarati',
                'feed_url': 'https://www.teslarati.com/feed',
                'category': ev_cat,
                'logo_url': 'https://www.teslarati.com/wp-content/uploads/2019/03/teslarati-logo-2019.png',
            },
            {
                'name': 'Electrek Tesla',
                'feed_url': 'https://electrek.co/guides/tesla/feed',
                'category': ev_cat,
                'logo_url': 'https://electrek.co/wp-content/uploads/sites/3/2016/04/electrek-logo.png',
            },
            {
                'name': 'BMWBLOG',
                'feed_url': 'https://www.bmwblog.com/feed',
                'category': luxury_cat,
                'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/BMW.svg/200px-BMW.svg.png',
            },
        ]

        created = 0
        for feed_data in feeds:
            feed, created_new = RSSFeed.objects.get_or_create(
                feed_url=feed_data['feed_url'],
                defaults={
                    'name': feed_data['name'],
                    'default_category': feed_data['category'],
                    'logo_url': feed_data['logo_url'],
                    'is_enabled': True,
                }
            )
            if created_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {feed.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'- Already exists: {feed.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Added {created} new RSS feeds'))
        self.stdout.write(f'📊 Total RSS feeds: {RSSFeed.objects.count()}')
