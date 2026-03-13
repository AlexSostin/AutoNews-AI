"""
Database Backup Command — pg_dump with optional cloud upload.

Usage:
    python manage.py backup_database                  # Local backup
    python manage.py backup_database --upload-r2      # Upload to Cloudflare R2
    python manage.py backup_database --cleanup        # Remove old backups (retention policy)
    python manage.py backup_database --list            # List existing backups

Retention policy: 7 daily + 4 weekly backups.
"""
import os
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

BACKUP_DIR = Path(settings.BASE_DIR) / 'backups'


class Command(BaseCommand):
    help = 'Create a compressed PostgreSQL backup with optional cloud upload'

    def add_arguments(self, parser):
        parser.add_argument('--upload-r2', action='store_true', help='Upload to Cloudflare R2')
        parser.add_argument('--cleanup', action='store_true', help='Remove old backups per retention policy')
        parser.add_argument('--list', action='store_true', help='List existing backups')
        parser.add_argument('--retention-daily', type=int, default=7, help='Keep N daily backups (default: 7)')
        parser.add_argument('--retention-weekly', type=int, default=4, help='Keep N weekly backups (default: 4)')

    def handle(self, *args, **options):
        BACKUP_DIR.mkdir(exist_ok=True)
        
        if options['list']:
            return self._list_backups()
        
        if options['cleanup']:
            return self._cleanup(options['retention_daily'], options['retention_weekly'])
        
        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'autonews_backup_{timestamp}.sql.gz'
        filepath = BACKUP_DIR / filename
        
        self.stdout.write(f'Creating backup: {filename}...')
        
        # Get database config
        db_config = settings.DATABASES['default']
        database_url = os.getenv('DATABASE_URL', '')
        
        try:
            if database_url:
                # Railway / production: use DATABASE_URL
                sql_file = BACKUP_DIR / f'temp_{timestamp}.sql'
                result = subprocess.run(
                    ['pg_dump', database_url, '-f', str(sql_file)],
                    capture_output=True, text=True, timeout=300,
                )
            else:
                # Local: use individual settings
                env = os.environ.copy()
                env['PGPASSWORD'] = db_config.get('PASSWORD', '')
                sql_file = BACKUP_DIR / f'temp_{timestamp}.sql'
                result = subprocess.run(
                    [
                        'pg_dump',
                        '-h', db_config.get('HOST', 'localhost'),
                        '-p', str(db_config.get('PORT', '5432')),
                        '-U', db_config.get('USER', 'autonews_user'),
                        '-d', db_config.get('NAME', 'autonews'),
                        '-f', str(sql_file),
                    ],
                    capture_output=True, text=True, env=env, timeout=300,
                )
            
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(
                    f'pg_dump failed: {result.stderr}'
                ))
                return
            
            # Compress
            with open(sql_file, 'rb') as f_in:
                with gzip.open(filepath, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove temp SQL file
            sql_file.unlink()
            
            size_mb = filepath.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(
                f'Backup created: {filename} ({size_mb:.1f} MB)'
            ))
            
            # Upload to R2 if requested
            if options['upload_r2']:
                self._upload_to_r2(filepath, filename)
            
            # Auto-cleanup after successful backup
            self._cleanup(options['retention_daily'], options['retention_weekly'])
            
        except subprocess.TimeoutExpired:
            self.stderr.write(self.style.ERROR('pg_dump timed out (>300s)'))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                'pg_dump not found. Install PostgreSQL client tools.'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Backup failed: {e}'))
    
    def _list_backups(self):
        """List existing backup files."""
        if not BACKUP_DIR.exists():
            self.stdout.write('No backups directory found.')
            return
        
        backups = sorted(BACKUP_DIR.glob('autonews_backup_*.sql.gz'), reverse=True)
        if not backups:
            self.stdout.write('No backups found.')
            return
        
        self.stdout.write(f'\nFound {len(backups)} backup(s):')
        for b in backups:
            size_mb = b.stat().st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(b.stat().st_mtime)
            self.stdout.write(f'  {b.name}  ({size_mb:.1f} MB)  {modified:%Y-%m-%d %H:%M}')
    
    def _cleanup(self, keep_daily=7, keep_weekly=4):
        """Apply retention policy: keep N daily + N weekly backups."""
        if not BACKUP_DIR.exists():
            return
        
        backups = sorted(BACKUP_DIR.glob('autonews_backup_*.sql.gz'), reverse=True)
        if len(backups) <= keep_daily:
            return
        
        # Keep the newest `keep_daily` backups unconditionally
        to_keep = set(backups[:keep_daily])
        
        # Also keep weekly backups (one per week, up to keep_weekly)
        weekly_kept = 0
        seen_weeks = set()
        for b in backups:
            modified = datetime.fromtimestamp(b.stat().st_mtime)
            week_key = modified.strftime('%Y-W%W')
            if week_key not in seen_weeks and weekly_kept < keep_weekly:
                to_keep.add(b)
                seen_weeks.add(week_key)
                weekly_kept += 1
        
        removed = 0
        for b in backups:
            if b not in to_keep:
                b.unlink()
                removed += 1
        
        if removed:
            self.stdout.write(f'Cleanup: removed {removed} old backup(s)')
    
    def _upload_to_r2(self, filepath, filename):
        """Upload backup to Cloudflare R2 (S3-compatible)."""
        r2_endpoint = os.getenv('R2_ENDPOINT_URL')
        r2_access_key = os.getenv('R2_ACCESS_KEY_ID')
        r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
        r2_bucket = os.getenv('R2_BUCKET_NAME', 'freshmotors-backups')
        
        if not all([r2_endpoint, r2_access_key, r2_secret_key]):
            self.stdout.write(self.style.WARNING(
                'R2 credentials not configured. Set R2_ENDPOINT_URL, '
                'R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY env vars.'
            ))
            return
        
        try:
            import boto3
            s3 = boto3.client(
                's3',
                endpoint_url=r2_endpoint,
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
            )
            
            key = f'backups/{filename}'
            s3.upload_file(str(filepath), r2_bucket, key)
            self.stdout.write(self.style.SUCCESS(
                f'Uploaded to R2: s3://{r2_bucket}/{key}'
            ))
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'boto3 not installed. Run: pip install boto3'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'R2 upload failed: {e}'))
