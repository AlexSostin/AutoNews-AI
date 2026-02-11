"""
Management command to test Hybrid Vector Search functionality
"""

from django.core.management.base import BaseCommand
from news.models import Article, Category, ArticleEmbedding
from ai_engine.modules.vector_search import get_vector_engine
import time


class Command(BaseCommand):
    help = 'Test Hybrid Vector Search implementation'
    
    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🧪 HYBRID VECTOR SEARCH TEST SUITE"))
        self.stdout.write("=" * 60)
        
        # Test 1: Check migration
        self.stdout.write("\n📋 Test 1: Check ArticleEmbedding model")
        try:
            count = ArticleEmbedding.objects.count()
            self.stdout.write(self.style.SUCCESS("✅ ArticleEmbedding model exists"))
            self.stdout.write(f"   Current embeddings in DB: {count}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ ArticleEmbedding model error: {e}"))
        
        # Test 2: Create test article (auto-indexing)
        self.stdout.write("\n📝 Test 2: Create article (test auto-indexing)")
        article = None
        try:
            cat = Category.objects.first()
            if not cat:
                self.stdout.write("   Creating test category...")
                cat = Category.objects.create(name="Test Category", slug="test-category")
            
            # Delete existing test article
            Article.objects.filter(title__startswith="TEST: Hybrid Vector Search").delete()
            
            article = Article.objects.create(
                title="TEST: Hybrid Vector Search - Tesla Model S Plaid 2024",
                content="""The Tesla Model S Plaid is a high-performance electric sedan:
                
                - Power: 1020 horsepower (760 kW)
                - Drivetrain: Tri-motor all-wheel drive
                - Acceleration: 0-100 km/h in 2.1 seconds
                - Top Speed: 322 km/h
                - Range: 600 km (WLTP)
                - Battery: 100 kWh
                - Price: Starting from $135,000""",
                summary="High-performance electric sedan with 1020 HP",
                is_published=True
            )
            article.categories.add(cat)
            
            self.stdout.write(self.style.SUCCESS(f"✅ Created test article (ID: {article.id})"))
            
            # Wait for signal
            time.sleep(3)
            
            emb = ArticleEmbedding.objects.filter(article=article).first()
            if emb:
                self.stdout.write(self.style.SUCCESS("✅ Auto-indexing worked!"))
                self.stdout.write(f"   Vector dimension: {emb.get_vector_dimension()}")
            else:
                self.stdout.write(self.style.ERROR("❌ Auto-indexing failed"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test 2 failed: {e}"))
            import traceback
            traceback.print_exc()
        
        # Test 3: Vector engine stats
        self.stdout.write("\n📊 Test 3: Vector search engine stats")
        try:
            engine = get_vector_engine()
            stats = engine.get_stats()
            self.stdout.write(self.style.SUCCESS("✅ Vector engine initialized"))
            self.stdout.write(f"   FAISS articles: {stats['total_articles']}")
            self.stdout.write(f"   PostgreSQL embeddings: {stats['db_embeddings']}")
            self.stdout.write(f"   Index size: {stats['index_size_mb']} MB")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test 3 failed: {e}"))
        
        # Test 4: Find similar articles
        self.stdout.write("\n🔍 Test 4: Find similar articles")
        try:
            if article:
                similar = engine.find_similar_articles(article.id, k=3)
                self.stdout.write(self.style.SUCCESS(f"✅ Found {len(similar)} similar articles"))
                for i, s in enumerate(similar, 1):
                    self.stdout.write(f"   {i}. {s['title'][:50]}... (score: {s['score']:.2f})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test 4 failed: {e}"))
        
        # Test 5: Semantic search
        self.stdout.write("\n🔎 Test 5: Semantic search")
        try:
            results = engine.search("electric car high performance", k=3)
            self.stdout.write(self.style.SUCCESS(f"✅ Search returned {len(results)} results"))
            for i, r in enumerate(results, 1):
                self.stdout.write(f"   {i}. {r['title'][:50]}... (score: {r['score']:.2f})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test 5 failed: {e}"))
        
        # Cleanup
        self.stdout.write("\n🧹 Cleanup")
        try:
            if article:
                article.delete()
                self.stdout.write(self.style.SUCCESS(f"✅ Test article deleted"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  Cleanup failed: {e}"))
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ TEST SUITE COMPLETED"))
        self.stdout.write("=" * 60)
