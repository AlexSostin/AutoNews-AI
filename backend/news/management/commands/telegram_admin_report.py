"""
Management command: telegram_admin_report

Sends a beautiful daily summary report to the admin via Telegram.
Schedule via Railway cron: 0 9 * * * (every day at 09:00 UTC)

    python manage.py telegram_admin_report

Options:
    --health    Also send a system health check
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send daily admin report to Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            '--health',
            action='store_true',
            default=False,
            help='Also send a system health check message',
        )

    def handle(self, *args, **options):
        from ai_engine.modules.notify_admin import send_daily_report, notify_system_health

        self.stdout.write('📊 Sending daily report to Telegram...')
        result = send_daily_report()

        if result.get('ok'):
            self.stdout.write(self.style.SUCCESS('✅ Daily report sent!'))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ Failed to send report: {result.get("description", "unknown error")}'
            ))

        if options['health']:
            self.stdout.write('🩺 Sending health check...')
            health_result = notify_system_health()
            if health_result.get('ok'):
                self.stdout.write(self.style.SUCCESS('✅ Health check sent!'))
            else:
                self.stdout.write(self.style.ERROR('❌ Health check failed to send'))
