from django.core.management.base import BaseCommand
from news.services.gsc_service import GSCService

class Command(BaseCommand):
    help = 'Sync data from Google Search Console'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to sync'
        )

    def handle(self, *args, **options):
        days = options['days']
        self.stdout.write(f'🚀 Starting GSC sync for the last {days} days...')
        
        service = GSCService()
        success = service.sync_data(days=days)
        
        if success:
            self.stdout.write(self.style.SUCCESS('✅ GSC sync completed successfully'))
        else:
            self.stdout.write(self.style.ERROR('❌ GSC sync failed. Check logs for details.'))
