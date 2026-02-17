"""
Bulk re-enrich all published articles missing enrichments.
Usage: python manage.py bulk_enrich [--mode missing|all] [--ids 1,2,3] [--dry-run]
"""
import time
from django.core.management.base import BaseCommand
from news.models import Article, Tag, VehicleSpecs, ArticleTitleVariant, CarSpecification


class Command(BaseCommand):
    help = 'Bulk re-enrich published articles (Deep Specs, A/B Titles, Smart Auto-Tags)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode', choices=['missing', 'all'], default='missing',
            help='missing = only articles without VehicleSpecs or A/B titles, all = every published article'
        )
        parser.add_argument(
            '--ids', type=str, default='',
            help='Comma-separated article IDs to enrich (overrides --mode)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Just list which articles would be enriched, without running AI'
        )
        parser.add_argument(
            '--tags-only', action='store_true',
            help='Only run smart auto-tagging (skip Deep Specs and A/B titles)'
        )
        parser.add_argument(
            '--no-ai-tags', action='store_true',
            help='Skip AI tag extraction (Layer 2) — only use structured data and keyword matching'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        ids_str = options['ids']
        dry_run = options['dry_run']
        tags_only = options['tags_only']
        no_ai_tags = options['no_ai_tags']

        published = Article.objects.filter(is_published=True, is_deleted=False)

        if ids_str:
            ids = [int(x.strip()) for x in ids_str.split(',') if x.strip()]
            articles = published.filter(id__in=ids)
            self.stdout.write(f'🎯 Mode: selected IDs ({len(ids)})')
        elif mode == 'missing':
            specs_ids = set(VehicleSpecs.objects.values_list('article_id', flat=True))
            ab_ids = set(ArticleTitleVariant.objects.values_list('article_id', flat=True))
            fully_enriched = specs_ids & ab_ids
            articles = published.exclude(id__in=fully_enriched)
            self.stdout.write(f'🔍 Mode: missing (articles without VehicleSpecs AND A/B titles)')
        else:
            articles = published
            self.stdout.write(f'🌐 Mode: all published articles')

        if tags_only:
            self.stdout.write(f'🏷️  Tags-only mode: skipping Deep Specs and A/B titles')

        total = articles.count()
        self.stdout.write(f'📊 Found {total} articles to process\n')

        if dry_run:
            for a in articles.order_by('id'):
                has_specs = VehicleSpecs.objects.filter(article=a).exists()
                has_ab = ArticleTitleVariant.objects.filter(article=a).exists()
                tag_count = a.tags.count()
                self.stdout.write(
                    f'  #{a.id:>3d} | Specs:{"✅" if has_specs else "❌"} | A/B:{"✅" if has_ab else "❌"} | Tags:{tag_count:>2d} | {a.title[:60]}'
                )
            self.stdout.write(f'\n  --dry-run mode, no changes made.')
            return

        from news.auto_tags import auto_tag_article

        success = 0
        errors = 0
        total_tags_created = 0
        total_tags_matched = 0
        start = time.time()

        for i, article in enumerate(articles.order_by('id'), 1):
            self.stdout.write(f'\n[{i}/{total}] Processing: {article.title[:60]}...')

            if not tags_only:
                specs_dict = None
                web_context = ''

                # Step 1: Web search
                try:
                    car_spec = CarSpecification.objects.filter(article=article).first()
                    if car_spec and car_spec.make:
                        specs_dict = {
                            'make': car_spec.make, 'model': car_spec.model or '',
                            'trim': car_spec.trim or '',
                        }
                    else:
                        import re
                        m = re.match(r'(\d{4})\s+(.+?)(?:\s+(?:Review|First|Walk|Test|Preview|Deep|Comp))', article.title, re.I)
                        if m:
                            parts = m.group(2).strip().split(' ', 1)
                            if len(parts) >= 2:
                                specs_dict = {'make': parts[0], 'model': parts[1], 'year': int(m.group(1))}

                    if specs_dict and specs_dict.get('make'):
                        try:
                            from ai_engine.modules.searcher import get_web_context
                            web_context = get_web_context(specs_dict)
                            self.stdout.write(f'   🔍 Web context: {len(web_context)} chars')
                        except Exception:
                            pass
                except Exception:
                    pass

                # Step 2: Deep specs
                has_specs = VehicleSpecs.objects.filter(article=article).exists()
                if not has_specs and specs_dict and specs_dict.get('make'):
                    try:
                        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                        vs = generate_deep_vehicle_specs(article, specs=specs_dict, web_context=web_context, provider='gemini')
                        self.stdout.write(self.style.SUCCESS(f'   🚗 Deep specs: {vs.make} {vs.model_name}' if vs else '   ⚠️ Deep specs: empty'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ Deep specs: {e}'))
                        errors += 1
                        continue
                elif has_specs:
                    self.stdout.write(f'   ⏭️  Deep specs: already exists')

                # Step 3: A/B titles
                has_ab = ArticleTitleVariant.objects.filter(article=article).exists()
                if not has_ab:
                    try:
                        from ai_engine.main import generate_title_variants
                        generate_title_variants(article, provider='gemini')
                        count = ArticleTitleVariant.objects.filter(article=article).count()
                        self.stdout.write(self.style.SUCCESS(f'   📝 A/B titles: {count} variants created'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   ❌ A/B titles: {e}'))
                else:
                    self.stdout.write(f'   ⏭️  A/B titles: already exists')

            # Step 4: Smart Auto-Tags (always runs)
            try:
                tag_result = auto_tag_article(article, use_ai=not no_ai_tags)
                created = tag_result['created']
                matched = tag_result['matched']
                total_tags_created += len(created)
                total_tags_matched += len(matched)

                if created:
                    self.stdout.write(self.style.SUCCESS(f'   🏷️  Tags: +{len(created)} NEW ({", ".join(created[:5])})'))
                if matched:
                    self.stdout.write(f'   🏷️  Tags: +{len(matched)} existing ({", ".join(matched[:5])})')
                if not created and not matched:
                    self.stdout.write(f'   🏷️  Tags: no new matches')
                if tag_result['ai_used']:
                    self.stdout.write(f'   🤖 AI extraction was used')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Tags: {e}'))

            success += 1

        elapsed = round(time.time() - start, 1)
        self.stdout.write(f'\n{"="*50}')
        self.stdout.write(self.style.SUCCESS(f'✅ Done! {success}/{total} articles enriched in {elapsed}s'))
        self.stdout.write(f'   🏷️  Tags created: {total_tags_created}')
        self.stdout.write(f'   🏷️  Tags matched: {total_tags_matched}')
        if errors:
            self.stdout.write(self.style.ERROR(f'   ❌ {errors} articles had errors'))
