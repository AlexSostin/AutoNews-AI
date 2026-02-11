"""
Management command to extract vehicle specifications from all articles using AI
"""

from django.core.management.base import BaseCommand
from news.models import Article, VehicleSpecs
from ai_engine.modules.specs_extractor import extract_vehicle_specs
import time


class Command(BaseCommand):
    help = 'Extract vehicle specs from all articles using AI'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-extract even if specs already exist',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of articles to process (for testing)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API calls in seconds (to avoid rate limits)',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        delay = options['delay']
        
        self.stdout.write(self.style.SUCCESS('🤖 Starting AI specs extraction...'))
        
        # Get articles to process
        articles_qs = Article.objects.filter(
            is_published=True,
            is_deleted=False
        )
        
        if not force:
            # Only process articles without specs
            articles_qs = articles_qs.filter(vehicle_specs__isnull=True)
            self.stdout.write('📋 Processing only articles without existing specs')
        else:
            self.stdout.write('🔄 Force mode: Re-extracting all specs')
        
        if limit:
            articles_qs = articles_qs[:limit]
        
        total = articles_qs.count()
        self.stdout.write(f'📊 Found {total} articles to process')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️  No articles to process'))
            return
        
        # Process articles
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, article in enumerate(articles_qs, 1):
            self.stdout.write(f'\n[{i}/{total}] Processing: {article.title[:60]}...')
            
            try:
                # Extract specs using AI
                specs_data = extract_vehicle_specs(
                    title=article.title,
                    content=article.content,
                    summary=article.summary or ""
                )
                
                # Check if we got meaningful data
                if not specs_data or specs_data.get('confidence_score', 0) < 0.3:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  Low confidence or no data extracted'))
                    skipped_count += 1
                    continue
                
                # Create or update VehicleSpecs
                vehicle_specs, created = VehicleSpecs.objects.update_or_create(
                    article=article,
                    defaults=specs_data
                )
                
                action = "Created" if created else "Updated"
                confidence = specs_data.get('confidence_score', 0)
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ {action} specs (confidence: {confidence:.2f})'
                ))
                
                # Show some extracted data
                if specs_data.get('power_hp'):
                    self.stdout.write(f'      Power: {specs_data["power_hp"]} HP')
                if specs_data.get('range_km'):
                    self.stdout.write(f'      Range: {specs_data["range_km"]} km')
                if specs_data.get('price_from'):
                    self.stdout.write(f'      Price: ${specs_data["price_from"]:,.0f}+')
                
                success_count += 1
                
                # Delay to avoid rate limits
                if delay > 0 and i < total:
                    time.sleep(delay)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {e}'))
                error_count += 1
                continue
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ Extraction complete!'))
        self.stdout.write(f'   - Successful: {success_count}')
        self.stdout.write(f'   - Skipped (low confidence): {skipped_count}')
        self.stdout.write(f'   - Errors: {error_count}')
        self.stdout.write(f'   - Total processed: {total}')
