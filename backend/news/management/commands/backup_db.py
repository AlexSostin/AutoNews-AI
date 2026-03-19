"""
Management command: backup_db

Creates a compressed PostgreSQL backup using pg_dump.
Can be run manually or from the scheduler.

Usage:
    python manage.py backup_db                 # dump to /tmp/
    python manage.py backup_db --upload        # dump + upload to Cloudinary
    python manage.py backup_db --keep 7        # keep last 7 local backups
"""
import os
import subprocess
import gzip
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a compressed PostgreSQL database backup'

    BACKUP_DIR = Path('/tmp/db_backups')

    def add_arguments(self, parser):
        parser.add_argument(
            '--upload',
            action='store_true',
            help='Upload backup to Cloudinary after creating it.',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=5,
            help='Number of local backups to keep (default: 5, oldest deleted first)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Custom output path for the backup file',
        )

    def handle(self, *args, **options):
        # Parse DATABASE_URL
        db_url = os.environ.get('DATABASE_URL', '')
        if not db_url:
            self.stderr.write(self.style.ERROR('❌ DATABASE_URL not set'))
            return

        parsed = urlparse(db_url)
        db_name = parsed.path.lstrip('/')
        db_host = parsed.hostname
        db_port = parsed.port or 5432
        db_user = parsed.username
        db_pass = parsed.password

        # Create backup dir
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        if options.get('output'):
            output_path = Path(options['output'])
        else:
            output_path = self.BACKUP_DIR / f'freshmotors_{timestamp}.sql.gz'

        self.stdout.write(f"🗄️  Starting backup of '{db_name}' on {db_host}...")

        # Set PGPASSWORD env var for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = db_pass or ''

        # Run pg_dump
        try:
            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '--no-owner',
                '--no-privileges',
                '-Fc',  # Custom format (compressed)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                env=env,
                timeout=300,  # 5 min timeout
            )

            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(f'❌ pg_dump failed: {result.stderr.decode()[:500]}'))
                return

            # Write compressed output
            with open(output_path, 'wb') as f:
                f.write(result.stdout)

            size_mb = output_path.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(
                f'✅ Backup created: {output_path} ({size_mb:.1f} MB)'
            ))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                '❌ pg_dump not found. Install PostgreSQL client tools:\n'
                '   apt-get install postgresql-client'
            ))
            return
        except subprocess.TimeoutExpired:
            self.stderr.write(self.style.ERROR('❌ pg_dump timed out after 5 minutes'))
            return

        # Upload to Cloudinary if requested
        if options['upload']:
            try:
                import cloudinary.uploader
                upload_result = cloudinary.uploader.upload(
                    str(output_path),
                    resource_type='raw',
                    folder='db_backups',
                    public_id=f'freshmotors_{timestamp}',
                )
                self.stdout.write(self.style.SUCCESS(
                    f'☁️  Uploaded to Cloudinary: {upload_result.get("secure_url", "?")}'
                ))
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'⚠️  Cloudinary upload failed: {e}'))

        # Cleanup old backups
        keep = options['keep']
        existing = sorted(self.BACKUP_DIR.glob('freshmotors_*.sql.gz'), reverse=True)
        if len(existing) > keep:
            for old in existing[keep:]:
                old.unlink()
                self.stdout.write(f'🧹 Deleted old backup: {old.name}')

        self.stdout.write(f'📊 Backups on disk: {min(len(existing), keep)}/{keep}')
