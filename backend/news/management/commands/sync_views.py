"""
Sync article views from Redis to Database

This command syncs view counts from Redis cache to the database.
Views are incremented in Redis for performance, but analytics reads from DB.
Run this periodically (e.g., every hour) to keep analytics up-to-date.
"""
from django.core.management.base import BaseCommand
from django_redis import get_redis_connection
from news.models import Article


class Command(BaseCommand):
    help = 'Sync article view counts from Redis to Database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        try:
            redis_conn = get_redis_connection("default")
            
            # Get all article view keys
            keys = redis_conn.keys('article_views:*')
            
            if not keys:
                self.stdout.write(self.style.WARNING('No view counts found in Redis'))
                return
            
            self.stdout.write(f'Found {len(keys)} articles with views in Redis')
            
            synced_count = 0
            total_views_synced = 0
            
            for key in keys:
                try:
                    # Extract article ID from key (format: article_views:123)
                    article_id = int(key.decode().split(':')[1])
                    redis_views = int(redis_conn.get(key) or 0)
                    
                    if redis_views == 0:
                        continue
                    
                    # Get article from DB
                    try:
                        article = Article.objects.get(id=article_id)
                        db_views = article.views
                        
                        if redis_views > db_views:
                            if dry_run:
                                self.stdout.write(
                                    f'  Would sync: {article.title[:50]} - DB:{db_views} → Redis:{redis_views} (+{redis_views - db_views})'
                                )
                            else:
                                # Update database
                                Article.objects.filter(id=article_id).update(views=redis_views)
                                synced_count += 1
                                total_views_synced += (redis_views - db_views)
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'  ✓ Synced: {article.title[:50]} - {db_views} → {redis_views} (+{redis_views - db_views})'
                                    )
                                )
                        elif redis_views < db_views:
                            # Redis is behind DB - update Redis to match DB
                            if dry_run:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  Redis behind DB: {article.title[:50]} - Redis:{redis_views} < DB:{db_views}'
                                    )
                                )
                            else:
                                redis_conn.set(key, db_views)
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  ⚠ Updated Redis: {article.title[:50]} - {redis_views} → {db_views}'
                                    )
                                )
                        else:
                            # Already in sync
                            if options['verbosity'] >= 2:
                                self.stdout.write(f'  = In sync: {article.title[:50]} - {db_views} views')
                    
                    except Article.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'  Article ID {article_id} not found in DB, skipping')
                        )
                        continue
                        
                except (ValueError, IndexError) as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Error processing key {key}: {e}')
                    )
                    continue
            
            # Summary
            if dry_run:
                self.stdout.write(self.style.WARNING('\n🔍 DRY RUN - No changes made'))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Synced {synced_count} articles, total +{total_views_synced} views'
                    )
                )
                
                # Clear cache to reflect new view counts
                try:
                    from django.core.cache import cache
                    cache.clear()
                    self.stdout.write(self.style.SUCCESS('✓ Cleared cache'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠ Could not clear cache: {e}'))
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error connecting to Redis: {e}')
            )
            raise
