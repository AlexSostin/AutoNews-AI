from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth.models import User
from news.models import Category, Tag, Article, SiteSettings
import random


class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting database population...\n")

        # 1. Create Categories
        self.stdout.write("\n📁 Creating categories...")
        categories_data = [
            ('News', 'news'),
            ('Reviews', 'reviews'),
            ('EVs', 'evs'),
            ('Technology', 'technology'),
            ('Industry', 'industry'),
            ('Classics', 'classics'),
            ('Motorsport', 'motorsport'),
            ('Modifications', 'modifications'),
            ('Comparisons', 'comparisons'),
        ]

        categories = []
        for name, slug in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name}
            )
            categories.append(cat)
            self.stdout.write(f"{'✅ Created' if created else '✓ Exists'}: {name}")

        # 2. Create Tags
        self.stdout.write("\n🏷️ Creating tags...")
        tags_data = [
            'Tesla', 'BMW', 'Mercedes', 'Audi', 'Toyota',
            'Electric', 'Hybrid', 'SUV', 'Sedan', 'Sport',
            'Luxury', 'Budget', 'Off-road', 'City', 'Family'
        ]

        tags = []
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(
                slug=slugify(tag_name),
                defaults={'name': tag_name}
            )
            tags.append(tag)
            self.stdout.write(f"{'✅' if created else '✓'} {tag_name}")

        # 3. Create sample articles
        self.stdout.write("\n📰 Creating sample articles...")

        sample_articles = [
            {
                'title': 'Tesla Model 3 - Electric Revolution on Wheels',
                'excerpt': 'In-depth review of the world\'s best-selling electric vehicle',
                'content': '''# Tesla Model 3: Complete Review

The Tesla Model 3 has become the world's best-selling electric vehicle. Here's why it's revolutionizing the automotive industry.

## Design
Minimalist interior design featuring a massive central touchscreen that controls virtually everything.

## Technology
- Full Self-Driving Autopilot capability
- Over-the-air software updates
- Up to 358 miles (576 km) of range
- Mobile app control and monitoring

## Performance
- 0-60 mph in 3.1 seconds (Performance variant)
- Top speed of 162 mph (261 km/h)
- Instant torque delivery
- Low center of gravity for superior handling

## Price
Starting from $40,000 for the base model.

## Verdict
The Model 3 sets the benchmark for electric sedans with its blend of performance, technology, and efficiency.''',
                'category': categories[2],  # EVs
                'tags_idx': [0, 5, 8],  # Tesla, Electric, Sedan
            },
            {
                'title': 'BMW M5 Competition 2026 - The King of Sport Sedans',
                'excerpt': 'New generation of BMW\'s legendary performance sedan',
                'content': '''# BMW M5 Competition 2026

The new M5 Competition combines brutal performance with everyday usability.

## Engine
4.4L Twin-Turbo V8 with hybrid system
- Power: 727 horsepower
- Torque: 1000 Nm (738 lb-ft)
- Hybrid electric boost for instant response

## Performance
- 0-60 mph in 2.9 seconds
- Top speed: 189 mph (limited)
- All-wheel drive with M xDrive system

## Interior
Premium materials throughout with carbon fiber accents and sport bucket seats. Latest iDrive 9 infotainment system.

## Technology
- M Drift Analyzer
- Track mode with telemetry
- Adaptive M suspension

## Price
Starting at $115,000

## Conclusion
The ultimate driver's sedan that doesn't compromise on comfort or practicality.''',
                'category': categories[1],  # Reviews
                'tags_idx': [1, 9, 10],  # BMW, Sport, Luxury
            },
            {
                'title': 'Toyota Land Cruiser 300 - The Legend Continues',
                'excerpt': 'New generation of the world\'s most reliable off-roader',
                'content': '''# Toyota Land Cruiser 300

The Land Cruiser nameplate has been synonymous with reliability and capability for over 70 years.

## Reliability
Toyota's legendary build quality means these vehicles regularly exceed 300,000 miles with minimal issues.

## Off-Road Capabilities
- Full-time 4WD system
- Electronic locking differentials
- Adaptive air suspension
- Multi-Terrain Select
- Crawl Control for extreme terrain

## Engine
3.5L Twin-Turbo V6 producing 415 horsepower and 442 lb-ft of torque. 10-speed automatic transmission.

## Technology
- 12.3-inch touchscreen
- 360-degree camera system
- Apple CarPlay and Android Auto
- Toyota Safety Sense 3.0

## Price
Starting from $85,000

## Verdict
The Land Cruiser 300 maintains its reputation as the go-anywhere SUV while adding modern comfort and technology.''',
                'category': categories[0],  # News
                'tags_idx': [4, 7, 12],  # Toyota, SUV, Off-road
            },
            {
                'title': 'Mercedes S-Class W223 - The Pinnacle of Luxury',
                'excerpt': 'The most technologically advanced sedan in the world',
                'content': '''# Mercedes-Benz S-Class W223

The flagship Mercedes represents the absolute pinnacle of automotive luxury and technology.

## Technology
- MBUX with AI voice assistant
- Augmented reality navigation
- 12 airbags including rear side airbags
- Level 3 autonomous driving capability
- Gesture controls and ambient lighting with 64 colors

## Comfort
Executive rear seats with massage, heating, ventilation, and multiple adjustment options. Active road noise cancellation.

## Engine Options
From 3.0L inline-6 mild hybrid to 6.0L V12 in the Maybach variant.
- S500: 429 hp
- S580: 496 hp  
- AMG S63: 603 hp

## Interior
Finest Nappa leather, real wood trim, and executive rear seating with entertainment system.

## Price
Starting from $115,000 (S500)

## Conclusion
The S-Class defines what a luxury sedan should be, setting standards that others can only aspire to match.''',
                'category': categories[1],  # Reviews
                'tags_idx': [2, 10, 8],  # Mercedes, Luxury, Sedan
            },
            {
                'title': 'Porsche 911 GT3 - The Ultimate Driver\'s Car',
                'excerpt': 'Track-focused sports car that\'s equally at home on the road',
                'content': '''# Porsche 911 GT3

The GT3 represents Porsche's purest driving experience, a naturally aspirated masterpiece.

## Engine
4.0L flat-six naturally aspirated engine
- Power: 510 horsepower
- Rev limit: 9,000 RPM
- Sound: Spine-tingling mechanical symphony

## Track Performance
- Nürburgring lap time: 6:55 (one of the fastest production cars)
- PDK or 6-speed manual transmission
- Rear-wheel steering
- Limited-slip differential

## Aerodynamics
Massive rear wing generates significant downforce. Front splitter and diffuser work in harmony for balance.

## Daily Usability
Despite its track focus, the GT3 is surprisingly comfortable for daily driving with decent ride quality and practical trunk space.

## Price
Starting from $170,000

## Verdict
The 911 GT3 is the gold standard for track-capable sports cars, offering an analog driving experience in an increasingly digital world.''',
                'category': categories[6],  # Motorsport
                'tags_idx': [9, 10],  # Sport, Luxury
            }
        ]

        for article_data in sample_articles:
            article, created = Article.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    'slug': slugify(article_data['title'][:50]),
                    'summary': article_data['excerpt'],  # Use 'summary' instead of 'excerpt'
                    'content': article_data['content'],
                    'category': article_data['category'],
                    # No 'author' field in Article model
                    'is_published': True,
                    'views': 0,  # Real views only
                }
            )
            
            if created:
                article_tags = [tags[i] for i in article_data['tags_idx'] if i < len(tags)]
                article.tags.set(article_tags)
                self.stdout.write(f"✅ Created: {article.title[:50]}...")
            else:
                self.stdout.write(f"✓ Exists: {article.title[:50]}...")

        # 4. Create Site Settings
        self.stdout.write("\n⚙️ Creating site settings...")
        settings, created = SiteSettings.objects.get_or_create(
            id=1,
            defaults={
                'site_name': 'AutoNews',
                'site_description': 'The best automotive news and reviews',
                'contact_email': 'info@autonews.ai',
                # No contact_phone field in SiteSettings model
                'footer_text': '© 2026 AutoNews. All rights reserved.',
            }
        )
        self.stdout.write(f"{'✅ Created' if created else '✓ Exists'}: Site Settings")

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("🎉 Database populated successfully!"))
        self.stdout.write("="*50)
        self.stdout.write(f"\n📊 Statistics:")
        self.stdout.write(f"  Categories: {Category.objects.count()}")
        self.stdout.write(f"  Tags: {Tag.objects.count()}")
        self.stdout.write(f"  Articles: {Article.objects.count()}")
        self.stdout.write(f"  Users: {User.objects.count()}")
        self.stdout.write("\n✅ Ready to go!")
