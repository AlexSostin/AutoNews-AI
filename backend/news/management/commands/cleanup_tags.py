"""
Management command to clean up tags:
- Rename model tags to include brand prefix (SEO fix)
- Merge duplicate/redundant tags
- Delete useless trim tags
- Fix group assignments
- Remove dead tags (0 articles, no group)
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db.models import Count
from news.models import Tag, TagGroup


# ============================================================
# Phase 1: RENAMES — Add brand prefix to model tags
# Format: old_slug → new_name (slug auto-generated)
# ============================================================
RENAMES = {
    '001': 'Zeekr 001',
    '6': 'Smart #6',
    '7x': 'Zeekr 7X',
    '9x': 'Zeekr 9X',
    'd9': 'Denza D9',
    'et9': 'NIO ET9',
    'g6': 'XPeng G6',
    'g7': 'XPeng G7',
    'g9': 'XPeng G9',
    'galaxy-m9': 'Geely Galaxy M9',
    'han': 'BYD Han',
    'hs6': 'Hongqi HS6',
    'highlander': 'Toyota Highlander',
    'ls9': 'IM LS9',
    'n8l': 'Denza N8L',
    'n9': 'Denza N9',
    'onvo-l60': 'NIO ONVO L60',
    'onvo-l90': 'NIO ONVO L90',
    'p7': 'XPeng P7',
    'qin-l': 'BYD Qin L',
    'seal-05': 'BYD Seal 05',
    'seal-06': 'BYD Seal 06',
    'sealion-05': 'BYD Sealion 05',
    'sealion-06': 'BYD Sealion 06',
    'seagull': 'BYD Seagull',
    'su7': 'Xiaomi SU7',
    'tang': 'BYD Tang',
    'tank-700': 'GWM Tank 700',
    'taishan': 'VOYAH Taishan',
    'wendao-v9': 'ArcFox Wendao V9',
    'x9': 'XPeng X9',
    'yu7': 'Xiaomi YU7',
    'yuan-up': 'BYD Yuan Up',
    'z9': 'Denza Z9',
    'fcb': 'BYD FCB',
    'fcb-titanium-7': 'BYD FCB Titanium 7',
    'dreamer': 'VOYAH Dreamer',
    'zhiyin': 'VOYAH Zhiyin',
    'leopard-5': 'BYD Leopard 5',
    'leopard-7': 'BYD Leopard 7',
    'leopard-8': 'BYD Leopard 8',
    'avatr-07': 'Avatr 07',
    'avatr-12': 'Avatr 12',
    'onvo': 'NIO ONVO',
    'song': 'BYD Song',
}

# ============================================================
# Phase 2: MERGES — Move articles from source → target, delete source
# Format: source_slug → target_slug
# ============================================================
MERGE_MAP = {
    'electric': 'ev',                   # Electric → EV
    'bev': 'ev',                        # BEV → EV
    'plug-in-hybrid': 'phev',           # Plug-in Hybrid → PHEV
    'rev': 'e-rev',                     # REV → E-REV
    'range-extended': 'e-rev',          # Range-extended → E-REV
    'mercedes-benz': 'mercedes',        # Mercedes-Benz → Mercedes
    'formula-1': 'f1',                  # Formula 1 → F1
    'battery-technology': 'battery',    # Battery Technology → Battery
}

# ============================================================
# Phase 3: Special merges — tags that need combining
# ZEEKR 007 GT: merge "007" into a new tag, handle "GT" article reassignment
# BYD Song Pro: merge "Song" + "Pro" → BYD Song Pro
# ============================================================
SPECIAL_MERGES = [
    # (old_slugs_to_absorb, new_name, new_group_slug)
    # 007 + GT → ZEEKR 007 GT (for article 86 specifically)
    {
        'match_article_tags': ['007', 'GT'],  # article must have BOTH
        'old_slugs': ['007'],
        'new_name': 'ZEEKR 007 GT',
        'remove_from_matched': ['GT'],  # remove GT tag from matched articles
    },
    {
        'match_article_tags': ['Song', 'Pro'],
        'old_slugs': ['song'],  # will already be renamed to BYD Song
        'new_name': 'BYD Song Pro',
        'remove_from_matched': ['Pro'],
    },
]

# ============================================================
# Phase 4: DELETE — Useless tags
# ============================================================
DELETE_TAGS = [
    'gt',       # Generic trim, articles reassigned above
    'max',      # Generic trim
    'plus',     # Generic trim (0 articles)
    'pro',      # Generic trim, articles reassigned above
    'green',    # Vague (0 articles)
    'factory',  # Vague (0 articles)
    'endurance', # Vague (0 articles)
    'towing',   # Vague (0 articles)
]

# ============================================================
# Phase 5: GROUP REASSIGNMENTS
# Format: tag_slug → group_slug
# ============================================================
GROUP_FIXES = {
    # Motorsports tags wrongly in Segments
    'f1': 'events-motorsports',
    'formula-e': 'events-motorsports',
    'motogp': 'events-motorsports',
    'wrc': 'events-motorsports',
    'rally': 'events-motorsports',
    'drift': 'events-motorsports',

    # Range wrongly in Events
    'range': 'tech-features',

    # Fuel Economy wrongly in Segments
    'fuel-economy': 'tech-features',

    # Uncategorized tags
    'chip-shortage': 'tech-features',
    'e-rev': 'fuel-types',
}


class Command(BaseCommand):
    help = 'Comprehensive tag cleanup: rename, merge, delete, regroup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--remove-dead',
            action='store_true',
            help='Remove tags with 0 articles (keeps grouped tags)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        remove_dead = options['remove_dead']

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE - No changes will be made]\n'))

        self._phase1_renames(dry_run)
        self._phase2_merges(dry_run)
        self._phase3_special_merges(dry_run)
        self._phase4_deletes(dry_run)
        self._phase5_group_fixes(dry_run)

        if remove_dead:
            self._phase6_remove_dead(dry_run)

        self._print_summary()

    def _phase1_renames(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 1: Renaming Model Tags (Add Brand Prefix) ===\n'))
        count = 0

        for old_slug, new_name in RENAMES.items():
            try:
                tag = Tag.objects.get(slug=old_slug)
            except Tag.DoesNotExist:
                continue

            new_slug = slugify(new_name)

            # Check if target slug already exists
            if Tag.objects.filter(slug=new_slug).exclude(id=tag.id).exists():
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Slug "{new_slug}" already exists, skipping rename of "{tag.name}"'
                ))
                continue

            self.stdout.write(f'  ✏️  "{tag.name}" → "{new_name}" (slug: {old_slug} → {new_slug})')

            if not dry_run:
                tag.name = new_name
                tag.slug = new_slug
                tag.save(update_fields=['name', 'slug'])
                self.stdout.write(self.style.SUCCESS(f'    ✓ Renamed'))

            count += 1

        self.stdout.write(f'\n  Total renames: {count}\n')

    def _phase2_merges(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 2: Merging Duplicate Tags ===\n'))
        count = 0

        for source_slug, target_slug in MERGE_MAP.items():
            if source_slug == target_slug:
                continue

            try:
                source = Tag.objects.get(slug=source_slug)
            except Tag.DoesNotExist:
                continue

            try:
                target = Tag.objects.get(slug=target_slug)
            except Tag.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Target "{target_slug}" not found, skipping merge of "{source.name}"'
                ))
                continue

            source_count = source.article_set.count()
            target_count = target.article_set.count()

            self.stdout.write(
                f'  📎 "{source.name}" ({source_count} articles) → "{target.name}" ({target_count} articles)'
            )

            if not dry_run:
                for article in source.article_set.all():
                    article.tags.add(target)
                    article.tags.remove(source)
                source.delete()
                self.stdout.write(self.style.SUCCESS(f'    ✓ Merged & deleted'))

            count += 1

        self.stdout.write(f'\n  Total merges: {count}\n')

    def _phase3_special_merges(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 3: Special Merges (Multi-tag Combinations) ===\n'))

        for spec in SPECIAL_MERGES:
            match_names = spec['match_article_tags']
            new_name = spec['new_name']
            remove_names = spec.get('remove_from_matched', [])

            # Find or create the new tag
            new_slug = slugify(new_name)
            models_group = TagGroup.objects.filter(slug='models').first()

            new_tag, created = Tag.objects.get_or_create(
                slug=new_slug,
                defaults={
                    'name': new_name,
                    'group': models_group,
                }
            )

            if created and not dry_run:
                self.stdout.write(self.style.SUCCESS(f'  ✨ Created new tag: "{new_name}"'))
            elif created and dry_run:
                self.stdout.write(f'  ✨ Would create: "{new_name}"')
                new_tag.delete()  # Don't leave behind in dry run
                continue

            # Find articles that have ALL the match tags
            match_tags = list(Tag.objects.filter(name__in=match_names))
            if len(match_tags) != len(match_names):
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Not all match tags found for "{new_name}", skipping'
                ))
                continue

            # Get articles that have all match tags
            from django.db.models import Q
            from functools import reduce
            from news.models import Article

            articles = Article.objects.all()
            for tag in match_tags:
                articles = articles.filter(tags=tag)

            article_count = articles.count()
            self.stdout.write(f'  🔗 {match_names} → "{new_name}" (affects {article_count} articles)')

            if not dry_run and article_count > 0:
                for article in articles:
                    article.tags.add(new_tag)
                    # Remove the tags that should be removed
                    for remove_name in remove_names:
                        remove_tag = Tag.objects.filter(name=remove_name).first()
                        if remove_tag:
                            article.tags.remove(remove_tag)
                self.stdout.write(self.style.SUCCESS(f'    ✓ Reassigned {article_count} articles'))

            # Rename old slugs to point to new tag (handled by renames already for 'song')
            for old_slug in spec['old_slugs']:
                old_tag = Tag.objects.filter(slug=old_slug).first()
                if not old_tag:
                    # Try renamed slug
                    old_tag = Tag.objects.filter(slug=slugify(old_slug)).first()
                if old_tag and old_tag.id != new_tag.id:
                    remaining = old_tag.article_set.count()
                    if remaining == 0:
                        if not dry_run:
                            old_tag.delete()
                            self.stdout.write(self.style.SUCCESS(f'    ✓ Deleted empty old tag "{old_tag.name}"'))
                    else:
                        self.stdout.write(f'    ℹ Old tag "{old_tag.name}" still has {remaining} articles, keeping')

    def _phase4_deletes(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 4: Deleting Useless Tags ===\n'))
        count = 0

        for slug in DELETE_TAGS:
            try:
                tag = Tag.objects.get(slug=slug)
            except Tag.DoesNotExist:
                continue

            article_count = tag.article_set.count()
            self.stdout.write(f'  🗑️  "{tag.name}" ({article_count} articles)')

            if article_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'    ⚠ Has {article_count} articles — removing tag from articles first'
                ))
                if not dry_run:
                    tag.article_set.clear()

            if not dry_run:
                tag.delete()
                self.stdout.write(self.style.SUCCESS(f'    ✓ Deleted'))

            count += 1

        self.stdout.write(f'\n  Total deletes: {count}\n')

    def _phase5_group_fixes(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 5: Fixing Group Assignments ===\n'))
        count = 0

        group_cache = {g.slug: g for g in TagGroup.objects.all()}

        for tag_slug, group_slug in GROUP_FIXES.items():
            try:
                tag = Tag.objects.get(slug=tag_slug)
            except Tag.DoesNotExist:
                # Try with renamed slug
                try:
                    tag = Tag.objects.get(slug=slugify(tag_slug))
                except Tag.DoesNotExist:
                    continue

            group = group_cache.get(group_slug)
            if not group:
                self.stdout.write(self.style.WARNING(f'  ⚠ Group "{group_slug}" not found'))
                continue

            old_group = tag.group.name if tag.group else 'None'
            if tag.group == group:
                continue  # Already correct

            self.stdout.write(f'  🔄 "{tag.name}": {old_group} → {group.name}')

            if not dry_run:
                tag.group = group
                tag.save(update_fields=['group'])
                self.stdout.write(self.style.SUCCESS(f'    ✓ Fixed'))

            count += 1

        self.stdout.write(f'\n  Total group fixes: {count}\n')

    def _phase6_remove_dead(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 6: Removing Dead Tags (0 Articles) ===\n'))

        dead_tags = Tag.objects.annotate(
            article_count=Count('articles')
        ).filter(article_count=0, group__isnull=True)

        count = dead_tags.count()
        self.stdout.write(f'  Found {count} dead tags (0 articles, no group)\n')

        for tag in dead_tags[:30]:
            self.stdout.write(f'    🗑️  "{tag.name}" (slug: {tag.slug})')

        if count > 30:
            self.stdout.write(f'    ... and {count - 30} more')

        if not dry_run and count > 0:
            dead_tags.delete()
            self.stdout.write(self.style.SUCCESS(f'\n  ✓ Deleted {count} dead tags'))

    def _print_summary(self):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Summary ===\n'))

        total = Tag.objects.count()
        grouped = Tag.objects.filter(group__isnull=False).count()
        ungrouped = Tag.objects.filter(group__isnull=True).count()

        self.stdout.write(f'  Total tags: {total}')
        self.stdout.write(f'  With group: {grouped}')
        self.stdout.write(f'  Without group: {ungrouped}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n  Per-group breakdown:'))
        for group in TagGroup.objects.all().order_by('order', 'name'):
            count = Tag.objects.filter(group=group).count()
            self.stdout.write(f'    {group.name}: {count} tags')
