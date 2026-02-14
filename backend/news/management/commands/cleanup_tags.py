"""
Management command to clean up tags:
- Merge duplicate tags (reassign articles, then delete duplicate)
- Assign groups to ungrouped tags
- Optionally remove zero-article tags
"""
import re
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from news.models import Tag, TagGroup


# Merge map: source_slug → target_slug
# Articles from source will be moved to target, then source deleted
MERGE_MAP = {
    'electric': 'ev',                  # Electric(24) → EV(24)
    'plug-in-hybrid': 'phev',          # Plug-in Hybrid(2) → PHEV(15)
    'plug-in': 'phev',                 # Plug-in(1) → PHEV(15)
    'mercedes-benz': 'mercedes',       # Mercedes-Benz → Mercedes
    'formula-1': 'f1',                 # Formula 1 → F1
    'formula-e': 'formula-e',          # keep as is, just note
}

# Group assignments: tag_slug → group_slug
# These tags currently have group=NULL
GROUP_ASSIGNMENTS = {
    # → Body Types
    'convertible': 'body-types',
    'roadster': 'body-types',
    
    # → Tech & Features
    'design': 'tech-features',
    'interior': 'tech-features',
    'head-up-display': 'tech-features',
    'performance': 'tech-features',
    'infotainment': 'tech-features',
    'connected-car': 'tech-features',
    'self-driving': 'tech-features',
    
    # → Segments
    'comparison': 'segments',
    'first-drive': 'segments',
    'test-drive': 'segments',
    'review': 'segments',
    'supercar': 'segments',
    
    # → Events / Motorsports
    'racing': 'events-motorsports',
    'nascar': 'events-motorsports',
    'le-mans': 'events-motorsports',
    'indycar': 'events-motorsports',
    'rally': 'events-motorsports',
    'drift': 'segments',
    'track': 'events-motorsports',
    
    # → Fuel Types
    'eco': 'fuel-types',
    
    # → Manufacturers
    'vinfast': 'manufacturers',
    
    # → Industry/Business (no group yet, assign to general)
    'industry': 'tech-features',
    'innovation': 'tech-features',
    'technology': 'tech-features',
    'sustainability': 'tech-features',
    'environment': 'tech-features',
    'manufacturing': 'tech-features',
    'investment': 'tech-features',
    'sales': 'tech-features',
    'market': 'tech-features',
    'policy': 'tech-features',
    'regulation': 'tech-features',
    'infrastructure': 'tech-features',
    'supply-chain': 'tech-features',
    'climate': 'tech-features',
    'carbon-neutral': 'tech-features',
    'zero-emission': 'fuel-types',
    
    # → Engine Types (currently no group)
    'inline-4': 'tech-features',
    'inline-6': 'tech-features',
    'flat-4': 'tech-features',
    'flat-6': 'tech-features',
    'twin-turbo': 'tech-features',
    'supercharged': 'tech-features',
    'rotary': 'fuel-types',
    'lithium': 'tech-features',
    'solid-state': 'tech-features',
    
    # → Content types
    'news': 'segments',
    'update': 'segments',
    'spy-shots': 'segments',
    'teaser': 'segments',
    'reveal': 'segments',
    'debut': 'segments',
    'launch': 'segments',
    'facelift': 'segments',
    'refresh': 'segments',
    'next-generation': 'segments',
    'concept': 'segments',
    'production': 'segments',
    'recall': 'segments',
    'rumor': 'segments',
    'limited-edition': 'segments',
    'special-edition': 'segments',
    'gran-turismo': 'segments',
    
    # Misclassified
    'long-range': 'tech-features',  # Was in Manufacturers, should be Tech
}


