#!/bin/bash
# ┌─────────────────────────────────────────────────────────────────┐
# │  FreshMotors — Daily Cron Job                                   │
# │  Runs every day at 06:00 UTC via Railway Cron Service           │
# │                                                                 │
# │  Railway Cron config:                                           │
# │    Start Command: bash cron_daily.sh                            │
# │    Cron Schedule: 0 6 * * *   (daily at 6:00 AM UTC)           │
# └─────────────────────────────────────────────────────────────────┘

set -e

echo "══════════════════════════════════════════"
echo "🕐 FreshMotors Daily Cron — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "══════════════════════════════════════════"

cd /app  # Railway mounts the backend dir here

# 1. Car data quality check (prices, specs, anomalies)
echo ""
echo "📊 [1/3] Running car data quality check..."
python manage.py analyze_car_data --telegram-alert || echo "⚠️  analyze_car_data failed — continuing"

# 2. Telegram alert: check if articles were published in last 24h
echo ""
echo "📱 [2/3] Checking Telegram posting health..."
python manage.py telegram_daily_alert || echo "⚠️  telegram_daily_alert failed — continuing"

# 3. Sync Redis view counts to database (keeps analytics fresh)
echo ""
echo "👁️  [3/3] Syncing view counts to DB..."
python manage.py sync_redis_views || echo "⚠️  sync_redis_views failed — continuing"

echo ""
echo "✅ Daily cron completed at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "══════════════════════════════════════════"
