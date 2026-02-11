import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db.migrations.recorder import MigrationRecorder

# Delete the conflicting migration record
deleted = MigrationRecorder.Migration.objects.filter(
    app='news',
    name='0038_vehiclespecs_and_more'
).delete()

print(f"✓ Deleted {deleted[0]} migration record(s)")
