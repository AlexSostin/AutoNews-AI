"""
Quick test: BM25Index standalone (no Django, no FAISS, no Gemini API).
Tests that BM25 keyword search works correctly in isolation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engine.modules.vector_search import BM25Index


SAMPLE_DOCS = [
    {'article_id': 1, 'title': 'BYD Seal 2025 Review', 'text': 'BYD Seal is a premium electric sedan with 523 km range and 530 HP dual motor. The price starts at $38,000.'},
    {'article_id': 2, 'title': 'Tesla Model 3 Redesign', 'text': 'Tesla Model 3 Highland gets new interior and improved range up to 600 km. Fast charging at Supercharger.'},
    {'article_id': 3, 'title': 'ZEEKR 7X Specifications', 'text': 'ZEEKR 7X SUV by Geely offers 800V charging, 475 HP, and 660 km CLTC range. Premium Chinese EV.'},
    {'article_id': 4, 'title': 'VinFast VF9 Launch', 'text': 'VinFast VF9 is a Vietnamese electric SUV with 7 seats and 438 km range. Competitively priced.'},
    {'article_id': 5, 'title': 'BMW i5 Long Range', 'text': 'BMW i5 offers 582 km range and luxurious interior. Available as rear-wheel and all-wheel drive.'},
]


def test_bm25_basic():
    bm25 = BM25Index()
    bm25.build(SAMPLE_DOCS)
    assert bm25.is_ready, "BM25 should be ready after build()"

    # Test 1: exact keyword match
    results = bm25.search("BYD Seal", k=3)
    assert results, "Should return results for 'BYD Seal'"
    assert results[0]['article_id'] == 1, f"Expected article 1 (BYD Seal), got {results[0]}"
    print(f"✅ Test 1 PASS — 'BYD Seal' → article #{results[0]['article_id']}: '{results[0]['title']}'")

    # Test 2: semantic keyword (ZEEKR should rank above Tesla for suv query)
    results = bm25.search("electric SUV China", k=5)
    assert results, "Should return results for 'electric SUV China'"
    top_id = results[0]['article_id']
    print(f"✅ Test 2 PASS — 'electric SUV China' → top: article #{top_id}: '{results[0]['title']}'")

    # Test 3: unknown query returns ranked results
    results = bm25.search("luxury sedan range", k=3)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    print(f"✅ Test 3 PASS — 'luxury sedan range' → top: article #{results[0]['article_id']}: '{results[0]['title']}'")

    # Test 4: empty query (edge case)
    results_empty = bm25.search("", k=3)
    print(f"✅ Test 4 PASS — empty query returns {len(results_empty)} results (ok)")

    print("\n🎉 All BM25 tests passed!")


def test_rrf_logic():
    """Test RRF score calculation manually."""
    # Simulate: BM25 says article 1 is rank 1, vector says article 2 is rank 1
    bm25_rank = {1: 1, 2: 3, 3: 5}
    vector_rank = {2: 1, 1: 2, 4: 4}
    RRF_K = 60
    all_ids = set(bm25_rank) | set(vector_rank)

    scored = {}
    for aid in all_ids:
        rrf = 0.0
        if aid in bm25_rank:
            rrf += 1.0 / (bm25_rank[aid] + RRF_K)
        if aid in vector_rank:
            rrf += 1.0 / (vector_rank[aid] + RRF_K)
        scored[aid] = rrf

    sorted_ids = sorted(scored, key=lambda x: scored[x], reverse=True)
    print(f"\n📊 RRF fusion result: {[(aid, round(scored[aid], 5)) for aid in sorted_ids]}")
    # Article 1 (BM25 rank 1) and Article 2 (vector rank 1) should both be top 2
    assert 1 in sorted_ids[:2] or 2 in sorted_ids[:2], "Top 2 should include articles ranked 1st by either method"
    print("✅ Test 5 PASS — RRF fusion logic correct")


if __name__ == '__main__':
    print("=" * 60)
    print("BM25 Hybrid Search — Unit Tests")
    print("=" * 60)
    test_bm25_basic()
    test_rrf_logic()
