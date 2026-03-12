"""
Hybrid Vector Search Engine using FAISS + BM25 + PostgreSQL

Architecture:
- FAISS:      Fast in-memory semantic (vector) search
- BM25:       Fast in-memory keyword search (no API calls, free)
- PostgreSQL: Persistent storage for embeddings
- Hybrid:     Reciprocal Rank Fusion (RRF) merges both results

RRF formula: score = 1/(rank_bm25 + 60) + 1/(rank_vector + 60)
k=60 is the standard constant — dampens the effect of very high ranks.
"""

import os
import hashlib
import threading
import logging
import time
from typing import List, Dict, Optional
from collections import deque
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import faiss
import numpy as np

logger = logging.getLogger(__name__)

# Redis key for storing the serialized FAISS index
FAISS_REDIS_KEY = 'faiss_index_cache'
FAISS_REDIS_TTL = 60 * 60 * 24 * 7  # 7 days

# Embedding query cache (prevents repeated API calls for same search)
EMBEDDING_CACHE_PREFIX = 'emb_cache:'
EMBEDDING_CACHE_TTL = 60 * 60  # 1 hour

# Throttle: max embedding API calls per window
THROTTLE_MAX_CALLS = 40
THROTTLE_WINDOW_SECONDS = 60


class BM25Index:
    """
    Lightweight in-memory BM25 keyword index.
    Built from article texts — no API calls, fully local.
    """

    def __init__(self):
        self._bm25 = None
        self._doc_ids: List[int] = []   # article_id at each position
        self._doc_titles: List[str] = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + lowercase tokenizer."""
        import re
        text = text.lower()
        return re.findall(r'[\w]+', text)

    def build(self, docs: List[Dict]):
        """
        Build the BM25 index from a list of dicts:
            {'article_id': int, 'title': str, 'text': str}
        """
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            print("⚠️ rank-bm25 not installed — BM25 disabled. Run: pip install rank-bm25")
            return

        if not docs:
            self._bm25 = None
            self._doc_ids = []
            self._doc_titles = []
            return

        tokenized = [self._tokenize(d['text']) for d in docs]
        self._bm25 = BM25Okapi(tokenized)
        self._doc_ids = [d['article_id'] for d in docs]
        self._doc_titles = [d.get('title', '') for d in docs]
        print(f"✓ BM25 index built with {len(docs)} documents")

    def search(self, query: str, k: int = 20) -> List[Dict]:
        """
        Keyword search. Returns list of {article_id, title, bm25_score, rank}.
        """
        if self._bm25 is None or not self._doc_ids:
            return []

        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)

        # Pair with doc info and sort
        paired = [
            (score, self._doc_ids[i], self._doc_titles[i])
            for i, score in enumerate(scores)
        ]
        paired.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (score, article_id, title) in enumerate(paired[:k]):
            results.append({
                'article_id': article_id,
                'title': title,
                'bm25_score': float(score),
                'rank': rank + 1,
            })
        return results


    @property
    def is_ready(self) -> bool:
        return self._bm25 is not None


class ThrottledEmbeddings:
    """Wrapper around GoogleGenerativeAIEmbeddings that enforces rate limiting.
    
    Prevents burst embedding calls from exceeding Gemini API rate limits.
    Max THROTTLE_MAX_CALLS per THROTTLE_WINDOW_SECONDS (default: 40/min).
    Also proxies all attributes so langchain/FAISS sees it as a normal embeddings object.
    """

    def __init__(self, embeddings, engine=None):
        self._embeddings = embeddings
        self._engine = engine  # Reference to VectorSearchEngine for shared timestamp deque
        self._local_timestamps = deque()  # Fallback if no engine

    @property
    def _timestamps(self):
        if self._engine is not None:
            return self._engine._throttle_timestamps
        return self._local_timestamps

    def _throttle(self):
        """Wait if we're exceeding rate limits."""
        now = time.time()
        # Clean old timestamps
        while self._timestamps and self._timestamps[0] < now - THROTTLE_WINDOW_SECONDS:
            self._timestamps.popleft()
        
        if len(self._timestamps) >= THROTTLE_MAX_CALLS:
            wait_time = self._timestamps[0] + THROTTLE_WINDOW_SECONDS - now + 0.1
            if wait_time > 0:
                logger.info(f'⏳ Embedding throttle: waiting {wait_time:.1f}s ({len(self._timestamps)} calls in last {THROTTLE_WINDOW_SECONDS}s)')
                time.sleep(wait_time)
        
        self._timestamps.append(time.time())

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query with throttling."""
        self._throttle()
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents with throttling."""
        self._throttle()
        return self._embeddings.embed_documents(texts)

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying embeddings model."""
        return getattr(self._embeddings, name)



class VectorSearchEngine:
    """
    Hybrid vector search: FAISS (semantic) + BM25 (keyword) + PostgreSQL (persistence)
    """

    def __init__(self):
        """Initialize the hybrid vector search engine"""
        self._lock = threading.Lock()  # Prevent concurrent rebuild races
        self._throttle_timestamps = deque()  # Track recent API calls for throttling
        self.embedding_model = self._get_embedding_model()
        self.vector_store = None
        self.bm25 = BM25Index()
        self.index_path = Path("data/vector_db/faiss_index")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Startup priority: Redis cache → disk → full DB rebuild
        if not self._load_index_from_redis():
            if (self.index_path / "index.faiss").exists():
                self._load_index_from_disk()
            else:
                self._rebuild_from_database()
    
    def _get_embedding_model(self):
        """Get Google Gemini embedding model"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        return ThrottledEmbeddings(
            embeddings=GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
                google_api_key=api_key
            ),
            engine=self,
        )
    
    def _load_index_from_redis(self) -> bool:
        """Try loading FAISS index from Redis cache (survives Railway deploys)."""
        try:
            from django.core.cache import cache
            serialized = cache.get(FAISS_REDIS_KEY)
            if serialized:
                # Write to temp disk path and load via FAISS
                import tempfile, shutil
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp) / 'faiss_idx'
                    tmp_path.mkdir()
                    for name, data in serialized.items():
                        (tmp_path / name).write_bytes(data)
                    self.vector_store = FAISS.load_local(
                        str(tmp_path), self.embedding_model,
                        allow_dangerous_deserialization=True
                    )
                    # Also save to disk for faster future startups
                    self._save_index_to_disk()
                    self._rebuild_bm25_from_faiss()
                    logger.info(
                        f'✓ Loaded FAISS from Redis cache '
                        f'({self.vector_store.index.ntotal} vectors)'
                    )
                    return True
        except Exception as e:
            logger.debug(f'Redis FAISS cache miss: {e}')
        return False

    def _save_index_to_redis(self):
        """Cache the serialized FAISS index in Redis for fast startup after deploy."""
        if not self.vector_store:
            return
        try:
            from django.core.cache import cache
            # Serialize FAISS to disk first, then read the files
            self.vector_store.save_local(str(self.index_path))
            serialized = {}
            for f in self.index_path.iterdir():
                serialized[f.name] = f.read_bytes()
            cache.set(FAISS_REDIS_KEY, serialized, FAISS_REDIS_TTL)
            logger.info(f'✓ Saved FAISS to Redis cache ({len(serialized)} files)')
        except Exception as e:
            logger.warning(f'⚠️ Failed to cache FAISS in Redis: {e}')

    def _load_index_from_disk(self):
        """Load existing FAISS index from disk (fast startup)"""
        try:
            self.vector_store = FAISS.load_local(
                str(self.index_path),
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
            self._rebuild_bm25_from_faiss()
            logger.info(f'✓ Loaded FAISS index from disk ({self.vector_store.index.ntotal} vectors)')
        except Exception as e:
            logger.warning(f'⚠️ Failed to load from disk: {e}')
            self._rebuild_from_database()
    
    def _rebuild_from_database(self):
        """Rebuild FAISS + BM25 indexes from PostgreSQL (on first startup or corruption).
        Uses STORED embedding vectors from ArticleEmbedding — NO Gemini API calls needed!
        """
        with self._lock:
            try:
                from news.models import ArticleEmbedding

                embeddings = ArticleEmbedding.objects.select_related('article').all()
                count = embeddings.count()

                if count == 0:
                    logger.info('ℹ️ No embeddings in database, starting with empty index')
                    self.vector_store = None
                    return

                logger.info(f'🔄 Rebuilding FAISS + BM25 from {count} stored embeddings (no API calls)...')

                documents = []
                bm25_docs = []
                emb_vectors = []
                for emb in embeddings:
                    article = emb.article
                    text = f"{article.title}\n\n{article.summary or ''}\n\n{article.content}"

                    doc = Document(
                        page_content=text,
                        metadata={
                            "article_id": article.id,
                            "title": article.title,
                            "summary": article.summary or "",
                            "slug": article.slug,
                        }
                    )
                    documents.append(doc)
                    bm25_docs.append({'article_id': article.id, 'title': article.title, 'text': text})

                    # Use stored vector if available (no API call!)
                    vec = getattr(emb, 'embedding_vector', None)
                    if vec is not None:
                        emb_vectors.append(vec)

                if documents and len(emb_vectors) == len(documents):
                    # Build FAISS directly from stored vectors (FREE — no Gemini API)
                    text_embedding_pairs = list(zip(
                        [doc.page_content for doc in documents],
                        emb_vectors,
                    ))
                    metadatas = [doc.metadata for doc in documents]
                    self.vector_store = FAISS.from_embeddings(
                        text_embedding_pairs,
                        self.embedding_model,
                        metadatas=metadatas,
                    )
                    logger.info(f'✅ Rebuilt FAISS from stored vectors ({len(documents)} articles, 0 API calls)')
                elif documents:
                    # Fallback: re-embed via API (only if no stored vectors)
                    logger.warning('⚠️ No stored vectors — re-embedding via Gemini API')
                    self.vector_store = FAISS.from_documents(documents, self.embedding_model)

                self._save_index_to_disk()
                self._save_index_to_redis()
                self.bm25.build(bm25_docs)
                logger.info(f'✅ Rebuild complete: {len(documents)} articles indexed')

            except Exception as e:
                logger.error(f'❌ Failed to rebuild from database: {e}')
                import traceback
                traceback.print_exc()
                self.vector_store = None

    def _save_index_to_disk(self):
        """Save FAISS index to disk for faster startup"""
        if self.vector_store:
            try:
                self.vector_store.save_local(str(self.index_path))
                logger.info(f'✓ Saved FAISS index to {self.index_path}')
            except Exception as e:
                logger.warning(f'⚠️ Failed to save index: {e}')
    
    def _save_to_database(self, article_id: int, embedding: List[float], text: str):
        """Save embedding to PostgreSQL for persistence"""
        try:
            from news.models import ArticleEmbedding, Article
            
            # Calculate hash of text to detect changes
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            article = Article.objects.get(id=article_id)
            
            # Use explicit filter+save instead of update_or_create
            # to avoid SELECT FOR UPDATE sequential scans
            existing = ArticleEmbedding.objects.filter(article=article).first()
            if existing:
                existing.embedding_vector = embedding
                existing.model_name = 'models/gemini-embedding-001'
                existing.text_hash = text_hash
                existing.save(update_fields=['embedding_vector', 'model_name', 'text_hash', 'updated_at'])
            else:
                ArticleEmbedding.objects.create(
                    article=article,
                    embedding_vector=embedding,
                    model_name='models/gemini-embedding-001',
                    text_hash=text_hash,
                )
            print(f"✓ Saved embedding to database for article {article_id}")
            
        except Exception as e:
            print(f"❌ Failed to save to database: {e}")
    
    def _remove_from_database(self, article_id: int):
        """Remove embedding from PostgreSQL"""
        try:
            from news.models import ArticleEmbedding
            
            ArticleEmbedding.objects.filter(article_id=article_id).delete()
            print(f"✓ Removed embedding from database for article {article_id}")
            
        except Exception as e:
            print(f"⚠️ Failed to remove from database: {e}")
    
    def index_article(self, article_id: int, title: str, content: str,
                     summary: str = "", metadata: Optional[Dict] = None):
        """
        Index a single article into FAISS + BM25 + PostgreSQL.
        """
        text_to_index = f"{title}\n\n{summary}\n\n{content}"
        embedding = self.embedding_model.embed_query(text_to_index)
        self._save_to_database(article_id, embedding, text_to_index)

        doc_metadata = {
            "article_id": article_id,
            "title": title,
            "summary": summary,
            **(metadata or {})
        }
        document = Document(page_content=text_to_index, metadata=doc_metadata)

        if self.vector_store is None:
            self.vector_store = FAISS.from_documents([document], self.embedding_model)
        else:
            self.vector_store.add_documents([document])

        self._save_index_to_disk()
        self._save_index_to_redis()

        # Rebuild BM25 from all current docs (cheap, instant)
        self._rebuild_bm25_from_faiss()
        return True
    
    def index_articles_bulk(self, articles: List[Dict]):
        """
        Index multiple articles at once — more efficient than one-by-one.
        Articles: List of dicts with keys: id, title, content, summary, metadata
        """
        documents = []
        bm25_docs = []

        for article in articles:
            text_to_index = f"{article['title']}\n\n{article.get('summary', '')}\n\n{article['content']}"
            embedding = self.embedding_model.embed_query(text_to_index)
            self._save_to_database(article['id'], embedding, text_to_index)

            doc_metadata = {
                "article_id": article['id'],
                "title": article['title'],
                "summary": article.get('summary', ''),
                **article.get('metadata', {})
            }
            documents.append(Document(page_content=text_to_index, metadata=doc_metadata))
            bm25_docs.append({'article_id': article['id'], 'title': article['title'], 'text': text_to_index})

        if not documents:
            return False

        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(documents, self.embedding_model)
        else:
            self.vector_store.add_documents(documents)

        self._save_index_to_disk()
        self._save_index_to_redis()
        self._rebuild_bm25_from_faiss()
        logger.info(f'✓ Indexed {len(documents)} articles (FAISS + BM25)')
        return True
    
    def remove_article(self, article_id: int):
        """Remove article from FAISS, BM25, and PostgreSQL.
        
        IMPORTANT: Rebuilds FAISS from stored vectors in PostgreSQL.
        Does NOT re-embed via API — 0 Gemini API calls.
        """
        self._remove_from_database(article_id)

        if self.vector_store is None:
            return True

        # Get all documents except the one to delete
        all_docs = [
            doc for doc in self.vector_store.docstore._dict.values()
            if doc.metadata.get("article_id") != article_id
        ]

        if not all_docs:
            self.vector_store = None
            self.bm25 = BM25Index()
            return True

        # Rebuild from stored vectors (FREE — no API calls)
        # Fetch stored embedding vectors from PostgreSQL
        try:
            from news.models import ArticleEmbedding
            remaining_ids = [doc.metadata.get('article_id') for doc in all_docs]
            stored = ArticleEmbedding.objects.filter(
                article_id__in=remaining_ids
            ).values_list('article_id', 'embedding_vector')
            stored_map = {aid: vec for aid, vec in stored}

            # Build text-embedding pairs from docs + stored vectors
            text_embedding_pairs = []
            metadatas = []
            docs_without_vectors = []

            for doc in all_docs:
                aid = doc.metadata.get('article_id')
                vec = stored_map.get(aid)
                if vec is not None:
                    text_embedding_pairs.append((doc.page_content, vec))
                    metadatas.append(doc.metadata)
                else:
                    docs_without_vectors.append(doc)

            if text_embedding_pairs:
                self.vector_store = FAISS.from_embeddings(
                    text_embedding_pairs,
                    self.embedding_model,
                    metadatas=metadatas,
                )
                # Add any docs without stored vectors (rare — needs API)
                if docs_without_vectors:
                    logger.warning(f'⚠️ {len(docs_without_vectors)} docs missing stored vectors, re-embedding')
                    self.vector_store.add_documents(docs_without_vectors)
                logger.info(f'✓ Removed article {article_id} from FAISS (0 API calls, {len(text_embedding_pairs)} stored vectors)')
            else:
                # No stored vectors at all — fallback to API (shouldn't happen)
                logger.warning(f'⚠️ No stored vectors found, falling back to API re-embedding')
                self.vector_store = FAISS.from_documents(all_docs, self.embedding_model)
        except Exception as e:
            logger.error(f'❌ Stored-vector rebuild failed, falling back to API: {e}')
            self.vector_store = FAISS.from_documents(all_docs, self.embedding_model)

        self._save_index_to_disk()
        self._save_index_to_redis()
        self._rebuild_bm25_from_faiss()
        return True
    
    # ─────────────────────────────────────────────────────────────
    # Search methods
    # ─────────────────────────────────────────────────────────────

    def _rebuild_bm25_from_faiss(self):
        """Sync BM25 index from current FAISS docstore (fast, local)."""
        if self.vector_store is None:
            self.bm25 = BM25Index()
            return
        bm25_docs = [
            {
                'article_id': doc.metadata.get('article_id'),
                'title': doc.metadata.get('title', ''),
                'text': doc.page_content,
            }
            for doc in self.vector_store.docstore._dict.values()
        ]
        self.bm25.build(bm25_docs)

    def _cached_embed_query(self, text: str) -> List[float]:
        """Embed query text with Redis cache — avoids repeated API calls."""
        cache_key = f"{EMBEDDING_CACHE_PREFIX}{hashlib.sha256(text.encode()).hexdigest()[:16]}"
        try:
            from django.core.cache import cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f'✓ Embedding cache hit for query: {text[:50]}')
                return cached
        except Exception:
            pass

        # Cache miss — call API
        embedding = self.embedding_model.embed_query(text)

        try:
            from django.core.cache import cache
            cache.set(cache_key, embedding, EMBEDDING_CACHE_TTL)
        except Exception:
            pass

        return embedding

    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Pure semantic (FAISS vector) search.
        Uses cached query embeddings to avoid repeated API calls.
        Prefer hybrid_search() for better relevance.
        """
        if self.vector_store is None:
            return []

        try:
            # Use cached embedding instead of letting FAISS call the API directly
            query_embedding = self._cached_embed_query(query)
            results = self.vector_store.similarity_search_with_score_by_vector(query_embedding, k=k)
            formatted = []
            for doc, score in results:
                result = {
                    "article_id": doc.metadata.get("article_id"),
                    "title": doc.metadata.get("title"),
                    "summary": doc.metadata.get("summary"),
                    "score": float(score),
                    "metadata": doc.metadata,
                }
                if filter_metadata:
                    if all(doc.metadata.get(fk) == fv for fk, fv in filter_metadata.items()):
                        formatted.append(result)
                else:
                    formatted.append(result)
            return formatted
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    def hybrid_search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Hybrid BM25 + Vector search using Reciprocal Rank Fusion (RRF).

        RRF formula: score = 1/(rank_bm25 + 60) + 1/(rank_vector + 60)
        k=60 dampens high-rank differences — standard IR constant.

        Falls back to pure vector search if BM25 not ready.
        """
        if self.vector_store is None:
            return []

        # ── Step 1: BM25 keyword search ──
        bm25_results = self.bm25.search(query, k=k * 4) if self.bm25.is_ready else []
        bm25_rank: Dict[int, int] = {r['article_id']: r['rank'] for r in bm25_results}

        # ── Step 2: FAISS vector search ──
        try:
            # Use cached embedding to avoid API call on every search
            query_embedding = self._cached_embed_query(query)
            vector_hits = self.vector_store.similarity_search_with_score_by_vector(query_embedding, k=k * 4)
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            vector_hits = []

        vector_rank: Dict[int, int] = {}
        vector_meta: Dict[int, Dict] = {}
        for rank, (doc, score) in enumerate(vector_hits, start=1):
            aid = doc.metadata.get('article_id')
            if aid:
                vector_rank[aid] = rank
                vector_meta[aid] = doc.metadata

        # ── Step 3: RRF fusion ──
        all_ids = set(bm25_rank.keys()) | set(vector_rank.keys())
        RRF_K = 60  # standard constant

        scored = []
        for aid in all_ids:
            rrf = 0.0
            if aid in bm25_rank:
                rrf += 1.0 / (bm25_rank[aid] + RRF_K)
            if aid in vector_rank:
                rrf += 1.0 / (vector_rank[aid] + RRF_K)

            meta = vector_meta.get(aid, {})
            result = {
                'article_id': aid,
                'title': meta.get('title', bm25_results[bm25_rank[aid] - 1]['title'] if aid in bm25_rank else ''),
                'summary': meta.get('summary', ''),
                'score': round(rrf, 6),
                'bm25_rank': bm25_rank.get(aid),
                'vector_rank': vector_rank.get(aid),
                'metadata': meta,
            }

            if filter_metadata:
                if all(meta.get(fk) == fv for fk, fv in filter_metadata.items()):
                    scored.append(result)
            else:
                scored.append(result)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:k]
    
    def find_similar_articles(self, article_id: int, k: int = 5) -> List[Dict]:
        """Find articles similar to a given article (vector only)."""
        if self.vector_store is None:
            return []
        try:
            all_docs = self.vector_store.docstore._dict
            target_doc = next(
                (doc for doc in all_docs.values() if doc.metadata.get('article_id') == article_id),
                None
            )
            if not target_doc:
                print(f"⚠️ Article {article_id} not found in index")
                return []
            results = self.search(target_doc.page_content, k=k + 1)
            return [r for r in results if r['article_id'] != article_id][:k]
        except Exception as e:
            print(f"❌ Error finding similar articles: {e}")
            return []

    def find_similar_articles_hybrid(self, article_id: int, k: int = 5) -> List[Dict]:
        """Find similar articles using hybrid BM25 + vector search."""
        if self.vector_store is None:
            return []
        try:
            all_docs = self.vector_store.docstore._dict
            target_doc = next(
                (doc for doc in all_docs.values() if doc.metadata.get('article_id') == article_id),
                None
            )
            if not target_doc:
                print(f"⚠️ Article {article_id} not found in index")
                return []
            # Use title + first 500 chars of content as query for better BM25 hits
            query = target_doc.page_content[:500]
            results = self.hybrid_search(query, k=k + 1)
            return [r for r in results if r['article_id'] != article_id][:k]
        except Exception as e:
            print(f"❌ Error finding similar articles (hybrid): {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector database"""
        if self.vector_store is None:
            return {
                "total_articles": 0,
                "index_size_mb": 0,
                "status": "empty"
            }
        
        index_size = 0
        if (self.index_path / "index.faiss").exists():
            index_size = (self.index_path / "index.faiss").stat().st_size / (1024 * 1024)
        
        # Get database count
        try:
            from news.models import ArticleEmbedding
            db_count = ArticleEmbedding.objects.count()
        except:
            db_count = 0
        
        return {
            "total_articles": self.vector_store.index.ntotal,
            "db_embeddings": db_count,
            "index_size_mb": round(index_size, 2),
            "status": "ready"
        }


# Singleton instance
_vector_engine = None

def get_vector_engine() -> VectorSearchEngine:
    """Get or create the vector search engine singleton"""
    global _vector_engine
    if _vector_engine is None:
        _vector_engine = VectorSearchEngine()
    return _vector_engine
