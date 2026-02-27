"""
ML Quality Scorer — predicts article engagement using Gradient Boosted Trees.

Replaces the heuristic quality_scorer when sufficient training data is available.
Falls back to heuristic scoring when < 50 articles have engagement data.

Training data: Article features → engagement_score (from engagement_scorer.py)

Usage:
    # Predict quality for a new article:
    score = predict_quality(title, content, specs, tags, images)
    
    # Train/retrain the model:
    python manage.py train_quality_model
"""
import os
import re
import json
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger('news')

# Model storage
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MODEL_PATH = os.path.join(MODEL_DIR, 'quality_model.joblib')
META_PATH = os.path.join(MODEL_DIR, 'quality_model_meta.json')

# Minimum training samples required
MIN_TRAINING_SAMPLES = 50


# ──────────────────────────────────────────────
# Feature Extraction
# ──────────────────────────────────────────────

def extract_features(title: str, content: str, specs: dict = None,
                     tags: list = None, featured_image: str = '',
                     images: list = None, provider: str = '',
                     source_type: str = '') -> dict:
    """
    Extract ML features from an article.
    Returns dict of feature_name → float value.
    """
    specs = specs or {}
    tags = tags or []
    images = images or []
    
    # Clean HTML for text analysis
    plain_text = re.sub(r'<[^>]+>', '', content) if content else ''
    words = plain_text.split()
    word_count = len(words)
    
    # --- Text Features ---
    features = {
        'word_count': word_count,
        'char_count': len(plain_text),
        'title_length': len(title) if title else 0,
        'title_word_count': len(title.split()) if title else 0,
        
        # Structure
        'heading_count': len(re.findall(r'<h[23][^>]*>', content, re.I)) if content else 0,
        'paragraph_count': content.count('</p>') if content else 0,
        'list_item_count': content.count('<li>') if content else 0,
        'has_pros_cons': 1.0 if (content and ('Pros' in content and 'Cons' in content)) else 0.0,
        
        # Richness
        'image_count': len(images) + (1 if featured_image else 0),
        'has_featured_image': 1.0 if featured_image else 0.0,
        
        # Spec coverage
        'spec_field_count': sum(1 for v in specs.values() 
                               if v and str(v) not in ('', 'Not specified', 'None')),
        'tag_count': len(tags),
        
        # Content density (avg words per paragraph)
        'avg_words_per_paragraph': (word_count / max(content.count('</p>'), 1)) if content else 0,
        
        # Number density (how many numbers in the text — more = more specific)
        'number_density': len(re.findall(r'\d+', plain_text)) / max(word_count, 1) if plain_text else 0,
        
        # Source type encoding
        'is_youtube': 1.0 if source_type == 'youtube' else 0.0,
        'is_rss': 1.0 if source_type in ('rss', 'rss_original') else 0.0,
        
        # Provider encoding
        'is_gemini': 1.0 if provider == 'gemini' else 0.0,
        'is_groq': 1.0 if provider == 'groq' else 0.0,
    }
    
    # --- Brand popularity (known popular brands get a boost) ---
    brand = specs.get('make', '').lower()
    popular_brands = {'tesla', 'byd', 'nio', 'xpeng', 'zeekr', 'bmw', 'mercedes', 'audi', 'porsche'}
    features['is_popular_brand'] = 1.0 if brand in popular_brands else 0.0
    
    # --- Price segment ---
    price_str = str(specs.get('price', specs.get('price_usd', '')))
    try:
        price = float(re.sub(r'[^\d.]', '', price_str)) if price_str else 0
    except (ValueError, TypeError):
        price = 0
    features['price_segment'] = (
        0 if price == 0 else
        1 if price < 30000 else
        2 if price < 60000 else
        3 if price < 100000 else 4
    )
    
    # --- Red flags ---
    red_flags = 0
    if content:
        for flag in ['lorem ipsum', 'TODO', 'FIXME', '[insert', '{placeholder']:
            if flag.lower() in content.lower():
                red_flags += 1
    features['red_flag_count'] = red_flags
    
    return features


# ──────────────────────────────────────────────
# Model Training
# ──────────────────────────────────────────────

