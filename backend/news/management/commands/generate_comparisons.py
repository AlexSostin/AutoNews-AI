"""
Generate comparison articles from VehicleSpecs data.

Usage:
    python manage.py generate_comparisons                 # Top 5 pairs (dry-run preview)
    python manage.py generate_comparisons --execute       # Actually generate articles
    python manage.py generate_comparisons --limit 10      # Generate 10 pairs
    python manage.py generate_comparisons --segment SUV   # Only SUV comparisons
    python manage.py generate_comparisons --provider groq # Use Groq (free tier)
    python manage.py generate_comparisons --brands BYD,Tesla  # Only these brands
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Auto-generate comparison articles from VehicleSpecs data'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true',
                            help='Actually generate articles (default is dry-run preview)')
        parser.add_argument('--limit', type=int, default=5,
                            help='Max number of comparisons to generate (default: 5)')
        parser.add_argument('--segment', type=str, default=None,
                            help='Filter by body type: SUV, sedan, hatchback, etc.')
        parser.add_argument('--fuel', type=str, default=None,
                            help='Filter by fuel type: EV, PHEV, Hybrid, Gas')
        parser.add_argument('--provider', type=str, default='gemini',
                            help='AI provider: gemini or groq (default: gemini)')
        parser.add_argument('--brands', type=str, default=None,
                            help='Comma-separated brand filter, e.g. BYD,Tesla,ZEEKR')
        parser.add_argument('--auto', action='store_true',
                            help='Automated mode: check AutomationSettings, respect weekly limits, enforce diversity')

    def handle(self, *args, **options):
        from news.models import VehicleSpecs, Article, CarSpecification, Category, Tag
        from itertools import combinations

        execute = options['execute']
        limit = options['limit']
        segment = options['segment']
        fuel = options['fuel']
        provider = options['provider']
        brands_filter = options['brands']
        auto_mode = options['auto']

        if provider not in ('gemini', 'groq'):
            provider = 'gemini'

        # === Auto mode: check settings ===
        if auto_mode:
            from news.models.system import AutomationSettings
            from django.utils import timezone
            from datetime import timedelta

            settings = AutomationSettings.load()

            if not settings.comparison_enabled:
                self.stdout.write(self.style.WARNING('⏸️ Comparison automation is disabled.'))
                return

            # Weekly reset
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())  # Monday
            if settings.comparison_week_start != week_start:
                settings.comparison_this_week_count = 0
                settings.comparison_week_start = week_start
                settings.save(update_fields=['comparison_this_week_count', 'comparison_week_start'])

            remaining = settings.comparison_max_per_week - settings.comparison_this_week_count
            if remaining <= 0:
                self.stdout.write(self.style.WARNING(
                    f'⏸️ Weekly limit reached ({settings.comparison_this_week_count}/{settings.comparison_max_per_week})'
                ))
                return

            # Acquire lock
            if not AutomationSettings.acquire_lock('comparison'):
                self.stdout.write(self.style.WARNING('🔒 Another comparison task is running.'))
                return

            # Override settings from automation config
            execute = True
            limit = min(limit, remaining)
            provider = settings.comparison_provider or 'gemini'

            self.stdout.write(f'🤖 AUTO MODE: {remaining} comparisons remaining this week')

        self.stdout.write(f"\n{'🚀 EXECUTE MODE' if execute else '👀 DRY-RUN PREVIEW'}")
        self.stdout.write(f"Provider: {provider}, Limit: {limit}\n")

        # ── Step 1: Find pairable vehicles ──
        qs = VehicleSpecs.objects.exclude(make='').exclude(model_name='').filter(
            body_type__isnull=False,
            fuel_type__isnull=False,
        )

        if segment:
            qs = qs.filter(body_type__iexact=segment)
            self.stdout.write(f"Segment filter: {segment}")

        if fuel:
            qs = qs.filter(fuel_type__iexact=fuel)
            self.stdout.write(f"Fuel filter: {fuel}")

        if brands_filter:
            brand_list = [b.strip() for b in brands_filter.split(',')]
            qs = qs.filter(make__in=brand_list)
            self.stdout.write(f"Brand filter: {brand_list}")

        all_specs = list(qs)
        self.stdout.write(f"\nFound {len(all_specs)} vehicles with complete segment data\n")

        if len(all_specs) < 2:
            self.stdout.write(self.style.ERROR("Need at least 2 vehicles to compare"))
            return

        # ── Step 2: Group by segment ──
        segments = {}
        for spec in all_specs:
            key = (spec.body_type, spec.fuel_type)
            segments.setdefault(key, []).append(spec)

        self.stdout.write("Segments:")
        for (bt, ft), specs in sorted(segments.items(), key=lambda x: -len(x[1])):
            self.stdout.write(f"  {ft} {bt}: {len(specs)} vehicles")

        # ── Step 3: Generate pairs ──
        pairs = []
        for (bt, ft), specs in segments.items():
            if len(specs) < 2:
                continue

            for a, b in combinations(specs, 2):
                # Rule: different brands only
                if a.make.lower() == b.make.lower():
                    continue

                # Score pair by data completeness
                score = 0
                for spec in (a, b):
                    if spec.power_hp:
                        score += 2
                    if spec.price_from:
                        score += 3
                    if spec.range_km or spec.range_wltp:
                        score += 2
                    if spec.battery_kwh:
                        score += 1
                    if spec.acceleration_0_100:
                        score += 2
                    if spec.length_mm:
                        score += 1

                # Price proximity bonus (±40% range)
                if a.price_from and b.price_from:
                    ratio = min(a.price_from, b.price_from) / max(a.price_from, b.price_from)
                    if ratio >= 0.6:
                        score += 5  # Similar price = better comparison

                pairs.append((score, a, b))

        # Sort by score (best pairs first)
        pairs.sort(key=lambda x: -x[0])

        # ── Step 4: Filter out existing comparisons ──
        filtered_pairs = []
        for score, a, b in pairs:
            slug_a = slugify(f"{a.make}-{a.model_name}-vs-{b.make}-{b.model_name}-comparison")[:200]
            slug_b = slugify(f"{b.make}-{b.model_name}-vs-{a.make}-{a.model_name}-comparison")[:200]

            exists = Article.objects.filter(
                slug__in=[slug_a, slug_b],
                is_deleted=False,
            ).exists()

            if not exists:
                filtered_pairs.append((score, a, b))

        self.stdout.write(f"\n{len(filtered_pairs)} pairs available (after excluding existing articles)")
        if not filtered_pairs:
            self.stdout.write(self.style.WARNING("No new pairs to generate!"))
            if auto_mode:
                AutomationSettings.release_lock('comparison')
            return

        # ── Step 5b: Diversity — skip vehicles already used this week ──
        if auto_mode:
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())

            recent_comparisons = Article.objects.filter(
                categories__name='Comparisons',
                created_at__date__gte=week_start,
                is_deleted=False,
            )
            used_vehicles = set()
            for art in recent_comparisons:
                meta = art.generation_metadata or {}
                if meta.get('spec_a'):
                    used_vehicles.add(meta['spec_a'])
                if meta.get('spec_b'):
                    used_vehicles.add(meta['spec_b'])

            diverse_pairs = []
            used_in_batch = set()
            for score, a, b in filtered_pairs:
                name_a = f"{a.make} {a.model_name}"
                name_b = f"{b.make} {b.model_name}"
                if name_a in used_vehicles or name_b in used_vehicles:
                    continue  # Already compared this week
                if name_a in used_in_batch or name_b in used_in_batch:
                    continue  # Already in this batch
                diverse_pairs.append((score, a, b))
                used_in_batch.add(name_a)
                used_in_batch.add(name_b)

            self.stdout.write(f"{len(diverse_pairs)} diverse pairs (after weekly diversity filter)")
            filtered_pairs = diverse_pairs

        # ── Step 5: Preview or generate ──
        to_generate = filtered_pairs[:limit]

        self.stdout.write(f"\n{'Generating' if execute else 'Would generate'} {len(to_generate)} comparisons:\n")

        for i, (score, a, b) in enumerate(to_generate, 1):
            name_a = f"{a.make} {a.model_name}"
            name_b = f"{b.make} {b.model_name}"
            price_a = a.get_price_display()
            price_b = b.get_price_display()
            segment_label = f"{a.fuel_type} {a.get_body_type_display()}"

            self.stdout.write(
                f"  {i}. {name_a} vs {name_b} "
                f"[{segment_label}] "
                f"(score: {score}, price: {price_a} / {price_b})"
            )

        if not execute:
            self.stdout.write(self.style.WARNING(
                f"\n👀 DRY-RUN: Add --execute to actually generate these articles\n"
            ))
            return

        # ── Step 6: Generate articles ──
        from ai_engine.modules.comparison_generator import generate_comparison

        created = 0
        errors = 0

        # Get or create "Comparisons" category
        comparisons_cat, _ = Category.objects.get_or_create(
            name='Comparisons',
            defaults={'slug': 'comparisons'},
        )

        for i, (score, spec_a, spec_b) in enumerate(to_generate, 1):
            name_a = f"{spec_a.make} {spec_a.model_name}"
            name_b = f"{spec_b.make} {spec_b.model_name}"

            try:
                self.stdout.write(f"\n  [{i}/{len(to_generate)}] Generating {name_a} vs {name_b}...")

                result = generate_comparison(spec_a, spec_b, provider=provider)

                # Ensure unique slug
                slug = result['slug']
                base_slug = slug
                counter = 1
                while Article.objects.filter(slug=slug, is_deleted=False).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create draft article
                article = Article.objects.create(
                    title=result['title'],
                    slug=slug,
                    content=result['content'],
                    content_original=result['content'],
                    summary=result['summary'],
                    seo_description=result['seo_description'][:160],
                    is_published=False,  # Always draft
                    is_news_only=False,
                    generation_metadata={
                        'source': 'comparison_generator',
                        'provider': provider,
                        'spec_a': f"{spec_a.make} {spec_a.model_name}",
                        'spec_b': f"{spec_b.make} {spec_b.model_name}",
                        'word_count': result['word_count'],
                        'pair_score': score,
                    },
                )

                # Assign category
                article.categories.add(comparisons_cat)

                # Auto-assign brand tags
                for spec in (spec_a, spec_b):
                    brand_tag = Tag.objects.filter(name__iexact=spec.make).first()
                    if brand_tag:
                        article.tags.add(brand_tag)

                # Segment tag (e.g., "SUV", "EV")
                for tag_name in [spec_a.body_type, spec_a.fuel_type]:
                    if tag_name:
                        seg_tag = Tag.objects.filter(name__iexact=tag_name).first()
                        if seg_tag:
                            article.tags.add(seg_tag)

                # Create CarSpecification for primary vehicle
                CarSpecification.objects.update_or_create(
                    article=article,
                    defaults={
                        'make': spec_a.make,
                        'model': spec_a.model_name,
                        'trim': spec_a.trim_name or '',
                    },
                )

                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ Created draft: \"{result['title']}\" "
                    f"({result['word_count']} words, slug: {slug})"
                ))

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))
                logger.error(f"Comparison generation failed for {name_a} vs {name_b}: {e}", exc_info=True)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Done! Created: {created}, Errors: {errors}")
        self.stdout.write(f"Articles saved as DRAFTS — review in admin before publishing.\n")

        # === Auto mode: update settings ===
        if auto_mode:
            from news.models.system import AutomationSettings
            from django.utils import timezone
            settings = AutomationSettings.load()
            settings.comparison_this_week_count += created
            settings.comparison_last_run = timezone.now()
            settings.comparison_last_status = f'Generated {created} articles, {errors} errors'
            settings.save(update_fields=[
                'comparison_this_week_count', 'comparison_last_run', 'comparison_last_status'
            ])
            AutomationSettings.release_lock('comparison')
