"""
Sync article view counts from Redis to PostgreSQL database.
Run periodically (e.g., every hour) to persist view counts.
"""
from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = 'Sync article view counts from Redis cache to database'

    def handle(self, *args, **options):
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            # Find all article view keys in Redis
            pattern = "article_views:*"
            keys = redis_conn.keys(pattern)
            
            synced_count = 0
            
            for key in keys:
                try:
                    # Extract article ID from key
                    article_id = int(key.decode().split(':')[1])
                    view_count = int(redis_conn.get(key) or 0)
                    
                    # Update database
                    updated = Article.objects.filter(id=article_id).update(views=view_count)
                    
                    if updated:
                        synced_count += 1
                        self.stdout.write(f"  Article {article_id}: {view_count} views")
                        
                except (ValueError, IndexError) as e:
                    self.stdout.write(self.style.WARNING(f"  Skipping invalid key: {key}"))
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Synced {synced_count} article view counts from Redis to database'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'⚠ Redis not available, skipping sync: {e}'
            ))
