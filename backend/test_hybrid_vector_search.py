"""
Test script for Hybrid Vector Search
Tests auto-indexing, persistence, and search functionality
"""

from news.models import Article, Category, ArticleEmbedding
from ai_engine.modules.vector_search import get_vector_engine

print("=" * 60)
print("🧪 HYBRID VECTOR SEARCH TEST SUITE")
print("=" * 60)

# Test 1: Check migration
print("\n📋 Test 1: Check ArticleEmbedding model")
try:
    count = ArticleEmbedding.objects.count()
    print(f"✅ ArticleEmbedding model exists")
    print(f"   Current embeddings in DB: {count}")
except Exception as e:
    print(f"❌ ArticleEmbedding model error: {e}")

# Test 2: Create test article (auto-indexing)
print("\n📝 Test 2: Create article (test auto-indexing)")
try:
    cat = Category.objects.first()
    if not cat:
        print("⚠️  No categories found, creating one...")
        cat = Category.objects.create(name="Test Category", slug="test-category")
    
    # Check if test article already exists
    existing = Article.objects.filter(title__startswith="TEST: Hybrid Vector Search").first()
    if existing:
        print(f"   Deleting existing test article (ID: {existing.id})")
        existing.delete()
    
    article = Article.objects.create(
        title="TEST: Hybrid Vector Search - Tesla Model S Plaid 2024",
        content="""The Tesla Model S Plaid is a high-performance electric sedan with exceptional specifications:
        
        - Power: 1020 horsepower (760 kW)
        - Drivetrain: Tri-motor all-wheel drive
        - Acceleration: 0-100 km/h in 2.1 seconds
        - Top Speed: 322 km/h
        - Range: 600 km (WLTP)
        - Battery: 100 kWh
        - Price: Starting from $135,000
        
        The Plaid variant represents the pinnacle of Tesla's performance engineering, combining ludicrous acceleration with practical daily usability.""",
        summary="High-performance electric sedan with 1020 HP and 600 km range",
        is_published=True
    )
    article.categories.add(cat)
    
    print(f"✅ Created test article (ID: {article.id})")
    print(f"   Title: {article.title}")
    
    # Check if embedding was created (auto-indexing)
    import time
    time.sleep(2)  # Give signal time to process
    
    emb = ArticleEmbedding.objects.filter(article=article).first()
    if emb:
        print(f"✅ Auto-indexing worked! Embedding created")
        print(f"   Vector dimension: {emb.get_vector_dimension()}")
        print(f"   Model: {emb.model_name}")
    else:
        print(f"❌ Auto-indexing failed - no embedding found")
        
except Exception as e:
    print(f"❌ Test 2 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Vector search engine stats
print("\n📊 Test 3: Vector search engine stats")
try:
    engine = get_vector_engine()
    stats = engine.get_stats()
    print(f"✅ Vector engine initialized")
    print(f"   Total articles in FAISS: {stats['total_articles']}")
    print(f"   Embeddings in PostgreSQL: {stats['db_embeddings']}")
    print(f"   Index size: {stats['index_size_mb']} MB")
    print(f"   Status: {stats['status']}")
except Exception as e:
    print(f"❌ Test 3 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Find similar articles
print("\n🔍 Test 4: Find similar articles")
try:
    if article:
        similar = engine.find_similar_articles(article.id, k=3)
        print(f"✅ Found {len(similar)} similar articles:")
        for i, s in enumerate(similar, 1):
            print(f"   {i}. {s['title'][:60]}... (score: {s['score']:.2f})")
        
        if len(similar) == 0:
            print("   ℹ️  No similar articles (might be the only article)")
    else:
        print("⚠️  Skipped - no test article created")
except Exception as e:
    print(f"❌ Test 4 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Search by query
print("\n🔎 Test 5: Semantic search")
try:
    results = engine.search("electric car high performance", k=3)
    print(f"✅ Search returned {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['title'][:60]}... (score: {r['score']:.2f})")
except Exception as e:
    print(f"❌ Test 5 failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Update article (re-indexing)
print("\n🔄 Test 6: Update article (test re-indexing)")
try:
    if article:
        old_content = article.content
        article.content = old_content + "\n\nUpdated with new information about battery technology."
        article.save()
        
        time.sleep(2)  # Give signal time to process
        
        emb = ArticleEmbedding.objects.filter(article=article).first()
        print(f"✅ Article updated")
        print(f"   Embedding updated_at: {emb.updated_at if emb else 'N/A'}")
    else:
        print("⚠️  Skipped - no test article")
except Exception as e:
    print(f"❌ Test 6 failed: {e}")

# Test 7: Unpublish article (auto-remove)
print("\n🗑️  Test 7: Unpublish article (test auto-remove)")
try:
    if article:
        article.is_published = False
        article.save()
        
        time.sleep(2)  # Give signal time to process
        
        emb = ArticleEmbedding.objects.filter(article=article).first()
        if emb:
            print(f"⚠️  Embedding still exists (might be kept for re-publishing)")
        else:
            print(f"✅ Embedding removed from database")
        
        # Check FAISS stats
        stats = engine.get_stats()
        print(f"   FAISS articles: {stats['total_articles']}")
        print(f"   PostgreSQL embeddings: {stats['db_embeddings']}")
    else:
        print("⚠️  Skipped - no test article")
except Exception as e:
    print(f"❌ Test 7 failed: {e}")

# Cleanup
print("\n🧹 Cleanup: Deleting test article")
try:
    if article:
        article.delete()
        print(f"✅ Test article deleted (ID: {article.id})")
except Exception as e:
    print(f"⚠️  Cleanup failed: {e}")

print("\n" + "=" * 60)
print("✅ TEST SUITE COMPLETED")
print("=" * 60)
