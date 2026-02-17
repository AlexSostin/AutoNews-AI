"""
One-time fix to reassign 17 ungrouped/misplaced tags to correct groups.
Usage: python manage.py fix_tag_groups
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify


# Map: tag_name → correct group_name
FIXES = {
    # Misplaced
    'EV': 'Fuel Types',       # was in Manufacturers
    'AWD': 'Drivetrain',      # was in Models
    # Ungrouped → Body Types
    'SUV': 'Body Types',
    'Hatchback': 'Body Types',
    'Convertible': 'Body Types',
    'Wagon': 'Body Types',
    'Pickup Truck': 'Body Types',
    'Supercar': 'Body Types',
    # Ungrouped → Segments
    'Luxury': 'Segments',
    'Budget': 'Segments',
    'Performance': 'Segments',
    # Ungrouped → Manufacturers
    'ZEEKR': 'Manufacturers',
    'Dongfeng': 'Manufacturers',
    # Ungrouped → Tech & Features
    'Navigation': 'Tech & Features',
    'Technology': 'Tech & Features',
    'Advanced': 'Tech & Features',
    # Ungrouped → Years
    '2025': 'Years',
}


class Command(BaseCommand):
    help = 'Fix ungrouped and misplaced tags — assigns them to correct groups'

    def handle(self, *args, **options):
        from news.models import Tag, TagGroup

        self.stdout.write(self.style.MIGRATE_HEADING('🔧 Fixing tag groups...'))
        fixed = 0

        for tag_name, group_name in FIXES.items():
            try:
                tag = Tag.objects.filter(name=tag_name).first()
                if not tag:
                    self.stdout.write(f'  ⏭️  Tag "{tag_name}" not found — skipping')
                    continue

                group, created = TagGroup.objects.get_or_create(
                    name=group_name,
                    defaults={'slug': slugify(group_name)}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✨ Created group "{group_name}"'))

                old_group = tag.group.name if tag.group else 'ungrouped'
                if old_group == group_name:
                    self.stdout.write(f'  ✓ "{tag_name}" already in "{group_name}"')
                    continue

                tag.group = group
                tag.save(update_fields=['group'])
                fixed += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ "{tag_name}": {old_group} → {group_name}'
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ "{tag_name}": {e}'))

        self.stdout.write(f'\n{"="*50}')
        self.stdout.write(self.style.SUCCESS(f'✅ Done! Fixed {fixed} tags'))

        # Show current state
        self.stdout.write(self.style.MIGRATE_HEADING('\n📊 Current tag groups:'))
        for group in TagGroup.objects.order_by('order'):
            tags = list(Tag.objects.filter(group=group).values_list('name', flat=True))
            self.stdout.write(f'  {group.name}: {tags}')
        ungrouped = list(Tag.objects.filter(group__isnull=True).values_list('name', flat=True))
        if ungrouped:
            self.stdout.write(self.style.WARNING(f'  ⚠️ Still ungrouped: {ungrouped}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  ✅ No ungrouped tags!'))
