"""
Hybrid Vector Search Engine using FAISS + PostgreSQL
- FAISS: Fast in-memory similarity search
- PostgreSQL: Persistent storage for embeddings
- Auto-rebuilds FAISS from PostgreSQL on startup
"""

import os
import hashlib
from typing import List, Dict, Optional
from pathlib import Path

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import faiss


class VectorSearchEngine:
    """
    Hybrid vector search: FAISS (speed) + PostgreSQL (persistence)
    """
    
    def __init__(self):
        """Initialize the hybrid vector search engine"""
        self.embedding_model = self._get_embedding_model()
        self.vector_store = None
        self.index_path = Path("data/vector_db/faiss_index")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try to load from disk first (faster), then from database
        if (self.index_path / "index.faiss").exists():
            self._load_index_from_disk()
        else:
            self._rebuild_from_database()
    
    def _get_embedding_model(self):
        """Get Google Gemini embedding model"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
    
    def _load_index_from_disk(self):
        """Load existing FAISS index from disk (fast startup)"""
        try:
            self.vector_store = FAISS.load_local(
                str(self.index_path),
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
            print(f"✓ Loaded FAISS index from disk ({self.vector_store.index.ntotal} vectors)")
        except Exception as e:
            print(f"⚠️ Failed to load from disk: {e}")
            self._rebuild_from_database()
    
    def _rebuild_from_database(self):
        """Rebuild FAISS index from PostgreSQL (on first startup or corruption)"""
        try:
            # Import here to avoid circular dependency
            from news.models import ArticleEmbedding
            
            embeddings = ArticleEmbedding.objects.select_related('article').all()
            count = embeddings.count()
            
            if count == 0:
                print("ℹ️ No embeddings in database, starting with empty index")
                self.vector_store = None
                return
            
            print(f"🔄 Rebuilding FAISS index from {count} database embeddings...")
            
            documents = []
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
            
            if documents:
                self.vector_store = FAISS.from_documents(
                    documents,
                    self.embedding_model
                )
                self._save_index_to_disk()
                print(f"✅ Rebuilt FAISS index with {len(documents)} articles")
            
        except Exception as e:
            print(f"❌ Failed to rebuild from database: {e}")
            import traceback
            traceback.print_exc()
            self.vector_store = None
    
    def _save_index_to_disk(self):
        """Save FAISS index to disk for faster startup"""
        if self.vector_store:
            try:
                self.vector_store.save_local(str(self.index_path))
                print(f"✓ Saved FAISS index to {self.index_path}")
            except Exception as e:
                print(f"⚠️ Failed to save index: {e}")
    
    def _save_to_database(self, article_id: int, embedding: List[float], text: str):
        """Save embedding to PostgreSQL for persistence"""
        try:
            from news.models import ArticleEmbedding, Article
            
            # Calculate hash of text to detect changes
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            article = Article.objects.get(id=article_id)
            
            ArticleEmbedding.objects.update_or_create(
                article=article,
                defaults={
                    'embedding_vector': embedding,
                    'model_name': 'models/gemini-embedding-001',
                    'text_hash': text_hash
                }
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
        Index a single article (saves to both FAISS and PostgreSQL)
        
        Args:
            article_id: Article database ID
            title: Article title
            content: Article content
            summary: Article summary
            metadata: Additional metadata
        """
        # Combine text for better semantic understanding
        text_to_index = f"{title}\n\n{summary}\n\n{content}"
        
        # Generate embedding
        embedding = self.embedding_model.embed_query(text_to_index)
        
        # Save to PostgreSQL (persistent)
        self._save_to_database(article_id, embedding, text_to_index)
        
        # Prepare metadata
        doc_metadata = {
            "article_id": article_id,
            "title": title,
            "summary": summary,
            **(metadata or {})
        }
        
        # Create document
        document = Document(
            page_content=text_to_index,
            metadata=doc_metadata
        )
        
        # Add to FAISS (fast search)
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(
                [document],
                self.embedding_model
            )
        else:
            self.vector_store.add_documents([document])
        
        # Save FAISS to disk
        self._save_index_to_disk()
        
        return True
    
    def index_articles_bulk(self, articles: List[Dict]):
        """
        Index multiple articles at once (more efficient)
        
        Args:
            articles: List of dicts with keys: id, title, content, summary, metadata
        """
        documents = []
        
        for article in articles:
            text_to_index = f"{article['title']}\n\n{article.get('summary', '')}\n\n{article['content']}"
            
            # Generate embedding
            embedding = self.embedding_model.embed_query(text_to_index)
            
            # Save to PostgreSQL
            self._save_to_database(article['id'], embedding, text_to_index)
            
            doc_metadata = {
                "article_id": article['id'],
                "title": article['title'],
                "summary": article.get('summary', ''),
                **article.get('metadata', {})
            }
            
            documents.append(Document(
                page_content=text_to_index,
                metadata=doc_metadata
            ))
        
        if not documents:
            return False
        
        # Create or update FAISS index
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(
                documents,
                self.embedding_model
            )
        else:
            self.vector_store.add_documents(documents)
        
        self._save_index_to_disk()
        print(f"✓ Indexed {len(documents)} articles")
        return True
    
    def remove_article(self, article_id: int):
        """
        Remove article from both FAISS and PostgreSQL
        
        Args:
            article_id: Article ID to remove
        """
        # Remove from PostgreSQL
        self._remove_from_database(article_id)
        
        # Remove from FAISS (requires rebuild)
        if self.vector_store is None:
            return True
        
        # Get all documents except the one to delete
        all_docs = []
        for doc_id, doc in self.vector_store.docstore._dict.items():
            if doc.metadata.get("article_id") != article_id:
                all_docs.append(doc)
        
        if not all_docs:
            self.vector_store = None
            return True
        
        # Rebuild FAISS index
        self.vector_store = FAISS.from_documents(
            all_docs,
            self.embedding_model
        )
        self._save_index_to_disk()
        
        print(f"✓ Removed article {article_id} from index")
        return True
    
    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Semantic search for articles
        
        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filters
        
        Returns:
            List of matching articles with scores
        """
        if self.vector_store is None:
            return []
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query,
                k=k
            )
            
            formatted_results = []
            for doc, score in results:
                result = {
                    "article_id": doc.metadata.get("article_id"),
                    "title": doc.metadata.get("title"),
                    "summary": doc.metadata.get("summary"),
                    "score": float(score),
                    "metadata": doc.metadata
                }
                
                if filter_metadata:
                    if all(doc.metadata.get(k) == v for k, v in filter_metadata.items()):
                        formatted_results.append(result)
                else:
                    formatted_results.append(result)
            
            return formatted_results
        
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def find_similar_articles(self, article_id: int, k: int = 5) -> List[Dict]:
        """
        Find articles similar to a given article
        
        Args:
            article_id: ID of the article to find similar ones for
            k: Number of similar articles to return
        
        Returns:
            List of similar articles
        """
        if self.vector_store is None:
            return []
        
        try:
            # Find the article in the index
            all_docs = self.vector_store.docstore._dict
            target_doc = None
            
            for doc_id, doc in all_docs.items():
                if doc.metadata.get("article_id") == article_id:
                    target_doc = doc
                    break
            
            if not target_doc:
                print(f"⚠️ Article {article_id} not found in index")
                return []
            
            # Use the article's content as query
            query = target_doc.page_content
            results = self.search(query, k=k+1)
            
            # Remove the article itself from results
            similar = [r for r in results if r["article_id"] != article_id][:k]
            
            return similar
        
        except Exception as e:
            print(f"❌ Error finding similar articles: {e}")
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
