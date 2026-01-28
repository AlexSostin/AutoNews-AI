from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = 'Reset all article view counts to 0 for real analytics'

    def handle(self, *args, **options):
        count = Article.objects.all().update(views=0)
        self.stdout.write(
            self.style.SUCCESS(f'✅ Reset views to 0 for {count} articles')
        )
