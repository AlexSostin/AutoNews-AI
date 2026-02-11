"""
One-time migration fix command.
Fixes the django_migrations table when old migrations were deleted
and replaced with new ones, but production DB still has old records.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix migration records after migration file cleanup'

    def handle(self, *args, **options):
        cursor = connection.cursor()

        # Check current state
        cursor.execute(
            "SELECT name FROM django_migrations WHERE app='news' AND name IN ("
            "'0038_vehiclespecs', "
            "'0039_merge_0038_vehiclespecs_0038_vehiclespecs_and_more'"
            ")"
        )
        old_records = [r[0] for r in cursor.fetchall()]

        cursor.execute(
            "SELECT COUNT(*) FROM django_migrations WHERE app='news' "
            "AND name='0038_vehiclespecs_and_more'"
        )
        new_exists = cursor.fetchone()[0] > 0

        if not old_records and new_exists:
            self.stdout.write(self.style.SUCCESS(
                'Migration records already clean - nothing to fix'
            ))
            return

        if not old_records and not new_exists:
            self.stdout.write(self.style.WARNING(
                'No old or new migration records found - '
                'migration 0038_vehiclespecs_and_more needs to be applied'
            ))
            return

        self.stdout.write(f'Found old migration records: {old_records}')
        self.stdout.write(f'New migration exists: {new_exists}')

        # Delete old records
        cursor.execute(
            "DELETE FROM django_migrations WHERE app='news' AND name IN ("
            "'0038_vehiclespecs', "
            "'0039_merge_0038_vehiclespecs_0038_vehiclespecs_and_more'"
            ")"
        )
        self.stdout.write(f'Deleted {len(old_records)} old record(s)')

        # Insert new record if not exists
        if not new_exists:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) "
                "VALUES ('news', '0038_vehiclespecs_and_more', NOW())"
            )
            self.stdout.write('Inserted 0038_vehiclespecs_and_more record')

        self.stdout.write(self.style.SUCCESS('Migration records fixed!'))
