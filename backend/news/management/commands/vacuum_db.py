"""
Django management command to run VACUUM ANALYZE on key tables.
Run on Railway: railway run python manage.py vacuum_db
"""
from django.core.management.base import BaseCommand
from django.db import connection


TABLES_TO_VACUUM = [
    'article_embeddings',
    'news_article',
    'news_article_categories',
    'news_pendingarticle',
    'news_articletitlevariant',
]


class Command(BaseCommand):
    help = 'Run VACUUM ANALYZE on key database tables to reclaim space and update statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Run VACUUM FULL (reclaims more space but locks tables)',
        )
        parser.add_argument(
            '--table',
            type=str,
            help='Vacuum a specific table only',
        )

    def handle(self, *args, **options):
        tables = [options['table']] if options.get('table') else TABLES_TO_VACUUM
        vacuum_type = 'VACUUM FULL ANALYZE' if options.get('full') else 'VACUUM (VERBOSE, ANALYZE)'

        self.stdout.write(self.style.NOTICE(f'🧹 Running {vacuum_type} on {len(tables)} tables...'))

        # VACUUM cannot run inside a transaction block
        old_autocommit = connection.get_autocommit()
        connection.set_autocommit(True)

        try:
            with connection.cursor() as cursor:
                for table in tables:
                    self.stdout.write(f'  → {table}...')
                    try:
                        cursor.execute(f'{vacuum_type} {table}')
                        self.stdout.write(self.style.SUCCESS(f'  ✅ {table} done'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  ❌ {table}: {e}'))

                # Run global ANALYZE
                self.stdout.write('  → Running global ANALYZE...')
                cursor.execute('ANALYZE')
                self.stdout.write(self.style.SUCCESS('  ✅ Global ANALYZE done'))

        finally:
            connection.set_autocommit(old_autocommit)

        self.stdout.write(self.style.SUCCESS('\n🎉 VACUUM complete!'))
