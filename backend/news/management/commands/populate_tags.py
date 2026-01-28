"""
Management command to populate database with automotive tags
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from news.models import Tag


class Command(BaseCommand):
    help = 'Populate database with common automotive tags'

    def handle(self, *args, **options):
        tags = [
            # Brands
            "Tesla", "BMW", "Mercedes-Benz", "Audi", "Porsche", "Toyota", "Honda",
            "Ford", "Chevrolet", "Volkswagen", "Nissan", "Hyundai", "Kia", "Mazda",
            "Volvo", "Jaguar", "Land Rover", "Lexus", "Genesis", "Rivian", "Lucid",
            "Ferrari", "Lamborghini", "McLaren", "Bentley", "Rolls-Royce", "Maserati",
            "Alfa Romeo", "Fiat", "Peugeot", "Renault", "Citroen", "Skoda", "SEAT",
            "Mini", "Subaru", "Mitsubishi", "Suzuki", "Infiniti", "Acura", "Lincoln",
            "Cadillac", "Buick", "GMC", "Ram", "Jeep", "Dodge", "Chrysler",
            "BYD", "NIO", "XPeng", "Li Auto", "Zeekr", "Polestar", "Vinfast",
            
            # Vehicle Types
            "Sedan", "SUV", "Truck", "Coupe", "Convertible", "Hatchback", "Wagon",
            "Minivan", "Crossover", "Sports Car", "Supercar", "Hypercar", "Pickup",
            "Van", "MPV", "Roadster", "Gran Turismo", "Shooting Brake",
            
            # Powertrain
            "Electric", "Hybrid", "Plug-in Hybrid", "Gasoline", "Diesel", "Hydrogen",
            "Battery", "EV", "ICE", "AWD", "4WD", "FWD", "RWD", "PHEV", "BEV", "FCEV",
            "Turbo", "Supercharged", "Twin-Turbo", "V6", "V8", "V10", "V12", "Inline-4",
            "Inline-6", "Flat-4", "Flat-6", "Rotary",
            
            # Technology
            "Autonomous", "Self-Driving", "Autopilot", "ADAS", "Safety", "AI",
            "Connected Car", "Infotainment", "CarPlay", "Android Auto", "OTA Update",
            "LiDAR", "Radar", "Camera", "Sensors", "Lane Assist", "Adaptive Cruise",
            "Parking Assist", "Night Vision", "Head-Up Display", "Digital Cockpit",
            
            # Features
            "Performance", "Luxury", "Off-Road", "Towing", "Fuel Economy",
            "Fast Charging", "Range", "Interior", "Design", "Aerodynamics",
            "Comfort", "Premium", "Sport", "Racing", "Track", "Drift",
            "Family", "City", "Budget", "Eco", "Green",
            
            # Categories
            "Review", "First Drive", "Test Drive", "Comparison", "Launch",
            "Concept", "Production", "Recall", "Update", "News", "Rumor",
            "Spy Shots", "Teaser", "Reveal", "Debut", "Facelift", "Refresh",
            "Next Generation", "Special Edition", "Limited Edition",
            
            # Year Tags
            "2024", "2025", "2026", "2027", "2028", "2029", "2030",
            
            # Topics
            "Charging", "Infrastructure", "Policy", "Regulation", "Sales",
            "Market", "Industry", "Technology", "Innovation", "Sustainability",
            "Environment", "Carbon Neutral", "Zero Emission", "Climate",
            "Investment", "Factory", "Manufacturing", "Supply Chain",
            "Chip Shortage", "Battery Technology", "Solid State", "Lithium",
            
            # Motorsport
            "Formula 1", "F1", "NASCAR", "Rally", "Le Mans", "Endurance",
            "IndyCar", "MotoGP", "DTM", "WRC", "Formula E", "Dakar",
            
            # Events & Shows
            "Auto Show", "Geneva", "Detroit", "Los Angeles", "New York",
            "Frankfurt", "Paris", "Tokyo", "Beijing", "Shanghai", "CES",
        ]

        created_count = 0
        existing_count = 0

        for tag_name in tags:
            slug = slugify(tag_name)
            # Use slug for lookup to avoid duplicates with different casing
            tag, created = Tag.objects.get_or_create(
                slug=slug,
                defaults={'name': tag_name}
            )
            if created:
                created_count += 1
            else:
                existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Tags: {created_count} created, {existing_count} already existed. '
                f'Total: {Tag.objects.count()}'
            )
        )
