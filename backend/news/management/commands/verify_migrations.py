"""
Management command: verify_migrations

Runs AFTER 'migrate' to verify that critical database columns and tables
actually exist in the database the current process is connected to.

This prevents the "split-DB" scenario where Django marks migrations as applied
but the actual ALTER TABLE ran on a different PostgreSQL instance (e.g. due to
Docker DNS inconsistency after docker compose down/up).

Usage:
    python manage.py verify_migrations
    python manage.py verify_migrations --fix   # Auto-apply missing columns
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


# ─── Define critical schema expectations ──────────────────────────────────────
# Format: (table_name, column_name, sql_type_prefix)
# sql_type_prefix is checked with LIKE so 'double' matches 'double precision'
CRITICAL_COLUMNS = [
    ('news_article', 'id', 'bigint'),
    ('news_article', 'title', 'character'),
    ('news_article', 'engagement_score', 'double'),
    ('news_article', 'engagement_updated_at', 'timestamp'),
    ('news_article', 'image_source', 'character'),
    ('news_frontendeventlog', 'url', 'character'),
    ('news_backenderrorlog', 'id', 'bigint'),
]

# Tables that must exist
CRITICAL_TABLES = [
    'news_article',
    'news_backenderrorlog',
    'news_frontendeventlog',
]


class Command(BaseCommand):
    help = 'Verify that critical database columns and tables exist after migration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='Attempt to auto-fix missing columns (run migrate again with fresh connection)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Verifying database schema ==='))

        # 1. Report which DB we're connected to
        with connection.cursor() as cursor:
            cursor.execute("SELECT inet_server_addr(), current_database(), current_user")
            row = cursor.fetchone()
            self.stdout.write(f'  Connected to: {row[0]}:{row[1]} as {row[2]}')

        # 2. Check critical tables
        missing_tables = []
        for table in CRITICAL_TABLES:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = 'public')",
                    [table]
                )
                exists = cursor.fetchone()[0]
                if exists:
                    self.stdout.write(f'  ✅ Table {table}')
                else:
                    self.stdout.write(self.style.ERROR(f'  ❌ Table {table} — MISSING!'))
                    missing_tables.append(table)

        # 3. Check critical columns
        missing_columns = []
        for table, column, expected_type in CRITICAL_COLUMNS:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT data_type FROM information_schema.columns 
                       WHERE table_name = %s AND column_name = %s AND table_schema = 'public'""",
                    [table, column]
                )
                row = cursor.fetchone()
                if row:
                    actual_type = row[0]
                    if expected_type in actual_type:
                        self.stdout.write(f'  ✅ {table}.{column} ({actual_type})')
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠️  {table}.{column} — type mismatch: expected {expected_type}*, got {actual_type}'
                        ))
                else:
                    self.stdout.write(self.style.ERROR(f'  ❌ {table}.{column} — MISSING!'))
                    missing_columns.append((table, column, expected_type))

        # 4. Summary
        if missing_tables or missing_columns:
            msg = f'\n❌ Schema verification FAILED: {len(missing_tables)} missing tables, {len(missing_columns)} missing columns'
            self.stdout.write(self.style.ERROR(msg))

            if options.get('fix'):
                self.stdout.write(self.style.WARNING('\n🔧 --fix flag set, retrying migrations...'))
                from django.core.management import call_command
                # Close all connections to force fresh ones
                from django.db import connections
                for conn_name in connections:
                    connections[conn_name].close()
                call_command('migrate', '--run-syncdb', verbosity=1)
                self.stdout.write(self.style.SUCCESS('Migration retry complete. Run verify_migrations again to check.'))
            else:
                self.stderr.write(
                    '\n💡 Try: python manage.py verify_migrations --fix\n'
                    '   Or:  python manage.py migrate (check which DB you are connected to!)\n'
                )
                raise CommandError(
                    'Database schema does not match expected state. '
                    'This usually means migrations ran on a different database instance. '
                    'See output above for details.'
                )
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Schema verification passed: {len(CRITICAL_TABLES)} tables, {len(CRITICAL_COLUMNS)} columns OK'
            ))
