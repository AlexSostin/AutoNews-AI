"""
Engagement Score Calculator — converts reader signals into a single 0-10 metric.

Combines:
- Scroll depth (from ReadMetric)
- Dwell time (from ReadMetric)
- Star ratings (from Rating model)
- Comments (from Comment model)
- Micro-feedback (from ArticleMicroFeedback)
- Negative feedback (from ArticleFeedback) — penalty
- Internal link clicks (from InternalLinkClick)

Used for:
- ML quality model training (Phase 2)
- Prompt optimization loop (Phase 3)
- Provider selection per brand (Phase 4)
- Auto-publish threshold calibration
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q, F

logger = logging.getLogger('news')


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
