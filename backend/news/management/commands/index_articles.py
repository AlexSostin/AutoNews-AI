"""
Management command to index all published articles into FAISS vector database
"""

from django.core.management.base import BaseCommand
from news.models import Article
from ai_engine.modules.vector_search import get_vector_engine


class Command(BaseCommand):
    help = 'Index all published articles into vector database for semantic search'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='Rebuild index from scratch (deletes existing index)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of articles to index (for testing)',
        )
    
    def handle(self, *args, **options):
        rebuild = options['rebuild']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting article indexing...'))
        
        # Get vector engine
        try:
            engine = get_vector_engine()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to initialize vector engine: {e}'))
            return
        
        # Get published articles
        articles_qs = Article.objects.filter(
            is_published=True,
            is_deleted=False
        ).select_related('specs').prefetch_related('categories', 'tags')
        
        if limit:
            articles_qs = articles_qs[:limit]
        
        total = articles_qs.count()
        self.stdout.write(f'📊 Found {total} published articles to index')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️  No articles to index'))
            return
        
        # Prepare articles for bulk indexing
        articles_data = []
        for article in articles_qs:
            metadata = {
                'slug': article.slug,
                'is_published': article.is_published,
                'created_at': article.created_at.isoformat(),
            }
            
            # Add categories
            if article.categories.exists():
                metadata['categories'] = [cat.slug for cat in article.categories.all()]
            
            # Add tags
            if article.tags.exists():
                metadata['tags'] = [tag.slug for tag in article.tags.all()]
            
            articles_data.append({
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'summary': article.summary or '',
                'metadata': metadata
            })
        
        # Bulk index
        try:
            success = engine.index_articles_bulk(articles_data)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully indexed {total} articles'))
                
                # Show stats
                stats = engine.get_stats()
                self.stdout.write(f'📈 Vector DB Stats:')
                self.stdout.write(f'   - Total vectors: {stats["total_articles"]}')
                self.stdout.write(f'   - Index size: {stats["index_size_mb"]} MB')
                self.stdout.write(f'   - Status: {stats["status"]}')
            else:
                self.stdout.write(self.style.ERROR('❌ Indexing failed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error during indexing: {e}'))
            import traceback
            traceback.print_exc()