class Command(BaseCommand):
    help = 'Clean up tags: merge duplicates, assign groups, remove dead tags'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--remove-dead',
            action='store_true',
            help='Remove tags with 0 articles and no group',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        remove_dead = options['remove_dead']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE - No changes will be made]\n'))
        
        # Phase 1: Merge duplicates
        self._merge_duplicates(dry_run)
        
        # Phase 2: Assign groups
        self._assign_groups(dry_run)
        
        # Phase 3: Fix misclassified tags
        self._fix_misclassified(dry_run)
        
        # Phase 4: Remove dead tags (optional)
        if remove_dead:
            self._remove_dead_tags(dry_run)
        
        # Summary
        self._print_summary()

    def _merge_duplicates(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 1: Merging Duplicate Tags ===\n'))
        merged_count = 0
        
        for source_slug, target_slug in MERGE_MAP.items():
            if source_slug == target_slug:
                continue  # Skip identity mappings
            
            try:
                source = Tag.objects.get(slug=source_slug)
            except Tag.DoesNotExist:
                continue  # Source doesn't exist, skip
            
            try:
                target = Tag.objects.get(slug=target_slug)
            except Tag.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Target tag "{target_slug}" not found, skipping merge of "{source_slug}"'
                ))
                continue
            
            # Count articles on source
            source_articles = source.article_set.all()
            article_count = source_articles.count()
            
            self.stdout.write(
                f'  📎 Merge: "{source.name}" ({article_count} articles) → "{target.name}" ({target.article_set.count()} articles)'
            )
            
            if not dry_run:
                # Move articles from source to target
                for article in source_articles:
                    article.tags.add(target)
                    article.tags.remove(source)
                
                # Delete the source tag
                source.delete()
                self.stdout.write(self.style.SUCCESS(f'    ✓ Merged and deleted "{source.name}"'))
            
            merged_count += 1
        
        self.stdout.write(f'\n  Total merges: {merged_count}\n')

    def _assign_groups(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 2: Assigning Groups to Ungrouped Tags ===\n'))
        
        # Cache tag groups by slug
        group_cache = {}
        for group in TagGroup.objects.all():
            group_cache[group.slug] = group
        
        # Also try matching by name-derived slug
        group_name_map = {
            'body-types': None,
            'tech-features': None,
            'segments': None,
            'events-motorsports': None,
            'fuel-types': None,
            'manufacturers': None,
        }
        
        for group in TagGroup.objects.all():
            slug = group.slug
            group_cache[slug] = group
            # Also map common name patterns
            name_slug = slugify(group.name)
            group_cache[name_slug] = group
        
        assigned_count = 0
        
        for tag_slug, group_slug in GROUP_ASSIGNMENTS.items():
            try:
                tag = Tag.objects.get(slug=tag_slug)
            except Tag.DoesNotExist:
                continue
            
            if tag.group is not None:
                # Already has a group, check if it needs reassignment
                if tag_slug in ('long-range',):  # Known misclassified
                    pass  # Will be handled in _fix_misclassified
                else:
                    continue  # Already grouped, skip
            
            # Find the target group
            group = group_cache.get(group_slug)
            if not group:
                # Try partial matches
                for g in TagGroup.objects.all():
                    if group_slug in g.slug or group_slug in slugify(g.name):
                        group = g
                        group_cache[group_slug] = g
                        break
            
            if not group:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ Group "{group_slug}" not found for tag "{tag.name}"'
                ))
                continue
            
            self.stdout.write(f'  🏷️  "{tag.name}" → group "{group.name}"')
            
            if not dry_run:
                tag.group = group
                tag.save(update_fields=['group'])
                self.stdout.write(self.style.SUCCESS(f'    ✓ Assigned'))
            
            assigned_count += 1
        
        self.stdout.write(f'\n  Total assignments: {assigned_count}\n')

    def _fix_misclassified(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 3: Fixing Misclassified Tags ===\n'))
        
        # Long-Range is in Manufacturers but should be Tech & Features
        try:
            tag = Tag.objects.get(slug='long-range')
            if tag.group and tag.group.name == 'Manufacturers':
                target_group = TagGroup.objects.filter(
                    slug__icontains='tech'
                ).first()
                
                if target_group:
                    self.stdout.write(
                        f'  🔄 "{tag.name}": Manufacturers → {target_group.name}'
                    )
                    if not dry_run:
                        tag.group = target_group
                        tag.save(update_fields=['group'])
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Fixed'))
        except Tag.DoesNotExist:
            pass

    def _remove_dead_tags(self, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Phase 4: Removing Dead Tags ===\n'))
        
        # Only remove tags that have 0 articles AND no group
        dead_tags = Tag.objects.filter(group__isnull=True).annotate(
            article_count=__import__('django.db.models', fromlist=['Count']).Count('articles')
        ).filter(article_count=0)
        
        # Safer approach: query manually
        from django.db.models import Count
        dead_tags = Tag.objects.annotate(
            article_count=Count('articles')
        ).filter(article_count=0, group__isnull=True)
        
        count = dead_tags.count()
        self.stdout.write(f'  Found {count} dead tags (0 articles, no group)\n')
        
        for tag in dead_tags[:20]:  # Show first 20
            self.stdout.write(f'    🗑️  "{tag.name}" (slug: {tag.slug})')
        
        if count > 20:
            self.stdout.write(f'    ... and {count - 20} more')
        
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
        
        # Per-group breakdown
        self.stdout.write(self.style.MIGRATE_HEADING('\n  Per-group breakdown:'))
        for group in TagGroup.objects.all().order_by('order', 'name'):
            count = Tag.objects.filter(group=group).count()
            self.stdout.write(f'    {group.name}: {count} tags')