def train_model(force=False):
    """
    Train a GradientBoostingRegressor on articles with engagement data.
    
    Returns:
        dict with training stats (samples, r2_score, feature_importances, etc.)
    """
    from news.models import Article
    
    # Get articles with real engagement data
    articles = Article.objects.filter(
        is_published=True,
        is_deleted=False,
        engagement_score__gt=0,
        engagement_updated_at__isnull=False,
    )
    
    count = articles.count()
    if count < MIN_TRAINING_SAMPLES and not force:
        msg = (f"Not enough training data: {count}/{MIN_TRAINING_SAMPLES} articles "
               f"have engagement scores. Collect more reader data first.")
        logger.warning(f"[ML-SCORER] {msg}")
        return {'success': False, 'reason': msg, 'samples': count}
    
    logger.info(f"[ML-SCORER] Training on {count} articles...")
    
    # Extract features and targets
    X_data = []
    y_data = []
    feature_names = None
    
    for article in articles.iterator():
        # Determine source type and provider
        source_type = article.image_source or 'unknown'
        provider = ''
        try:
            meta = article.generation_metadata or {}
            provider = meta.get('provider', '')
        except Exception:
            pass
        
        # Get specs from CarSpecification if available
        specs = {}
        try:
            car_spec = article.carspecification
            specs = {
                'make': car_spec.make or '',
                'model': car_spec.model or '',
                'year': car_spec.release_date or '',
                'engine': car_spec.engine or '',
                'horsepower': car_spec.horsepower or '',
                'price': car_spec.price or '',
            }
        except Exception:
            pass
        
        # Get tags
        tag_names = list(article.tags.values_list('name', flat=True))
        
        features = extract_features(
            title=article.title,
            content=article.content,
            specs=specs,
            tags=tag_names,
            featured_image=str(article.image) if article.image else '',
            images=[str(article.image_2), str(article.image_3)],
            provider=provider,
            source_type=source_type,
        )
        
        if feature_names is None:
            feature_names = sorted(features.keys())
        
        X_data.append([features[f] for f in feature_names])
        y_data.append(article.engagement_score)
    
    X = np.array(X_data, dtype=np.float64)
    y = np.array(y_data, dtype=np.float64)
    
    # Train GradientBoosting
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score
    import joblib
    
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
    )
    
    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=min(5, count), scoring='r2')
    
    # Train on full dataset
    model.fit(X, y)
    
    # Feature importances
    importances = dict(zip(feature_names, model.feature_importances_))
    top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:8]
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    
    # Save metadata
    meta = {
        'trained_at': datetime.utcnow().isoformat(),
        'samples': count,
        'feature_names': feature_names,
        'cv_r2_mean': round(float(np.mean(cv_scores)), 4),
        'cv_r2_std': round(float(np.std(cv_scores)), 4),
        'top_features': {k: round(float(v), 4) for k, v in top_features},
        'target_range': [round(float(y.min()), 2), round(float(y.max()), 2)],
    }
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2)
    
    logger.info(
        f"[ML-SCORER] ✅ Model trained: {count} samples, "
        f"CV R²={meta['cv_r2_mean']:.3f}±{meta['cv_r2_std']:.3f}"
    )
    logger.info(f"[ML-SCORER] Top features: {[f'{k}={v:.3f}' for k, v in top_features]}")
    
    return {
        'success': True,
        'samples': count,
        'cv_r2_mean': meta['cv_r2_mean'],
        'cv_r2_std': meta['cv_r2_std'],
        'top_features': meta['top_features'],
    }


# ──────────────────────────────────────────────
# Prediction
# ──────────────────────────────────────────────

def _load_model():
    """Load trained model and metadata. Returns (model, feature_names) or (None, None)."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
        return None, None
    
    try:
        import joblib
        model = joblib.load(MODEL_PATH)
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
        return model, meta.get('feature_names', [])
    except Exception as e:
        logger.warning(f"[ML-SCORER] Failed to load model: {e}")
        return None, None


def predict_quality(title: str, content: str, specs: dict = None,
                    tags: list = None, featured_image: str = '',
                    images: list = None, provider: str = '',
                    source_type: str = '') -> dict:
    """
    Predict article quality using ML model.
    Falls back to heuristic scorer if model not available.
    
    Returns:
        {
            'score': float (1-10),
            'method': 'ml' | 'heuristic',
            'confidence': float (0-1),  # only for ML
            'top_factors': dict,         # only for ML
        }
    """
    model, feature_names = _load_model()
    
    if model is None or feature_names is None:
        # Fallback to heuristic
        from ai_engine.modules.quality_scorer import calculate_quality_score
        heuristic_score = calculate_quality_score(
            title=title, content=content, specs=specs,
            tags=tags, featured_image=featured_image, images=images,
        )
        return {
            'score': heuristic_score,
            'method': 'heuristic',
            'reason': 'ML model not trained yet (need 50+ articles with engagement data)',
        }
    
    # Extract features
    features = extract_features(
        title=title, content=content, specs=specs,
        tags=tags, featured_image=featured_image, images=images,
        provider=provider, source_type=source_type,
    )
    
    # Build feature vector in correct order
    X = np.array([[features.get(f, 0) for f in feature_names]], dtype=np.float64)
    
    # Predict
    predicted = model.predict(X)[0]
    score = max(1.0, min(10.0, round(predicted, 1)))
    
    # Estimate confidence from tree variance
    try:
        tree_predictions = [tree.predict(X)[0] for tree in model.estimators_.flatten()]
        confidence = 1.0 - min(float(np.std(tree_predictions)) / 3.0, 1.0)
    except Exception:
        confidence = 0.5
    
    # Top contributing features
    importances = dict(zip(feature_names, model.feature_importances_))
    top_factors = {}
    for fname, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_factors[fname] = {
            'importance': round(float(imp), 3),
            'value': features.get(fname, 0),
        }
    
    logger.info(
        f"[ML-SCORER] Predicted: {score}/10 (confidence={confidence:.2f}, method=ML)"
    )
    
    return {
        'score': score,
        'method': 'ml',
        'confidence': round(confidence, 3),
        'top_factors': top_factors,
    }


def get_model_info() -> dict:
    """Get info about the current ML model for dashboard display."""
    if not os.path.exists(META_PATH):
        return {'trained': False, 'reason': 'No model trained yet'}
    
    try:
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
        meta['trained'] = True
        meta['model_path'] = MODEL_PATH
        return meta
    except Exception as e:
        return {'trained': False, 'reason': str(e)}
