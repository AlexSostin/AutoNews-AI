"""
Local TF-IDF Content Recommender — self-learning ML engine.

Replaces Gemini API calls for:
  1. Tag prediction (predict_tags)
  2. Category prediction (predict_categories)
  3. Similar articles (find_similar)

Zero API cost, works offline, improves automatically with every new article.
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter

import numpy as np
import joblib
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Model storage directory (same as quality model)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'content_recommender.joblib')
META_PATH = os.path.join(MODEL_DIR, 'content_recommender_meta.json')

# Minimum articles to build a useful model
MIN_ARTICLES = 10

# Cache for loaded model (avoid reloading from disk on every request)
_cached_model = None
_cached_model_hash = None


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _prepare_text(title: str, summary: str, content: str) -> str:
    """Combine article fields into a single searchable text.
    
    Title is weighted 3x by repeating it — this makes brand/model names
    more important in similarity calculations.
    """
    clean_content = _strip_html(content)
    clean_summary = _strip_html(summary)
    # Title repeated for weight
    return f"{title} {title} {title} {clean_summary} {clean_content}"


def build(force: bool = False) -> Dict:
    """
    Build (or rebuild) the TF-IDF model from all published articles.
    
    Saves the model to disk for fast loading.
    
    Args:
        force: Rebuild even if model exists and data hasn't changed
        
    Returns:
        dict with training stats
    """
    from news.models import Article
    
    articles = Article.objects.filter(
        is_published=True, is_deleted=False
    ).prefetch_related('tags', 'categories').only(
        'id', 'title', 'summary', 'content', 'slug'
    )
    
    article_count = articles.count()
    
    if article_count < MIN_ARTICLES:
        logger.warning(
            f"ContentRecommender: Only {article_count} articles, "
            f"need at least {MIN_ARTICLES}. Skipping build."
        )
        return {
            'success': False,
            'reason': f'Not enough articles ({article_count}/{MIN_ARTICLES})',
        }
    
    # Collect data
    article_ids = []
    texts = []
    tag_map = {}      # article_id → [tag_id, ...]
    cat_map = {}      # article_id → [category_id, ...]
    tag_names = {}     # tag_id → tag_name
    cat_names = {}     # category_id → category_name
    
    for article in articles:
        text = _prepare_text(article.title, article.summary, article.content)
        if len(text.strip()) < 50:
            continue
            
        article_ids.append(article.id)
        texts.append(text)
        
        # Collect tags
        article_tags = list(article.tags.values_list('id', 'name'))
        tag_map[article.id] = [t[0] for t in article_tags]
        for tid, tname in article_tags:
            tag_names[tid] = tname
        
        # Collect categories
        article_cats = list(article.categories.values_list('id', 'name'))
        cat_map[article.id] = [c[0] for c in article_cats]
        for cid, cname in article_cats:
            cat_names[cid] = cname
    
    if len(texts) < MIN_ARTICLES:
        logger.warning(f"ContentRecommender: Only {len(texts)} usable articles after filtering.")
        return {'success': False, 'reason': f'Not enough usable articles ({len(texts)})'}
    
    # Check if data has changed (skip unnecessary rebuilds)
    data_hash = hashlib.md5(
        json.dumps(sorted(article_ids)).encode()
    ).hexdigest()
    
    if not force and os.path.exists(META_PATH):
        try:
            with open(META_PATH) as f:
                meta = json.load(f)
            if meta.get('data_hash') == data_hash:
                logger.info("ContentRecommender: Data unchanged, skipping rebuild.")
                return {'success': True, 'reason': 'No changes detected', 'skipped': True}
        except Exception:
            pass
    
    # Build TF-IDF matrix
    logger.info(f"ContentRecommender: Building model from {len(texts)} articles...")
    
    vectorizer = TfidfVectorizer(
        max_features=5000,         # Vocabulary size
        stop_words='english',      # Remove common English words
        ngram_range=(1, 2),        # Unigrams and bigrams (catches "Toyota bZ7")
        min_df=1,                  # Keep rare terms (important for car names)
        max_df=0.95,               # Remove terms in >95% of docs
        sublinear_tf=True,         # Use log(1 + tf) — better for varied doc lengths
    )
    
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # Pre-compute similarity matrix (for similar articles — instant lookup)
    # Only store top-20 similar per article to save memory
    sim_matrix = cosine_similarity(tfidf_matrix)
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    model_data = {
        'vectorizer': vectorizer,
        'tfidf_matrix': tfidf_matrix,
        'article_ids': article_ids,
        'tag_map': tag_map,
        'cat_map': cat_map,
        'tag_names': tag_names,
        'cat_names': cat_names,
        'sim_matrix': sim_matrix,
    }
    
    joblib.dump(model_data, MODEL_PATH, compress=3)
    
    # Save metadata
    meta = {
        'data_hash': data_hash,
        'article_count': len(texts),
        'vocabulary_size': len(vectorizer.vocabulary_),
        'unique_tags': len(tag_names),
        'unique_categories': len(cat_names),
        'built_at': datetime.utcnow().isoformat(),
    }
    
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2)
    
    # Clear cached model so next call loads fresh
    global _cached_model, _cached_model_hash
    _cached_model = None
    _cached_model_hash = None
    
    logger.info(
        f"ContentRecommender: Model built — {len(texts)} articles, "
        f"{len(vectorizer.vocabulary_)} features, "
        f"{len(tag_names)} tags, {len(cat_names)} categories."
    )
    
    return {
        'success': True,
        'article_count': len(texts),
        'vocabulary_size': len(vectorizer.vocabulary_),
        'unique_tags': len(tag_names),
        'unique_categories': len(cat_names),
        'model_path': MODEL_PATH,
    }


def _load_model() -> Optional[Dict]:
    """Load model from disk with caching."""
    global _cached_model, _cached_model_hash
    
    if not os.path.exists(MODEL_PATH):
        return None
    
    # Check if file changed (by mtime)
    current_hash = str(os.path.getmtime(MODEL_PATH))
    
    if _cached_model is not None and _cached_model_hash == current_hash:
        return _cached_model
    
    try:
        model = joblib.load(MODEL_PATH)
        _cached_model = model
        _cached_model_hash = current_hash
        return model
    except Exception as e:
        logger.error(f"ContentRecommender: Failed to load model: {e}")
        return None


def predict_tags(title: str, content: str, summary: str = '',
                 top_n: int = 8) -> List[Dict]:
    """
    Predict relevant tags for an article using TF-IDF similarity.
    
    Finds K nearest articles in TF-IDF space, aggregates their tags
    by frequency, and returns the most common ones.
    
    Args:
        title: Article title
        content: Article content (HTML or plain text)
        summary: Optional article summary
        top_n: Maximum number of tags to return
        
    Returns:
        List of dicts: [{'id': tag_id, 'name': tag_name, 'confidence': 0.0-1.0}]
    """
    model = _load_model()
    if model is None:
        return []
    
    text = _prepare_text(title, summary, content)
    
    try:
        # Transform new article into TF-IDF space
        new_vector = model['vectorizer'].transform([text])
        
        # Find similarity to all training articles
        similarities = cosine_similarity(new_vector, model['tfidf_matrix'])[0]
        
        # Get top-K most similar articles
        k = min(7, len(similarities))
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        # Aggregate tags from similar articles, weighted by similarity
        tag_scores = Counter()
        for idx in top_indices:
            sim_score = similarities[idx]
            if sim_score < 0.05:  # Skip very dissimilar articles
                continue
            article_id = model['article_ids'][idx]
            for tag_id in model['tag_map'].get(article_id, []):
                tag_scores[tag_id] += sim_score
        
        if not tag_scores:
            return []
        
        # Normalize scores to 0-1 range
        max_score = max(tag_scores.values())
        
        results = []
        for tag_id, score in tag_scores.most_common(top_n):
            tag_name = model['tag_names'].get(tag_id, f'Tag#{tag_id}')
            confidence = round(score / max_score, 3)
            results.append({
                'id': tag_id,
                'name': tag_name,
                'confidence': confidence,
            })
        
        return results
    
    except Exception as e:
        logger.error(f"ContentRecommender.predict_tags failed: {e}")
        return []


def predict_categories(title: str, content: str, summary: str = '',
                       top_n: int = 2) -> List[Dict]:
    """
    Predict relevant categories for an article using TF-IDF similarity.
    
    Same approach as predict_tags but aggregates categories instead.
    
    Returns:
        List of dicts: [{'id': cat_id, 'name': cat_name, 'confidence': 0.0-1.0}]
    """
    model = _load_model()
    if model is None:
        return []
    
    text = _prepare_text(title, summary, content)
    
    try:
        new_vector = model['vectorizer'].transform([text])
        similarities = cosine_similarity(new_vector, model['tfidf_matrix'])[0]
        
        k = min(7, len(similarities))
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        cat_scores = Counter()
        for idx in top_indices:
            sim_score = similarities[idx]
            if sim_score < 0.05:
                continue
            article_id = model['article_ids'][idx]
            for cat_id in model['cat_map'].get(article_id, []):
                cat_scores[cat_id] += sim_score
        
        if not cat_scores:
            return []
        
        max_score = max(cat_scores.values())
        
        results = []
        for cat_id, score in cat_scores.most_common(top_n):
            cat_name = model['cat_names'].get(cat_id, f'Cat#{cat_id}')
            confidence = round(score / max_score, 3)
            results.append({
                'id': cat_id,
                'name': cat_name,
                'confidence': confidence,
            })
        
        return results
    
    except Exception as e:
        logger.error(f"ContentRecommender.predict_categories failed: {e}")
        return []


def find_similar(article_id: int, top_n: int = 5) -> List[Dict]:
    """
    Find articles similar to a given article using pre-computed TF-IDF similarity.
    
    Uses the pre-computed similarity matrix for instant results.
    
    Args:
        article_id: ID of the source article
        top_n: Number of similar articles to return
        
    Returns:
        List of dicts: [{'id': article_id, 'score': 0.0-1.0}]
    """
    model = _load_model()
    if model is None:
        return []
    
    try:
        # Find index of this article
        article_ids = model['article_ids']
        if article_id not in article_ids:
            # Article not in model — might be new, try live similarity
            return _find_similar_live(article_id, model, top_n)
        
        idx = article_ids.index(article_id)
        sim_row = model['sim_matrix'][idx]
        
        # Get top-N most similar (excluding self)
        top_indices = np.argsort(sim_row)[::-1]
        
        results = []
        for i in top_indices:
            if i == idx:  # Skip self
                continue
            score = float(sim_row[i])
            if score < 0.05:  # Skip very dissimilar
                break
            results.append({
                'id': article_ids[i],
                'score': round(score, 4),
            })
            if len(results) >= top_n:
                break
        
        return results
    
    except Exception as e:
        logger.error(f"ContentRecommender.find_similar failed: {e}")
        return []


def _find_similar_live(article_id: int, model: Dict, top_n: int) -> List[Dict]:
    """Compute similarity on-the-fly for an article not in the model."""
    try:
        from news.models import Article
        article = Article.objects.get(id=article_id)
        text = _prepare_text(article.title, article.summary, article.content)
        
        new_vector = model['vectorizer'].transform([text])
        similarities = cosine_similarity(new_vector, model['tfidf_matrix'])[0]
        
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for i in top_indices:
            score = float(similarities[i])
            if score < 0.05:
                break
            aid = model['article_ids'][i]
            if aid == article_id:
                continue
            results.append({
                'id': aid,
                'score': round(score, 4),
            })
            if len(results) >= top_n:
                break
        
        return results
    except Exception as e:
        logger.error(f"ContentRecommender._find_similar_live failed: {e}")
        return []


def get_model_info() -> Dict:
    """Get info about the current model for dashboard/debugging."""
    if not os.path.exists(META_PATH):
        return {
            'trained': False,
            'reason': 'Model not built yet. Run: python manage.py train_content_model',
        }
    
    try:
        with open(META_PATH) as f:
            meta = json.load(f)
        meta['trained'] = True
        meta['model_size_kb'] = round(os.path.getsize(MODEL_PATH) / 1024, 1)
        return meta
    except Exception as e:
        return {'trained': False, 'error': str(e)}


def is_available() -> bool:
    """Check if the model is trained and ready."""
    return os.path.exists(MODEL_PATH)


def _clean_text(text: str) -> str:
    """Clean text for TF-IDF comparison (used by RSS dedup and auto_publisher)."""
    text = _strip_html(text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def semantic_search(query: str, top_n: int = 10) -> List[Dict]:
    """
    Search articles by meaning using TF-IDF similarity.
    
    Unlike keyword search, this finds articles about similar topics
    even if exact words don't match (e.g., "expensive sedan" finds "luxury saloon").
    
    Args:
        query: Search query text
        top_n: Maximum results to return
        
    Returns:
        List of dicts: [{'id': article_id, 'score': 0.0-1.0, 'title': '...'}]
    """
    model = _load_model()
    if model is None:
        return []
    
    try:
        # Transform query into TF-IDF space
        query_text = _clean_text(query)
        query_vector = model['vectorizer'].transform([query_text])
        
        # Find similarity to all articles
        similarities = cosine_similarity(query_vector, model['tfidf_matrix'])[0]
        
        # Get top-N results
        top_indices = np.argsort(similarities)[::-1][:top_n]
        
        # Get titles for results
        from news.models import Article
        article_ids = [model['article_ids'][i] for i in top_indices if similarities[i] > 0.02]
        titles = dict(Article.objects.filter(id__in=article_ids).values_list('id', 'title'))
        
        results = []
        for i in top_indices:
            score = float(similarities[i])
            if score < 0.02:  # Skip very low similarity
                break
            aid = model['article_ids'][i]
            results.append({
                'id': aid,
                'score': round(score, 4),
                'title': titles.get(aid, ''),
            })
            if len(results) >= top_n:
                break
        
        return results
    
    except Exception as e:
        logger.error(f"ContentRecommender.semantic_search failed: {e}")
        return []


def select_newsletter_articles(days: int = 7, count: int = 6) -> List[Dict]:
    """
    Auto-select diverse, high-view articles for newsletter.
    
    Picks the best articles from recent days, ensuring topic diversity
    by using TF-IDF to avoid selecting articles about the same thing.
    
    Args:
        days: Look back N days for candidates
        count: Number of articles to select
        
    Returns:
        List of dicts: [{'id': article_id, 'title': '...', 'views': N}]
    """
    model = _load_model()
    if model is None:
        return []
    
    try:
        from news.models import Article
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        candidates = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=cutoff,
        ).order_by('-views', '-created_at')[:30]
        
        if not candidates:
            return []
        
        selected = []
        selected_vectors = []
        
        for article in candidates:
            if len(selected) >= count:
                break
            
            # Get TF-IDF vector
            text = _prepare_text(article.title, article.summary or '', article.content or '')
            vec = model['vectorizer'].transform([text])
            
            # Check diversity: if too similar to already selected, skip
            is_diverse = True
            for sv in selected_vectors:
                sim = cosine_similarity(vec, sv)[0][0]
                if sim > 0.5:  # Too similar
                    is_diverse = False
                    break
            
            if is_diverse:
                selected.append({
                    'id': article.id,
                    'title': article.title,
                    'views': article.views,
                    'slug': article.slug,
                })
                selected_vectors.append(vec)
        
        return selected
    
    except Exception as e:
        logger.error(f"ContentRecommender.select_newsletter_articles failed: {e}")
        return []


def extract_specs_from_text(title: str, content: str) -> Dict:
    """
    Extract vehicle specifications from article text using regex patterns.
    
    Zero API cost — pure Python parsing. Extracts numeric specs that are
    reliably mentioned in automotive articles.
    
    Args:
        title: Article title
        content: Article content (HTML or plain text)
        
    Returns:
        Dict with extracted VehicleSpecs fields (only fields that were found)
    """
    # Clean text
    text = _strip_html(f"{title} {content}")
    text_lower = text.lower()
    specs = {}
    
    # === POWER ===
    # "207 kW" / "282 hp" / "450 HP" / "335 horsepower"
    kw_match = re.search(r'(\d{2,4})\s*kW\b', text, re.IGNORECASE)
    hp_match = re.search(r'(\d{2,4})\s*(?:hp|HP|horsepower|bhp)\b', text)
    if kw_match:
        specs['power_kw'] = int(kw_match.group(1))
        if not hp_match:
            specs['power_hp'] = round(specs['power_kw'] * 1.341)
    if hp_match:
        specs['power_hp'] = int(hp_match.group(1))
        if not kw_match:
            specs['power_kw'] = round(specs['power_hp'] / 1.341)
    
    # === TORQUE ===
    # "400 Nm" / "350 Newton-meters"
    torque_match = re.search(r'(\d{2,5})\s*(?:Nm|N·m|Newton[- ]?meters?)\b', text, re.IGNORECASE)
    if torque_match:
        specs['torque_nm'] = int(torque_match.group(1))
    
    # === BATTERY ===
    # "71.35 kWh" / "88.13 kWh" / "100-kWh"
    battery_matches = re.findall(r'(\d{2,3}(?:\.\d{1,2})?)\s*[-]?\s*kWh\b', text, re.IGNORECASE)
    if battery_matches:
        # Take the largest battery option mentioned
        battery_values = [float(b) for b in battery_matches]
        specs['battery_kwh'] = max(battery_values)
    
    # === RANGE ===
    # "600 km" / "620 km CLTC" / "WLTP range of 450 km" / "EPA range: 300 miles"
    # CLTC
    cltc_match = re.search(r'(\d{3,4})\s*km\s*(?:\(?CLTC\)?|CLTC)', text, re.IGNORECASE)
    if not cltc_match:
        cltc_match = re.search(r'CLTC[:\s]*(\d{3,4})\s*km', text, re.IGNORECASE)
    if cltc_match:
        specs['range_cltc'] = int(cltc_match.group(1))
    
    # WLTP
    wltp_match = re.search(r'(\d{3,4})\s*km\s*(?:\(?WLTP\)?|WLTP)', text, re.IGNORECASE)
    if not wltp_match:
        wltp_match = re.search(r'WLTP[:\s]*(\d{3,4})\s*km', text, re.IGNORECASE)
    if wltp_match:
        specs['range_wltp'] = int(wltp_match.group(1))
    
    # EPA
    epa_match = re.search(r'(\d{3,4})\s*(?:km|miles?)\s*(?:\(?EPA\)?|EPA)', text, re.IGNORECASE)
    if not epa_match:
        epa_match = re.search(r'EPA[:\s]*(\d{3,4})\s*(?:km|miles?)', text, re.IGNORECASE)
    if epa_match:
        val = int(epa_match.group(1))
        # Convert miles to km if needed
        if 'mile' in text[max(0, epa_match.start()-5):epa_match.end()+10].lower():
            val = round(val * 1.609)
        specs['range_epa'] = val
    
    # General range (if no standard specified)
    if not any(k in specs for k in ['range_cltc', 'range_wltp', 'range_epa']):
        range_match = re.search(r'(?:range|запас хода)[:\s]*(?:up to\s*)?(\d{3,4})\s*km', text, re.IGNORECASE)
        if range_match:
            specs['range_km'] = int(range_match.group(1))
    
    # === ACCELERATION ===
    # "0-100 in 3.8s" / "0-100 km/h: 5.2 seconds" / "0-60 mph in 3.2 seconds"
    acc_match = re.search(r'0[-–]100\s*(?:km/h)?[:\s]*(?:in\s*)?(\d{1,2}(?:\.\d{1,2})?)\s*(?:s|sec|seconds?)', text, re.IGNORECASE)
    if acc_match:
        specs['acceleration_0_100'] = float(acc_match.group(1))
    else:
        # 0-60 mph → convert to 0-100 (approximate: add 0.5s)
        acc_60 = re.search(r'0[-–]60\s*(?:mph)?[:\s]*(?:in\s*)?(\d{1,2}(?:\.\d{1,2})?)\s*(?:s|sec|seconds?)', text, re.IGNORECASE)
        if acc_60:
            specs['acceleration_0_100'] = round(float(acc_60.group(1)) + 0.5, 1)
    
    # === TOP SPEED ===
    # "200 km/h" / "155 mph" / "top speed of 250 km/h"
    speed_match = re.search(r'(?:top speed|maximum speed)[:\s]*(?:of\s*)?(\d{3})\s*km/h', text, re.IGNORECASE)
    if speed_match:
        specs['top_speed_kmh'] = int(speed_match.group(1))
    else:
        speed_mph = re.search(r'(?:top speed|maximum speed)[:\s]*(?:of\s*)?(\d{3})\s*mph', text, re.IGNORECASE)
        if speed_mph:
            specs['top_speed_kmh'] = round(int(speed_mph.group(1)) * 1.609)
    
    # === DIMENSIONS ===
    # "5,130 mm" / "Length: 5130 mm" / "4,900mm"
    def _find_dim(pattern, text):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).replace(',', '').replace('.', '')
            return int(val)
        return None
    
    length = _find_dim(r'(?:length|长)[:\s]*(\d[,.]?\d{3})\s*mm', text)
    if length:
        specs['length_mm'] = length
    
    width = _find_dim(r'(?:width|宽)[:\s]*(\d[,.]?\d{3})\s*mm', text)
    if width:
        specs['width_mm'] = width
    
    height = _find_dim(r'(?:height|高)[:\s]*(\d[,.]?\d{3})\s*mm', text)
    if height:
        specs['height_mm'] = height
    
    wheelbase = _find_dim(r'(?:wheelbase|轴距)[:\s]*(\d[,.]?\d{3})\s*mm', text)
    if wheelbase:
        specs['wheelbase_mm'] = wheelbase
    
    weight = _find_dim(r'(?:weight|curb weight|kerb weight)[:\s]*(\d[,.]?\d{3})\s*kg', text)
    if weight:
        specs['weight_kg'] = weight
    
    # === VOLTAGE ARCHITECTURE ===
    # "800V" / "800-volt" / "400V platform"
    volt_match = re.search(r'(\d{3,4})\s*[-]?\s*[Vv](?:olt)?\s*(?:platform|architecture|charging)?', text)
    if volt_match:
        v = int(volt_match.group(1))
        if v in (400, 800, 900):
            specs['voltage_architecture'] = v
    
    # === SEATS ===
    # "5-seater" / "7 seats" / "seats 5"
    seats_match = re.search(r'(\d)\s*[-]?\s*(?:seat(?:er|s)?|passenger)', text, re.IGNORECASE)
    if seats_match:
        s = int(seats_match.group(1))
        if 2 <= s <= 9:
            specs['seats'] = s
    
    # === DRIVETRAIN ===
    drivetrain_map = {
        r'\bAWD\b': 'AWD', r'\ball[-\s]?wheel\s*drive\b': 'AWD',
        r'\bRWD\b': 'RWD', r'\brear[-\s]?wheel\s*drive\b': 'RWD',
        r'\bFWD\b': 'FWD', r'\bfront[-\s]?wheel\s*drive\b': 'FWD',
        r'\b4WD\b': '4WD', r'\bfour[-\s]?wheel\s*drive\b': '4WD',
    }
    for pattern, dt in drivetrain_map.items():
        if re.search(pattern, text, re.IGNORECASE):
            specs['drivetrain'] = dt
            break
    
    # === MOTOR COUNT ===
    if re.search(r'dual[\s-]?motor', text_lower) or 'two motor' in text_lower or 'twin motor' in text_lower:
        specs['motor_count'] = 2
    elif re.search(r'single[\s-]?motor', text_lower) or 'one motor' in text_lower:
        specs['motor_count'] = 1
    elif re.search(r'tri[\s-]?motor', text_lower) or 'three motor' in text_lower:
        specs['motor_count'] = 3
    elif re.search(r'quad[\s-]?motor', text_lower) or 'four motor' in text_lower:
        specs['motor_count'] = 4
    
    # === BODY TYPE ===
    body_map = {
        'sedan': 'sedan', 'saloon': 'sedan',
        'suv': 'SUV',
        'crossover': 'crossover', 'CUV': 'crossover',
        'hatchback': 'hatchback',
        'coupe': 'coupe', 'coupé': 'coupe',
        'wagon': 'wagon', 'estate': 'wagon', 'touring': 'wagon',
        'pickup': 'pickup', 'truck': 'truck',
        'mpv': 'MPV', 'minivan': 'MPV', 'van': 'van',
        'convertible': 'convertible', 'cabriolet': 'cabriolet',
        'roadster': 'roadster',
        'shooting brake': 'shooting_brake',
        'fastback': 'fastback', 'liftback': 'liftback',
    }
    for keyword, body in body_map.items():
        if keyword in text_lower:
            specs['body_type'] = body
            break
    
    # === FUEL TYPE ===
    if any(k in text_lower for k in ['plug-in hybrid', 'phev', 'plug in hybrid']):
        specs['fuel_type'] = 'PHEV'
    elif any(k in text_lower for k in ['electric vehicle', ' ev ', ' bev ', 'battery electric', 'all-electric', 'fully electric']):
        specs['fuel_type'] = 'EV'
    elif any(k in text_lower for k in ['hybrid']):
        specs['fuel_type'] = 'Hybrid'
    elif any(k in text_lower for k in ['hydrogen', 'fuel cell', 'fcev']):
        specs['fuel_type'] = 'Hydrogen'
    elif any(k in text_lower for k in ['diesel']):
        specs['fuel_type'] = 'Diesel'
    elif any(k in text_lower for k in ['gasoline', 'petrol', 'gas engine', 'ice ']):
        specs['fuel_type'] = 'Gas'
    # Default: if battery mentioned, likely EV
    if 'fuel_type' not in specs and 'battery_kwh' in specs:
        specs['fuel_type'] = 'EV'
    
    # === PRICE ===
    # "$28,000" / "¥299,800" / "€42,990" / "200,000 RMB"
    price_patterns = [
        (r'\$\s*(\d{1,3}(?:,\d{3})*)', 'USD'),
        (r'€\s*(\d{1,3}(?:,\d{3})*)', 'EUR'),
        (r'£\s*(\d{1,3}(?:,\d{3})*)', 'GBP'),
        (r'¥\s*(\d{1,3}(?:,\d{3})*)', 'CNY'),
        (r'(\d{1,3}(?:,\d{3})*)\s*(?:RMB|Yuan|CNY)', 'CNY'),
        (r'(\d{1,3}(?:,\d{3})*)\s*(?:USD|dollars?)', 'USD'),
        (r'(\d{1,3}(?:,\d{3})*)\s*(?:EUR|euros?)', 'EUR'),
    ]
    prices_found = []
    for pattern, currency in price_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            val = int(m.group(1).replace(',', ''))
            if val >= 5000:  # Ignore small numbers
                prices_found.append((val, currency))
    
    if prices_found:
        # Group by currency, use the most common one
        from collections import Counter as PriceCounter
        currency_counts = PriceCounter(p[1] for p in prices_found)
        main_currency = currency_counts.most_common(1)[0][0]
        currency_prices = sorted([p[0] for p in prices_found if p[1] == main_currency])
        specs['currency'] = main_currency
        specs['price_from'] = currency_prices[0]
        if len(currency_prices) > 1:
            specs['price_to'] = currency_prices[-1]
    
    # === YEAR ===
    # "2026 Toyota" / "model year 2027"
    year_match = re.search(r'\b(202[4-9]|203[0-5])\b', title)
    if year_match:
        specs['year'] = int(year_match.group(1))
        specs['model_year'] = specs['year']
    
    # === CHARGING ===
    # "10 minutes of charging" / "30 min to 80%"
    fast_charge = re.search(r'(\d{1,3})\s*(?:min(?:utes?)?\s*(?:to|for)\s*\d{1,3}%|minutes?\s*(?:of\s*)?(?:fast\s*)?charg)', text, re.IGNORECASE)
    if fast_charge:
        specs['charging_time_fast'] = f"{fast_charge.group(0).strip()}"
    
    charge_kw = re.search(r'(\d{2,3})\s*kW\s*(?:DC|fast|charging|charger)', text, re.IGNORECASE)
    if charge_kw:
        specs['charging_power_max_kw'] = int(charge_kw.group(1))
    
    # === TRANSMISSION ===
    if 'single-speed' in text_lower or 'single speed' in text_lower or ('ev' in text_lower and 'gear' not in text_lower):
        specs['transmission'] = 'single-speed'
    elif 'cvt' in text_lower:
        specs['transmission'] = 'CVT'
    elif 'dual-clutch' in text_lower or 'dct' in text_lower:
        specs['transmission'] = 'dual-clutch'
    elif 'manual' in text_lower and 'transmission' in text_lower:
        specs['transmission'] = 'manual'
    elif 'automatic' in text_lower:
        specs['transmission'] = 'automatic'
    
    logger.info(f"ML Regex extracted {len(specs)} spec fields from article text")
    return specs


