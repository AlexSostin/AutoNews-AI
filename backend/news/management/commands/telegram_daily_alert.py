"""
Management command: telegram_daily_alert

Checks if no articles published in last 24h and notifies admin.
Run via cron or Railway cron job:

    python manage.py telegram_daily_alert

Recommended cron schedule: every 24h at 09:00 UTC.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send Telegram alert if no articles published in the last 24 hours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Check window in hours (default: 24)',
        )

    def handle(self, *args, **options):
        from ai_engine.modules.telegram_publisher import check_and_alert_no_posts

        hours = options['hours']
        self.stdout.write(f'Checking for articles in last {hours}h...')

        alerted = check_and_alert_no_posts(hours=hours)
        if alerted:
            self.stdout.write(self.style.WARNING(
                f'⚠️  No articles found in last {hours}h. Admin alerted via Telegram.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅  Articles found in last {hours}h. No alert needed.'
            ))
