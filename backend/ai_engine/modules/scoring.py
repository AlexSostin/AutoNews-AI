"""
Unified scoring module — heuristic quality, ML quality, and engagement scoring.

Sub-modules merged:
  - quality_scorer:      heuristic 1-10 scoring for pending articles
  - ml_quality_scorer:   Gradient Boosted Trees predicting engagement
  - engagement_scorer:   reader-signal based engagement score (0-10)

Score range: 1-10
Threshold for auto-publish is configurable in AutomationSettings (default: 7)
"""
import os
import re
import json
import logging
import numpy as np
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Avg, Count, Q, F

logger = logging.getLogger('news')


# ══════════════════════════════════════════════════════════════════
#  Heuristic Quality Scorer
# ══════════════════════════════════════════════════════════════════

def calculate_quality_score(title: str, content: str, specs: dict = None,
                            tags: list = None, featured_image: str = '',
                            images: list = None) -> int:
    """
    Calculate a quality score (1-10) for a pending article.
    
    Scoring breakdown:
    - Content length:     0-2 points
    - Title quality:      0-2 points  
    - Content structure:  0-2 points
    - Has images:         0-1 point
    - Has specs/data:     0-1 point
    - Has tags:           0-1 point
    - No red flags:       0-1 point
    - Spec coverage:      0-1 bonus point (≥70% of key fields filled)
    """
    score = 0
    details = []
    
    # --- Content Length (0-2 points) ---
    word_count = len(content.split()) if content else 0
    if word_count >= 800:
        score += 2
        details.append(f"length: 2/2 ({word_count} words)")
    elif word_count >= 400:
        score += 1
        details.append(f"length: 1/2 ({word_count} words)")
    else:
        details.append(f"length: 0/2 ({word_count} words - too short)")
    
    # --- Title Quality (0-2 points) ---
    title_len = len(title) if title else 0
    title_words = len(title.split()) if title else 0
    title_score = 0
    
    if 30 <= title_len <= 100 and title_words >= 4:
        title_score += 1  # Good length
    if title and not title.isupper() and '???' not in title:
        title_score += 1  # Not all-caps, no garbage
    
    score += title_score
    details.append(f"title: {title_score}/2 ({title_len} chars, {title_words} words)")
    
    # --- Content Structure (0-2 points) ---
    structure_score = 0
    
    # Has headings (H2/H3)
    headings = len(re.findall(r'<h[23][^>]*>', content, re.IGNORECASE)) if content else 0
    if headings == 0:
        headings = len(re.findall(r'^#{2,3}\s', content, re.MULTILINE)) if content else 0
    
    if headings >= 2:
        structure_score += 1
    
    # Has paragraphs (not a wall of text)
    paragraphs = content.count('</p>') if content else 0
    if paragraphs == 0:
        paragraphs = content.count('\n\n') if content else 0
    
    if paragraphs >= 3:
        structure_score += 1
    
    score += structure_score
    details.append(f"structure: {structure_score}/2 ({headings} headings, {paragraphs} paragraphs)")
    
    # --- Has Images (0-1 point) ---
    has_image = bool(featured_image) or bool(images and len(images) > 0)
    if has_image:
        score += 1
        details.append("images: 1/1")
    else:
        details.append("images: 0/1 (no featured image — not penalized)")
    
    # --- Has Specs/Data (0-1 point) ---
    has_specs = bool(specs and any(v for v in specs.values() if v))
    if has_specs:
        score += 1
        details.append(f"specs: 1/1 ({len([v for v in specs.values() if v])} fields)")
    else:
        details.append("specs: 0/1")
    
    # --- Has Tags (0-1 point) ---
    has_tags = bool(tags and len(tags) >= 2)
    if has_tags:
        score += 1
        details.append(f"tags: 1/1 ({len(tags)} tags)")
    else:
        details.append(f"tags: 0/1 ({len(tags) if tags else 0} tags)")
    
    # --- Red Flags Check (0-1 point) ---
    red_flags = []
    if content:
        # Check for placeholder text
        placeholders = ['lorem ipsum', 'TODO', 'FIXME', '[insert', '{placeholder']
        for p in placeholders:
            if p.lower() in content.lower():
                red_flags.append(p)
        
        # Check for very repetitive content
        sentences = re.split(r'[.!?]', content)
        if len(sentences) > 5:
            unique_ratio = len(set(s.strip().lower() for s in sentences if s.strip())) / len(sentences)
            if unique_ratio < 0.5:
                red_flags.append('repetitive content')
    
    if not red_flags:
        score += 1
        details.append("quality: 1/1 (no red flags)")
    else:
        details.append(f"quality: 0/1 (flags: {', '.join(red_flags)})")
    
    # --- Spec Coverage Bonus (0-1 point) ---
    spec_coverage_bonus = 0
    if specs:
        key_fields = ['make', 'model', 'engine', 'horsepower', 'torque',
                       'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'year']
        filled = sum(1 for f in key_fields
                     if specs.get(f) and str(specs[f]) not in ('', 'Not specified', 'None'))
        coverage_pct = filled / len(key_fields) * 100
        if coverage_pct >= 70:
            spec_coverage_bonus = 1
            score += 1
            details.append(f"spec_coverage: 1/1 ({filled}/{len(key_fields)} = {coverage_pct:.0f}%)")
        else:
            details.append(f"spec_coverage: 0/1 ({filled}/{len(key_fields)} = {coverage_pct:.0f}%)")
    else:
        details.append("spec_coverage: 0/1 (no specs)")
    
    # Scale to max 10
    max_possible = 10 if has_image else 9
    max_possible += spec_coverage_bonus
    if max_possible > 10:
        final_score = max(1, min(10, round(score * 10 / max_possible)))
    else:
        final_score = max(1, min(10, score))
    
    logger.info(f"📊 Quality score: {final_score}/10 — {'; '.join(details)}")
    
    return final_score


def score_pending_article(pending_article) -> int:
    """
    Calculate and save quality score for a PendingArticle instance.
    Tries ML model first, falls back to heuristic if ML not available.
    """
    # Try ML scorer first
    try:
        # Determine source type and provider
        source_type = pending_article.image_source or 'unknown'
        provider = ''
        
        ml_result = predict_quality(
            title=pending_article.title,
            content=pending_article.content,
            specs=pending_article.specs,
            tags=pending_article.tags,
            featured_image=pending_article.featured_image,
            images=pending_article.images,
            provider=provider,
            source_type=source_type,
        )
        
        if ml_result.get('method') == 'ml':
            score = int(round(ml_result['score']))
            logger.info(
                f"🧠 ML quality score: {score}/10 "
                f"(confidence={ml_result.get('confidence', 0):.2f})"
            )
            pending_article.quality_score = score
            pending_article.save(update_fields=['quality_score'])
            return score
    except Exception as e:
        logger.debug(f"ML scorer unavailable, using heuristic: {e}")
    
    # Fallback to heuristic
    score = calculate_quality_score(
        title=pending_article.title,
        content=pending_article.content,
        specs=pending_article.specs,
        tags=pending_article.tags,
        featured_image=pending_article.featured_image,
        images=pending_article.images,
    )
    
    pending_article.quality_score = score
    pending_article.save(update_fields=['quality_score'])
    
    return score


# ══════════════════════════════════════════════════════════════════
#  ML Quality Scorer (Gradient Boosted Trees)
# ══════════════════════════════════════════════════════════════════

# Model storage
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MODEL_PATH = os.path.join(MODEL_DIR, 'quality_model.joblib')
META_PATH = os.path.join(MODEL_DIR, 'quality_model_meta.json')

# Minimum training samples required
MIN_TRAINING_SAMPLES = 50


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
        # Fallback to heuristic (local call, no cross-import needed)
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


# ══════════════════════════════════════════════════════════════════
#  Engagement Scorer (reader signals → 0-10 metric)
# ══════════════════════════════════════════════════════════════════

def compute_engagement_score(article) -> float:
    """
    Compute engagement score (0.0 - 10.0) for a single article.
    
    Scoring breakdown (weights sum to 1.0):
      - avg scroll depth:    0.30  (from ReadMetric.max_scroll_depth_pct)
      - avg dwell time:      0.25  (from ReadMetric.dwell_time_seconds, 5min=100%)
      - avg rating:          0.15  (from Rating model, 1-5 → 0-100%)
      - comment engagement:  0.10  (approved comments, capped at 10 → 100%)
      - micro-feedback:      0.10  (% of 👍 from ArticleMicroFeedback)
      - link clicks:         0.05  (InternalLinkClick count, capped at 5 → 100%)
      - penalty (feedback):  -0.05 (negative penalty for factual errors, hallucinations)
    
    Returns float 0.0 - 10.0, rounded to 1 decimal.
    """
    from news.models.interactions import (
        ReadMetric, Rating, Comment, ArticleFeedback, 
        ArticleMicroFeedback, InternalLinkClick
    )
    
    components = {}
    
    # --- 1. Scroll Depth (0-100) → weight 0.30 ---
    scroll_data = ReadMetric.objects.filter(article=article).aggregate(
        avg_scroll=Avg('max_scroll_depth_pct'),
        count=Count('id')
    )
    avg_scroll = scroll_data['avg_scroll'] or 0
    read_count = scroll_data['count'] or 0
    components['scroll'] = min(avg_scroll, 100) * 0.30
    
    # --- 2. Dwell Time (0-300s normalized to 0-100) → weight 0.25 ---
    dwell_data = ReadMetric.objects.filter(
        article=article,
        dwell_time_seconds__gt=3  # filter out bots/bounces
    ).aggregate(
        avg_dwell=Avg('dwell_time_seconds')
    )
    avg_dwell = dwell_data['avg_dwell'] or 0
    dwell_normalized = min(avg_dwell / 300.0, 1.0) * 100  # 5 min = 100%
    components['dwell'] = dwell_normalized * 0.25
    
    # --- 3. Average Rating (1-5 → 0-100) → weight 0.15 ---
    rating_data = Rating.objects.filter(article=article).aggregate(
        avg_rating=Avg('rating'),
        count=Count('id')
    )
    avg_rating = rating_data['avg_rating'] or 0
    rating_count = rating_data['count'] or 0
    if rating_count > 0:
        rating_normalized = ((avg_rating - 1) / 4.0) * 100  # 1→0%, 5→100%
    else:
        rating_normalized = 50  # neutral if no ratings
    components['rating'] = rating_normalized * 0.15
    
    # --- 4. Comment Engagement → weight 0.10 ---
    comment_count = Comment.objects.filter(
        article=article,
        is_approved=True
    ).count()
    comment_normalized = min(comment_count / 10.0, 1.0) * 100  # 10 comments = 100%
    components['comments'] = comment_normalized * 0.10
    
    # --- 5. Micro-Feedback (% helpful) → weight 0.10 ---
    micro_data = ArticleMicroFeedback.objects.filter(article=article).aggregate(
        total=Count('id'),
        helpful=Count('id', filter=Q(is_helpful=True))
    )
    if micro_data['total'] and micro_data['total'] > 0:
        helpful_ratio = (micro_data['helpful'] / micro_data['total']) * 100
    else:
        helpful_ratio = 50  # neutral if no feedback
    components['micro'] = helpful_ratio * 0.10
    
    # --- 6. Internal Link Clicks → weight 0.05 ---
    click_count = InternalLinkClick.objects.filter(source_article=article).count()
    click_normalized = min(click_count / 5.0, 1.0) * 100  # 5 clicks = 100%
    components['clicks'] = click_normalized * 0.05
    
    # --- 7. Negative Feedback Penalty → weight -0.05 ---
    negative_feedback = ArticleFeedback.objects.filter(
        article=article,
        category__in=['factual_error', 'hallucination']
    ).count()
    penalty = min(negative_feedback / 3.0, 1.0) * 100  # 3 reports = max penalty
    components['penalty'] = -penalty * 0.05
    
    # --- Compute Total ---
    raw_score = sum(components.values())
    
    # Scale from 0-100 to 0-10 and clamp
    final_score = round(max(0.0, min(10.0, raw_score / 10.0)), 1)
    
    # Confidence adjustment: if very few readers, pull toward neutral
    if read_count < 3:
        # Blend with neutral score (5.0) based on data availability
        confidence = read_count / 3.0
        final_score = round(5.0 * (1 - confidence) + final_score * confidence, 1)
    
    logger.info(
        f"📊 Engagement score for '{article.title[:40]}': {final_score}/10 "
        f"(reads={read_count}, dwell={avg_dwell:.0f}s, scroll={avg_scroll:.0f}%, "
        f"rating={avg_rating:.1f}/5×{rating_count}, comments={comment_count})"
    )
    
    return final_score


def compute_engagement_details(article) -> dict:
    """
    Return detailed breakdown of engagement score (for dashboard/debugging).
    """
    from news.models.interactions import (
        ReadMetric, Rating, Comment, ArticleFeedback,
        ArticleMicroFeedback, InternalLinkClick
    )
    
    scroll_data = ReadMetric.objects.filter(article=article).aggregate(
        avg_scroll=Avg('max_scroll_depth_pct'),
        count=Count('id')
    )
    dwell_data = ReadMetric.objects.filter(
        article=article, dwell_time_seconds__gt=3
    ).aggregate(avg_dwell=Avg('dwell_time_seconds'))
    
    rating_data = Rating.objects.filter(article=article).aggregate(
        avg_rating=Avg('rating'), count=Count('id')
    )
    
    comment_count = Comment.objects.filter(article=article, is_approved=True).count()
    
    micro_data = ArticleMicroFeedback.objects.filter(article=article).aggregate(
        total=Count('id'),
        helpful=Count('id', filter=Q(is_helpful=True))
    )
    
    click_count = InternalLinkClick.objects.filter(source_article=article).count()
    
    neg_feedback = ArticleFeedback.objects.filter(
        article=article, category__in=['factual_error', 'hallucination']
    ).count()
    
    return {
        'engagement_score': article.engagement_score,
        'read_count': scroll_data['count'] or 0,
        'avg_scroll_pct': round(scroll_data['avg_scroll'] or 0, 1),
        'avg_dwell_seconds': round(dwell_data['avg_dwell'] or 0, 1),
        'avg_rating': round(rating_data['avg_rating'] or 0, 1),
        'rating_count': rating_data['count'] or 0,
        'comment_count': comment_count,
        'micro_feedback_total': micro_data['total'] or 0,
        'micro_feedback_helpful': micro_data['helpful'] or 0,
        'internal_link_clicks': click_count,
        'negative_feedback_count': neg_feedback,
    }


def update_engagement_scores(days_back=30, force_all=False):
    """
    Batch update engagement scores for published articles.
    
    Args:
        days_back: only recalculate articles published within N days
        force_all: recalculate ALL published articles
    
    Returns:
        dict with stats: updated count, avg score, etc.
    """
    from news.models import Article
    
    if force_all:
        articles = Article.objects.filter(is_published=True, is_deleted=False)
    else:
        cutoff = timezone.now() - timedelta(days=days_back)
        articles = Article.objects.filter(
            is_published=True,
            is_deleted=False,
        ).filter(
            Q(created_at__gte=cutoff) |
            Q(engagement_updated_at__isnull=True) |
            Q(engagement_updated_at__lt=cutoff)
        )
    
    total = articles.count()
    scores = []
    updated = 0
    
    for article in articles.iterator():
        try:
            score = compute_engagement_score(article)
            article.engagement_score = score
            article.engagement_updated_at = timezone.now()
            article.save(update_fields=['engagement_score', 'engagement_updated_at'])
            scores.append(score)
            updated += 1
        except Exception as e:
            logger.error(f"Failed to compute engagement for article #{article.id}: {e}")
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    stats = {
        'total_eligible': total,
        'updated': updated,
        'avg_score': round(avg_score, 2),
        'min_score': round(min(scores), 1) if scores else 0,
        'max_score': round(max(scores), 1) if scores else 0,
    }
    
    logger.info(f"📊 Engagement score update complete: {stats}")
    return stats
