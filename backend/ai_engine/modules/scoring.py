"""
Unified scoring module — heuristic quality, ML quality, and engagement scoring.

Sub-modules merged:
  - quality_scorer:      heuristic 1-10 scoring for pending articles
  - ml_quality_scorer:   Gradient Boosted Trees predicting engagement
  - engagement_scorer:   reader-signal based engagement score (0-10)
  - ai_detection:        detects AI-generated content patterns

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
#  AI Detection Checks — identifies AI-generated content patterns
# ══════════════════════════════════════════════════════════════════

# Source leak phrases (indicate content was generated from video/transcript)
_SOURCE_LEAK_PHRASES = [
    'transcript', 'provided text', 'video source', 'source video',
    'based on the video', 'from the video', 'in the video',
    'the narrator', 'the host mentions', 'the presenter',
    'this video', 'the video showcases', 'the video provides',
    'this is a walk-around', 'this is a walkaround',
    'as mentioned in the video', 'according to the transcript',
    'the footage shows', 'in the clip',
]

# AI filler phrases (typical of LLM-generated automotive content)
_AI_FILLER_PHRASES = [
    'a compelling proposition', 'a compelling package',
    'for the discerning', 'commanding road presence',
    'commanding presence', 'effectively eliminates range anxiety',
    'in the evolving landscape', 'isn\'t just another',
    'isn\'t merely another', 'this isn\'t your typical',
    'this is where things get interesting',
    'setting a new benchmark', 'making waves',
    'hold on to your hats', 'buckle up',
    'jaw-dropping', 'mind-blowing', 'game-changing', 'game-changer',
    'nothing short of phenomenal', 'a testament to',
    'central to its identity', 'prioritizing comfort',
    'generous dimensions', 'a prime example',
    'is here to shake up', 'dropping bombshells',
    'eye-watering', 'it\'s clear that',
    'remain to be seen', 'only time will tell',
    'it remains to be seen', 'are still emerging',
]


def ai_detection_checks(content: str, summary: str = '') -> dict:
    """
    Run AI-detection checks on article content and summary.

    Returns dict with:
      - score: 0-100 (higher = more human-like)
      - checks: dict of individual check results
      - issues: list of detected problems
      - recommendation: 'publish' | 'review' | 'reject'
    """
    plain_text = re.sub(r'<[^>]+>', '', content) if content else ''
    words = plain_text.split()
    word_count = len(words)

    if word_count < 50:
        return {
            'score': 0,
            'checks': {},
            'issues': ['Content too short for analysis'],
            'recommendation': 'reject',
        }

    checks = {}
    issues = []
    score = 100  # Start perfect, subtract for issues

    # ── 1. Source Leak Detection (max -25 points) ──────────────────
    content_lower = (content + ' ' + (summary or '')).lower()
    leak_count = sum(1 for phrase in _SOURCE_LEAK_PHRASES
                     if phrase in content_lower)
    checks['source_leaks'] = {
        'count': leak_count,
        'penalty': min(leak_count * 10, 25),
        'status': '✅' if leak_count == 0 else '❌',
    }
    if leak_count > 0:
        score -= min(leak_count * 10, 25)
        issues.append(f'{leak_count} source leak phrases (transcript/video refs)')

    # ── 2. AI Filler Phrase Count (max -20 points) ─────────────────
    filler_count = sum(1 for phrase in _AI_FILLER_PHRASES
                       if phrase in content_lower)
    checks['ai_filler'] = {
        'count': filler_count,
        'penalty': min(filler_count * 4, 20),
        'status': '✅' if filler_count <= 1 else '⚠️' if filler_count <= 3 else '❌',
    }
    if filler_count > 1:
        score -= min(filler_count * 4, 20)
        issues.append(f'{filler_count} AI filler phrases detected')

    # ── 3. Vocabulary Diversity / TTR (max -15 points) ─────────────
    # Type-Token Ratio: unique words / total words
    # Use a sliding window of 100 words for fair comparison across lengths
    if word_count >= 100:
        # Average TTR over sliding windows
        window_size = 100
        ttrs = []
        lower_words = [w.lower().strip('.,!?;:()[]"\'') for w in words]
        for i in range(0, len(lower_words) - window_size + 1, 50):
            window = lower_words[i:i + window_size]
            ttrs.append(len(set(window)) / len(window))
        avg_ttr = np.mean(ttrs) if ttrs else 0.5
    else:
        lower_words = [w.lower().strip('.,!?;:()[]"\'') for w in words]
        avg_ttr = len(set(lower_words)) / len(lower_words) if lower_words else 0.5

    vocab_penalty = 0
    if avg_ttr < 0.45:
        vocab_penalty = 15  # Very repetitive vocabulary
    elif avg_ttr < 0.55:
        vocab_penalty = 8   # Somewhat repetitive
    elif avg_ttr < 0.60:
        vocab_penalty = 3   # Slightly below human average

    checks['vocabulary_diversity'] = {
        'ttr': round(float(avg_ttr), 3),
        'penalty': vocab_penalty,
        'status': '✅' if avg_ttr >= 0.60 else '⚠️' if avg_ttr >= 0.50 else '❌',
        'note': 'Human: 0.60-0.80, AI: 0.45-0.55',
    }
    if vocab_penalty > 0:
        score -= vocab_penalty
        issues.append(f'Low vocabulary diversity (TTR={avg_ttr:.2f})')

    # ── 4. Sentence Length Variance (max -15 points) ───────────────
    # Human writers mix short punchy sentences with long detailed ones
    sentences = [s.strip() for s in re.split(r'[.!?]+', plain_text) if len(s.strip()) > 5]
    if len(sentences) >= 5:
        sent_lengths = [len(s.split()) for s in sentences]
        sent_std = float(np.std(sent_lengths))
        sent_mean = float(np.mean(sent_lengths))

        variance_penalty = 0
        if sent_std < 4:
            variance_penalty = 15  # Very uniform = robotic
        elif sent_std < 6:
            variance_penalty = 8   # Somewhat uniform
        elif sent_std < 8:
            variance_penalty = 3   # Slightly below natural

        checks['sentence_variance'] = {
            'std': round(sent_std, 2),
            'mean_length': round(sent_mean, 1),
            'sentence_count': len(sentences),
            'penalty': variance_penalty,
            'status': '✅' if sent_std >= 8 else '⚠️' if sent_std >= 5 else '❌',
            'note': 'Human: std>8, AI: std<5',
        }
        if variance_penalty > 0:
            score -= variance_penalty
            issues.append(f'Uniform sentence lengths (std={sent_std:.1f})')
    else:
        checks['sentence_variance'] = {
            'std': 0, 'penalty': 0, 'status': '⚠️',
            'note': 'Not enough sentences to analyze',
        }

    # ── 5. Spec Repetition (max -15 points) ────────────────────────
    # Numbers/specs repeated in 4+ separate paragraphs = AI pattern
    spec_re = re.compile(r'(\d[\d,.]*\s*(?:km|hp|kW|Nm|mm|kWh|mph|kg|seconds?|s)\b)',
                         re.IGNORECASE)
    body_blocks = re.findall(r'<(?:p|li)>(.*?)</(?:p|li)>', content, re.DOTALL)
    if body_blocks:
        from collections import Counter
        spec_counts = Counter()
        for block in body_blocks:
            specs_in_block = set(spec_re.findall(block))
            for spec in specs_in_block:
                spec_counts[spec.strip().lower()] += 1

        overused = {s: c for s, c in spec_counts.items() if c >= 4}
        rep_penalty = min(len(overused) * 5, 15)

        checks['spec_repetition'] = {
            'overused_specs': dict(list(overused.items())[:5]),
            'penalty': rep_penalty,
            'status': '✅' if not overused else '❌',
        }
        if overused:
            score -= rep_penalty
            issues.append(f'{len(overused)} specs repeated 4+ times')
    else:
        checks['spec_repetition'] = {'penalty': 0, 'status': '✅'}

    # ── 6. Summary Quality (max -10 points) ────────────────────────
    summary_penalty = 0
    if summary:
        summary_lower = summary.lower()
        summary_has_leaks = any(p in summary_lower for p in _SOURCE_LEAK_PHRASES)
        summary_has_html = bool(re.search(r'<[a-z]', summary, re.I))
        summary_too_short = len(summary) < 50

        if summary_has_leaks:
            summary_penalty += 5
            issues.append('Summary contains source leak phrases')
        if summary_has_html:
            summary_penalty += 3
            issues.append('Summary contains HTML tags')
        if summary_too_short:
            summary_penalty += 2
            issues.append(f'Summary too short ({len(summary)} chars)')

    checks['summary_quality'] = {
        'penalty': summary_penalty,
        'length': len(summary) if summary else 0,
        'status': '✅' if summary_penalty == 0 else '❌',
    }
    score -= summary_penalty

    # ── Final Score & Recommendation ───────────────────────────────
    final_score = max(0, min(100, score))

    if final_score >= 70:
        recommendation = 'publish'
    elif final_score >= 50:
        recommendation = 'review'
    else:
        recommendation = 'reject'

    result = {
        'score': final_score,
        'checks': checks,
        'issues': issues,
        'recommendation': recommendation,
    }

    logger.info(
        f"🔍 AI Detection: {final_score}/100 ({recommendation}) — "
        f"{len(issues)} issues: {', '.join(issues[:3]) if issues else 'none'}"
    )

    return result



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
        
        # AI source leak check (transcript/video references)
        content_lower = content.lower()
        leak_count = sum(1 for p in _SOURCE_LEAK_PHRASES if p in content_lower)
        if leak_count > 0:
            red_flags.append(f'AI source leaks ({leak_count})')
    
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
    
    # Source trust bonus: safe/green → +1, review/yellow → +0.5, unsafe/red → +0
    try:
        if pending_article.rss_feed:
            safety = pending_article.rss_feed.safety_score
            trust_bonus = {'safe': 1.0, 'review': 0.5, 'unsafe': 0.0}.get(safety, 0.5)
            score = min(10, score + int(round(trust_bonus)))
            logger.info(f"🛡️ Source trust bonus: +{trust_bonus} from '{pending_article.rss_feed.name}' (safety={safety})")
    except Exception as e:
        logger.debug(f"Source trust bonus skipped: {e}")
    
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
    
    # --- AI Detection Features ---
    content_lower = content.lower() if content else ''
    features['ai_source_leak_count'] = sum(1 for p in _SOURCE_LEAK_PHRASES if p in content_lower)
    features['ai_filler_count'] = sum(1 for p in _AI_FILLER_PHRASES if p in content_lower)
    
    # Vocabulary diversity (sliding window TTR)
    if word_count >= 100:
        lower_words_ml = [w.lower().strip('.,!?;:()[]"\'') for w in words]
        ttrs_ml = []
        for i in range(0, len(lower_words_ml) - 100 + 1, 50):
            window = lower_words_ml[i:i + 100]
            ttrs_ml.append(len(set(window)) / 100)
        features['vocabulary_ttr'] = float(np.mean(ttrs_ml)) if ttrs_ml else 0.5
    else:
        features['vocabulary_ttr'] = 0.5
    
    # Sentence length variance
    plain_ml = re.sub(r'<[^>]+>', '', content) if content else ''
    sents_ml = [s.strip() for s in re.split(r'[.!?]+', plain_ml) if len(s.strip()) > 5]
    if len(sents_ml) >= 5:
        features['sentence_length_std'] = float(np.std([len(s.split()) for s in sents_ml]))
    else:
        features['sentence_length_std'] = 0.0
    
    # --- Source trust (from RSSFeed safety) ---
    features['is_safe_source'] = 0.0  # default, overridden by caller if available
    
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
        
        # Determine source safety from RSSFeed or YouTubeChannel
        is_safe = 0.0
        try:
            from news.models import RSSNewsItem
            rss_item = RSSNewsItem.objects.filter(
                title__icontains=article.title[:60]
            ).select_related('feed').first()
            if rss_item and rss_item.feed:
                is_safe = 1.0 if getattr(rss_item.feed, 'is_safe', False) else 0.0
        except Exception:
            pass

        features = extract_features(
            title=article.title,
            content=article.content,
            specs=specs,
            tags=tag_names,
            featured_image=str(article.image) if article.image else '',
            images=[x for x in [article.image_2, article.image_3] if x],
            provider=provider,
            source_type=source_type,
        )
        features['is_safe_source'] = is_safe
        
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
      - avg scroll depth:    0.25  (from ReadMetric.max_scroll_depth_pct)
      - avg dwell time:      0.20  (from ReadMetric.dwell_time_seconds, 5min=100%)
      - completion rate:     0.10  (% of readers who scrolled ≥90%)
      - avg rating:          0.15  (from Rating model, 1-5 → 0-100%)
      - comment engagement:  0.08  (approved comments, capped at 10 → 100%)
      - micro-feedback:      0.08  (% of 👍 from ArticleMicroFeedback)
      - favorites:           0.07  (Favorite count, capped at 10 → 100%)
      - link clicks:         0.05  (InternalLinkClick count, capped at 5 → 100%)
      - penalty (feedback):  -0.03 (negative penalty for factual errors, hallucinations)
    
    Returns float 0.0 - 10.0, rounded to 1 decimal.
    """
    from news.models.interactions import (
        ReadMetric, Rating, Comment, ArticleFeedback, 
        ArticleMicroFeedback, InternalLinkClick, Favorite
    )
    
    components = {}
    
    # --- 1. Scroll Depth (0-100) → weight 0.25 ---
    scroll_data = ReadMetric.objects.filter(article=article).aggregate(
        avg_scroll=Avg('max_scroll_depth_pct'),
        count=Count('id'),
        completed=Count('id', filter=Q(max_scroll_depth_pct__gte=90))
    )
    avg_scroll = scroll_data['avg_scroll'] or 0
    read_count = scroll_data['count'] or 0
    completed_count = scroll_data['completed'] or 0
    components['scroll'] = min(avg_scroll, 100) * 0.25
    
    # --- 2. Dwell Time (0-300s normalized to 0-100) → weight 0.20 ---
    dwell_data = ReadMetric.objects.filter(
        article=article,
        dwell_time_seconds__gt=3  # filter out bots/bounces
    ).aggregate(
        avg_dwell=Avg('dwell_time_seconds')
    )
    avg_dwell = dwell_data['avg_dwell'] or 0
    dwell_normalized = min(avg_dwell / 300.0, 1.0) * 100  # 5 min = 100%
    components['dwell'] = dwell_normalized * 0.20
    
    # --- 2.5. Completion Rate (% who scrolled ≥90%) → weight 0.10 ---
    completion_rate = (completed_count / max(read_count, 1)) * 100
    components['completion'] = completion_rate * 0.10
    
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
    components['comments'] = comment_normalized * 0.08
    
    # --- 5. Micro-Feedback (% helpful) → weight 0.10 ---
    micro_data = ArticleMicroFeedback.objects.filter(article=article).aggregate(
        total=Count('id'),
        helpful=Count('id', filter=Q(is_helpful=True))
    )
    if micro_data['total'] and micro_data['total'] > 0:
        helpful_ratio = (micro_data['helpful'] / micro_data['total']) * 100
    else:
        helpful_ratio = 50  # neutral if no feedback
    components['micro'] = helpful_ratio * 0.08
    
    # --- 5.5. Favorites → weight 0.07 ---
    favorites_count = Favorite.objects.filter(article=article).count()
    favorites_normalized = min(favorites_count / 10.0, 1.0) * 100  # 10 favorites = 100%
    components['favorites'] = favorites_normalized * 0.07
    
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
    components['penalty'] = -penalty * 0.03
    
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


def compute_relevance_score(article) -> float:
    """
    Compute relevance score blending engagement with freshness decay.
    
    Formula: relevance = engagement_score × freshness_factor
    
    freshness_factor decays linearly from 1.0 (published now) to 0.3 (7+ days old).
    This keeps old high-engagement articles visible but lets fresh content compete.
    
    Returns float 0.0 - 10.0.
    """
    from django.utils import timezone
    
    engagement = article.engagement_score or 0.0
    
    # Calculate hours since publication
    if article.created_at:
        age = timezone.now() - article.created_at
        hours_old = age.total_seconds() / 3600
    else:
        hours_old = 0
    
    # Linear decay over 168 hours (7 days) with 0.3 floor
    freshness = max(0.3, 1.0 - (hours_old / 168.0))
    
    relevance = round(engagement * freshness, 2)
    return min(10.0, max(0.0, relevance))


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
