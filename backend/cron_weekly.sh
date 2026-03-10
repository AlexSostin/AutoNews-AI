#!/bin/bash
# ┌─────────────────────────────────────────────────────────────────┐
# │  FreshMotors — Weekly Cron Job                                  │
# │  Runs every Sunday at 02:00 UTC via Railway Cron Service        │
# │                                                                 │
# │  Railway Cron config:                                           │
# │    Start Command: bash cron_weekly.sh                           │
# │    Cron Schedule: 0 2 * * 0   (Sundays at 2:00 AM UTC)         │
# └─────────────────────────────────────────────────────────────────┘

set -e

echo "══════════════════════════════════════════"
echo "🗓️  FreshMotors Weekly Cron — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "══════════════════════════════════════════"

cd /app

# 1. Retrain ML Quality Scorer (GradientBoosting)
echo ""
echo "🤖 [1/3] Retraining ML Quality Scorer..."
python manage.py train_quality_model || echo "⚠️  train_quality_model failed (not enough data?) — continuing"

# 2. Rebuild Content Recommender (TF-IDF)
echo ""
echo "🧠 [2/3] Rebuilding Content Recommender..."
python manage.py train_content_model || echo "⚠️  train_content_model failed — continuing"

# 3. Update engagement scores (boosts ML training quality)
echo ""
echo "📈 [3/3] Updating engagement scores..."
python manage.py update_engagement_scores || echo "⚠️  update_engagement_scores failed — continuing"

echo ""
echo "✅ Weekly cron completed at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "══════════════════════════════════════════"
