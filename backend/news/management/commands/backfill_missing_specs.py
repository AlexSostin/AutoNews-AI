"""
Backfill CarSpecification for articles that don't have one,
or refresh ALL existing specs with AI re-analysis.
Uses AI (Gemini) to extract specs from article content.
Also optionally deletes duplicate articles.
"""
import re
from django.core.management.base import BaseCommand
from news.models import Article, CarSpecification
from ai_engine.modules.ai_provider import get_ai_provider


# Articles that are news/non-car content - skip them
SKIP_ARTICLE_IDS = [73, 76]  # Wireless charging roads, Hongqi records


class Command(BaseCommand):
    help = 'Create/update CarSpecification for articles using AI extraction'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
        parser.add_argument('--refresh-all', action='store_true',
                          help='Re-analyze ALL articles, updating existing specs')
        parser.add_argument('--delete-dupes', nargs='+', type=int, help='Article IDs to delete')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        refresh_all = options['refresh_all']

        # Step 1: Delete duplicate articles if specified
        delete_ids = options.get('delete_dupes') or []
        if delete_ids:
            for aid in delete_ids:
                try:
                    article = Article.objects.get(id=aid)
                    self.stdout.write(f'🗑️  Deleting [{aid}] "{article.title[:60]}"')
                    if not dry_run:
                        article.delete()
                except Article.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'  Article {aid} not found'))

        # Step 2: Find target articles
        if refresh_all:
            # All published articles except news
            articles = (
                Article.objects
                .filter(is_published=True)
                .exclude(id__in=SKIP_ARTICLE_IDS)
                .order_by('id')
            )
            self.stdout.write(f'\n🔄 REFRESH ALL mode: processing {articles.count()} articles')
        else:
            # Only articles without CarSpecification
            articles_with_specs = set(
                CarSpecification.objects.values_list('article_id', flat=True)
            )
            articles = (
                Article.objects
                .filter(is_published=True)
                .exclude(id__in=articles_with_specs)
                .exclude(id__in=SKIP_ARTICLE_IDS)
                .order_by('id')
            )
            self.stdout.write(f'\n📊 Found {articles.count()} articles without CarSpecification')

        total = articles.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nothing to process!'))
            return

        ai = get_ai_provider('gemini')
        created = 0
        updated = 0

        for article in articles:
            self.stdout.write(f'\n🔍 [{article.id}] "{article.title[:60]}"')

            # Extract specs from article content using AI
            specs = self._extract_specs_from_content(ai, article)
            if not specs:
                self.stdout.write(self.style.WARNING('  ⚠️ Could not extract specs'))
                continue

            make = specs.get('make', '')
            model = specs.get('model', '')
            if not make or make == 'Not specified':
                self.stdout.write(self.style.WARNING(f'  ⚠️ No make extracted, skipping'))
                continue

            self.stdout.write(
                f'  → {make} {model} | engine={specs.get("engine","?")} | '
                f'hp={specs.get("horsepower","?")} | drivetrain={specs.get("drivetrain","?")} | '
                f'price={specs.get("price","?")}'
            )

            spec_data = {
                'model_name': f'{make} {model}'.strip(),
                'make': make,
                'model': model,
                'trim': specs.get('trim', '') if specs.get('trim') != 'Not specified' else '',
                'engine': specs.get('engine', '') if specs.get('engine') != 'Not specified' else '',
                'horsepower': specs.get('horsepower'),
                'torque': specs.get('torque', '') if specs.get('torque') != 'Not specified' else '',
                'zero_to_sixty': specs.get('acceleration', '') if specs.get('acceleration') != 'Not specified' else '',
                'top_speed': specs.get('top_speed', '') if specs.get('top_speed') != 'Not specified' else '',
                'drivetrain': specs.get('drivetrain', '') if specs.get('drivetrain') != 'Not specified' else '',
                'price': specs.get('price', '') if specs.get('price') != 'Not specified' else '',
            }

            if not dry_run:
                existing = CarSpecification.objects.filter(article=article).first()
                if existing:
                    # Update existing - only overwrite if AI found better data
                    changes = []
                    for field, value in spec_data.items():
                        if field == 'horsepower':
                            if value and (not existing.horsepower or existing.horsepower == 0):
                                setattr(existing, field, value)
                                changes.append(field)
                        elif value and value.strip():
                            old = getattr(existing, field, '') or ''
                            if not old.strip() or (refresh_all and value != old):
                                setattr(existing, field, value)
                                changes.append(field)
                    if changes:
                        existing.save()
                        self.stdout.write(f'  ✅ Updated fields: {", ".join(changes)}')
                        updated += 1
                    else:
                        self.stdout.write(f'  ℹ️ No changes needed')
                else:
                    CarSpecification.objects.create(article=article, **spec_data, release_date='')
                    self.stdout.write(f'  ✅ Created new spec')
                    created += 1
            else:
                existing = CarSpecification.objects.filter(article=article).exists()
                if existing:
                    self.stdout.write(f'  [DRY] Would update')
                    updated += 1
                else:
                    self.stdout.write(f'  [DRY] Would create')
                    created += 1

        action_verb = 'Would' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {action_verb} Created {created}, Updated {updated} CarSpecification records'
        ))

    def _extract_specs_from_content(self, ai, article):
        """Use AI to extract car specs from article content."""
        # Strip HTML tags for cleaner text
        content = re.sub(r'<[^>]+>', ' ', article.content or '')
        content = re.sub(r'\s+', ' ', content).strip()

        # Limit content length
        content = content[:4000]

        prompt = f"""Extract car specifications from this article.
Title: {article.title}

Content:
{content}

Output ONLY these fields with EXACT labels:
Make: [Brand name, e.g. "NIO", "BYD", "Xpeng", "Toyota"]
Model: [Model name without brand, e.g. "ET9", "Leopard 5", "Highlander"]
Trim/Version: [Trim if mentioned, else "Not specified"]
Engine: [Engine type, e.g. "Electric Dual Motor", "1.5L Turbo PHEV", "2.0L Inline-4"]
Horsepower: [Number with unit, e.g. "300 hp" or "220 kW"]
Torque: [With unit, e.g. "400 Nm"]
Acceleration: [0-60 mph or 0-100 km/h time, e.g. "5.5 seconds (0-60 mph)"]
Top Speed: [With unit, e.g. "155 mph" or "250 km/h"]
Drivetrain: [AWD/FWD/RWD/4WD or "Not specified"]
Price: [With currency symbol, e.g. "$45,000" or "¥169,800"]

IMPORTANT:
1. Only include specs EXPLICITLY mentioned in the content. 
2. Write "Not specified" if a spec is not found in the text.
3. NEVER guess, estimate, or use qualifiers like "(estimated)".
4. If the article is clearly NOT about a specific car model, output Make: Not specified
"""

        system_prompt = (
            "You are an automotive data extractor. Extract only facts explicitly "
            "stated in the text. Never guess. Use 'Not specified' for unknown fields."
        )

        try:
            result = ai.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=500,
            )
            return self._parse_specs(result)
        except Exception as e:
            self.stderr.write(f'  AI error: {e}')
            return None

    def _parse_specs(self, text):
        """Parse AI output into specs dict."""
        specs = {}
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('Make:'):
                specs['make'] = line.split(':', 1)[1].strip()
            elif line.startswith('Model:'):
                specs['model'] = line.split(':', 1)[1].strip()
            elif line.startswith('Trim/Version:'):
                specs['trim'] = line.split(':', 1)[1].strip()
            elif line.startswith('Engine:'):
                specs['engine'] = line.split(':', 1)[1].strip()
            elif line.startswith('Horsepower:'):
                hp_str = line.split(':', 1)[1].strip()
                match = re.search(r'(\d+)', hp_str)
                specs['horsepower'] = int(match.group(1)) if match else None
            elif line.startswith('Torque:'):
                specs['torque'] = line.split(':', 1)[1].strip()
            elif line.startswith('Acceleration:'):
                specs['acceleration'] = line.split(':', 1)[1].strip()
            elif line.startswith('Top Speed:'):
                specs['top_speed'] = line.split(':', 1)[1].strip()
            elif line.startswith('Drivetrain:') or line.startswith('Drive:'):
                specs['drivetrain'] = line.split(':', 1)[1].strip()
            elif line.startswith('Price:'):
                specs['price'] = line.split(':', 1)[1].strip()
        return specs
