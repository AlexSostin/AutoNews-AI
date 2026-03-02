from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from ..image_utils import optimize_image


# Intra-package imports to resolve foreign keys if needed

class Brand(models.Model):
    """
    Managed brand entity for the car catalog.
    
    Unlike the auto-aggregated brands from CarSpecification.make,
    this model gives admins full control: rename, reorder, merge,
    hide/show brands, upload logos, group sub-brands under parents.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Display name")
    slug = models.SlugField(max_length=120, unique=True, help_text="URL slug")
    logo = models.ImageField(upload_to='brands/', blank=True, help_text="Brand logo")
    country = models.CharField(max_length=50, blank=True, help_text="Country of origin")
    description = models.TextField(blank=True, help_text="Short brand description")
    sort_order = models.IntegerField(default=0, help_text="Manual sort order (0=auto by article count)")
    is_visible = models.BooleanField(default=True, help_text="Show in public catalog")
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sub_brands',
        help_text="Parent brand (e.g. DongFeng for VOYAH)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sort_order', 'name']
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name

    def get_article_count(self):
        """Count articles for this brand (and sub-brands), case-insensitive."""
        names = [self.name]
        for sub in self.sub_brands.all():
            names.append(sub.name)
        q = Q()
        for n in names:
            q |= Q(make__iexact=n)
        return CarSpecification.objects.filter(
            q, article__is_published=True
        ).values('article').distinct().count()

    def get_model_count(self):
        """Count unique models for this brand (and sub-brands), case-insensitive."""
        names = [self.name]
        for sub in self.sub_brands.all():
            names.append(sub.name)
        q = Q()
        for n in names:
            q |= Q(make__iexact=n)
        return CarSpecification.objects.filter(
            q
        ).exclude(model='').exclude(model='Not specified').values('model').distinct().count()

class BrandAlias(models.Model):
    """Maps brand name variations to a canonical name.
    
    Two modes:
    1. Simple alias (model_prefix=''):
       alias='DongFeng VOYAH' → canonical_name='VOYAH'
       Matches when make == alias, regardless of model.
    
    2. Sub-brand extraction (model_prefix set):
       alias='BYD', canonical_name='DENZA', model_prefix='Denza'
       Matches when make=='BYD' AND model starts with 'Denza'.
       Strips prefix from model: 'Denza D9' → 'D9'.
    """
    alias = models.CharField(
        max_length=100,
        help_text="The name variation (what AI might produce, e.g. 'DongFeng VOYAH')"
    )
    canonical_name = models.CharField(
        max_length=100,
        help_text="The correct brand name (e.g. 'VOYAH')"
    )
    model_prefix = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Sub-brand prefix in model name. If set, only matches when model starts with this prefix. Prefix is stripped from model."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Brand Aliases"
        ordering = ['canonical_name', 'alias']
        constraints = [
            models.UniqueConstraint(
                fields=['alias', 'model_prefix'],
                name='unique_alias_prefix',
            ),
        ]

    def __str__(self):
        if self.model_prefix:
            return f"{self.alias} + model:{self.model_prefix}* → {self.canonical_name}"
        return f"{self.alias} → {self.canonical_name}"

    @classmethod
    def resolve(cls, make):
        """Resolve a make name through simple aliases (no model_prefix).
        Returns canonical name or original. Kept for backward compatibility."""
        if not make:
            return make
        alias = cls.objects.filter(alias__iexact=make, model_prefix='').first()
        return alias.canonical_name if alias else make

    @classmethod
    def resolve_with_model(cls, make, model=''):
        """Resolve make+model through sub-brand rules then simple aliases.
        
        Returns (resolved_make, resolved_model).
        
        Example:
            BrandAlias(alias='BYD', canonical_name='DENZA', model_prefix='Denza')
            resolve_with_model('BYD', 'Denza D9') → ('DENZA', 'D9')
            resolve_with_model('BYD', 'Seal') → ('BYD', 'Seal')  # no match
        """
        if not make:
            return make, model
        
        # 1. Check sub-brand rules (model_prefix != '')
        if model:
            sub_brand_aliases = cls.objects.exclude(model_prefix='')
            for alias in sub_brand_aliases:
                if (make.lower().strip() == alias.alias.lower().strip() and
                        model.lower().strip().startswith(alias.model_prefix.lower().strip())):
                    new_model = model[len(alias.model_prefix):].strip()
                    return alias.canonical_name, new_model if new_model else model
        
        # 2. Fallback: simple name alias (existing behavior)
        resolved_make = cls.resolve(make)
        return resolved_make, model

class CarSpecification(models.Model):
    article = models.OneToOneField('news.Article', on_delete=models.CASCADE, related_name='specs')
    model_name = models.CharField(max_length=200, help_text="Specific trim or model (Legacy)")
    make = models.CharField(max_length=100, blank=True, db_index=True, help_text="Car Brand")
    model = models.CharField(max_length=100, blank=True, db_index=True, help_text="Base Model")
    trim = models.CharField(max_length=100, blank=True, help_text="Trim or Version")
    engine = models.CharField(max_length=200, blank=True)
    horsepower = models.CharField(max_length=50, blank=True)
    torque = models.CharField(max_length=50, blank=True)
    zero_to_sixty = models.CharField(max_length=50, blank=True, help_text="0-60 mph time")
    top_speed = models.CharField(max_length=50, blank=True)
    drivetrain = models.CharField(max_length=50, blank=True, help_text="AWD, FWD, RWD, 4WD")
    price = models.CharField(max_length=100, blank=True)
    release_date = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Manually verified by editor")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When specs were verified")
    is_make_locked = models.BooleanField(
        default=False,
        help_text="When True, make/model won't be overwritten by AI re-extraction or VehicleSpecs sync. "
                  "Set automatically by move-article."
    )
    
    def __str__(self):
        return f"Specs for {self.article.title}"

class VehicleSpecs(models.Model):
    """
    AI-extracted vehicle specifications from articles.
    Supports multiple trim variants per car model.
    """
    article = models.ForeignKey('news.Article',
        on_delete=models.SET_NULL,
        related_name='vehicle_specs_set',
        null=True, blank=True,
        help_text="Source article (optional)"
    )
    
    # Car identification — used to group trims on /cars/ pages
    make = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Car brand (e.g. Zeekr, BMW, Tesla)"
    )
    model_name = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Model name (e.g. 007 GT, iX3, Model 3)"
    )
    trim_name = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Trim variant (e.g. AWD 100 kWh, Long Range, Performance)"
    )
    
    # Drivetrain
    DRIVETRAIN_CHOICES = [
        ('FWD', 'Front-Wheel Drive'),
        ('RWD', 'Rear-Wheel Drive'),
        ('AWD', 'All-Wheel Drive'),
        ('4WD', 'Four-Wheel Drive'),
    ]
    drivetrain = models.CharField(
        max_length=10,
        choices=DRIVETRAIN_CHOICES,
        null=True, blank=True,
        help_text="Drive configuration"
    )
    motor_count = models.IntegerField(
        null=True, blank=True,
        help_text="Number of electric motors"
    )
    motor_placement = models.CharField(
        max_length=50,
        null=True, blank=True,
        help_text="Motor location (e.g., 'front', 'rear', 'front+rear')"
    )
    
    # Performance
    power_hp = models.IntegerField(
        null=True, blank=True,
        help_text="Power in horsepower"
    )
    power_kw = models.IntegerField(
        null=True, blank=True,
        help_text="Power in kilowatts"
    )
    torque_nm = models.IntegerField(
        null=True, blank=True,
        help_text="Torque in Newton-meters"
    )
    acceleration_0_100 = models.FloatField(
        null=True, blank=True,
        help_text="0-100 km/h acceleration time in seconds"
    )
    top_speed_kmh = models.IntegerField(
        null=True, blank=True,
        help_text="Top speed in km/h"
    )
    
    # EV Specifications
    battery_kwh = models.FloatField(
        null=True, blank=True,
        help_text="Battery capacity in kWh"
    )
    range_km = models.IntegerField(
        null=True, blank=True,
        help_text="Range in kilometers (general)"
    )
    range_wltp = models.IntegerField(
        null=True, blank=True,
        help_text="WLTP range in kilometers"
    )
    range_epa = models.IntegerField(
        null=True, blank=True,
        help_text="EPA range in kilometers"
    )
    range_cltc = models.IntegerField(
        null=True, blank=True,
        help_text="CLTC range in kilometers (Chinese standard)"
    )
    combined_range_km = models.IntegerField(
        null=True, blank=True,
        help_text="Total combined range for PHEVs (gas+electric) in km"
    )
    
    # Charging
    charging_time_fast = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Fast charging time (e.g., '30 min to 80%')"
    )
    charging_time_slow = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Slow/AC charging time"
    )
    charging_power_max_kw = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum charging power in kW"
    )
    
    # Transmission
    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
        ('CVT', 'CVT'),
        ('single-speed', 'Single-Speed'),
        ('dual-clutch', 'Dual-Clutch'),
    ]
    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        null=True, blank=True,
        help_text="Transmission type"
    )
    transmission_gears = models.IntegerField(
        null=True, blank=True,
        help_text="Number of gears"
    )
    
    # General Vehicle Info
    BODY_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('coupe', 'Coupe'),
        ('truck', 'Truck'),
        ('crossover', 'Crossover'),
        ('wagon', 'Wagon'),
        ('shooting_brake', 'Shooting Brake'),
        ('van', 'Van'),
        ('convertible', 'Convertible'),
        ('pickup', 'Pickup'),
        ('liftback', 'Liftback'),
        ('fastback', 'Fastback'),
        ('MPV', 'MPV / Minivan'),
        ('roadster', 'Roadster'),
        ('cabriolet', 'Cabriolet'),
        ('targa', 'Targa'),
        ('limousine', 'Limousine'),
    ]
    body_type = models.CharField(
        max_length=20,
        choices=BODY_TYPE_CHOICES,
        null=True, blank=True,
        help_text="Body style"
    )
    
    FUEL_TYPE_CHOICES = [
        ('EV', 'Electric Vehicle'),
        ('Hybrid', 'Hybrid'),
        ('PHEV', 'Plug-in Hybrid'),
        ('Gas', 'Gasoline'),
        ('Diesel', 'Diesel'),
        ('Hydrogen', 'Hydrogen'),
    ]
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        null=True, blank=True,
        help_text="Fuel/power source type"
    )
    
    seats = models.IntegerField(
        null=True, blank=True,
        help_text="Number of seats"
    )
    
    # Dimensions
    length_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Length in millimeters"
    )
    width_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Width in millimeters"
    )
    height_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Height in millimeters"
    )
    wheelbase_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Wheelbase in millimeters"
    )
    weight_kg = models.IntegerField(
        null=True, blank=True,
        help_text="Curb weight in kilograms"
    )
    cargo_liters = models.IntegerField(
        null=True, blank=True,
        help_text="Cargo/trunk capacity in liters"
    )
    cargo_liters_max = models.IntegerField(
        null=True, blank=True,
        help_text="Max cargo with seats folded in liters"
    )
    ground_clearance_mm = models.IntegerField(
        null=True, blank=True,
        help_text="Ground clearance in millimeters"
    )
    towing_capacity_kg = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum towing capacity in kg"
    )
    
    # Pricing
    price_from = models.IntegerField(
        null=True, blank=True,
        help_text="Starting price"
    )
    price_to = models.IntegerField(
        null=True, blank=True,
        help_text="Maximum price"
    )
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('CNY', 'Chinese Yuan'),
        ('RUB', 'Russian Ruble'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Price currency"
    )
    price_usd_from = models.IntegerField(
        null=True, blank=True,
        help_text="Price in USD (auto-converted from original currency)"
    )
    price_usd_to = models.IntegerField(
        null=True, blank=True,
        help_text="Max price in USD (auto-converted)"
    )
    price_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When price/exchange rate was last updated"
    )
    
    # Additional Info
    year = models.IntegerField(
        null=True, blank=True,
        help_text="Release year"
    )
    model_year = models.IntegerField(
        null=True, blank=True,
        help_text="Model year"
    )
    country_of_origin = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Country where manufactured"
    )
    
    # Technical Details
    platform = models.CharField(
        max_length=100,
        null=True, blank=True,
        help_text="Vehicle platform (e.g., SEA, MEB, E-GMP, TNGA)"
    )
    voltage_architecture = models.IntegerField(
        null=True, blank=True,
        help_text="Electrical architecture voltage (400, 800, 900)"
    )
    suspension_type = models.CharField(
        max_length=200,
        null=True, blank=True,
        help_text="Suspension type (e.g., air suspension, adaptive, McPherson)"
    )
    
    # Flexible extra specs (no migrations needed for new fields)
    extra_specs = models.JSONField(
        default=dict, blank=True,
        help_text="Additional specs as key-value pairs (e.g., {'panoramic_roof': true, 'lidar': 'Hesai ATX'})"
    )
    
    # Metadata
    extracted_at = models.DateTimeField(
        auto_now=True,
        help_text="When specs were last extracted/updated"
    )
    confidence_score = models.FloatField(
        default=0.0,
        help_text="AI extraction confidence (0.0-1.0)"
    )
    
    class Meta:
        verbose_name = "Vehicle Specification"
        verbose_name_plural = "Vehicle Specifications"
        ordering = ['make', 'model_name', 'trim_name']
        unique_together = [('make', 'model_name', 'trim_name')]
    
    def __str__(self):
        parts = [self.make, self.model_name, self.trim_name]
        label = ' '.join(p for p in parts if p)
        if not label and self.article:
            label = self.article.title[:50]
        return f"Specs: {label or 'Unnamed'}"
    
    def get_power_display(self):
        """Return formatted power string"""
        if self.power_hp and self.power_kw:
            return f"{self.power_hp} HP / {self.power_kw} kW"
        elif self.power_hp:
            return f"{self.power_hp} HP"
        elif self.power_kw:
            return f"{self.power_kw} kW"
        return "N/A"
    
    def get_range_display(self):
        """Return formatted range string"""
        if self.range_wltp:
            return f"{self.range_wltp} km (WLTP)"
        elif self.range_epa:
            return f"{self.range_epa} km (EPA)"
        elif self.range_km:
            return f"{self.range_km} km"
        return "N/A"
    
    def get_price_display(self):
        """Return formatted price in original currency only.
        USD conversion is handled by the frontend PriceConverter (live rates)."""
        if not self.price_from:
            return "N/A"
        
        symbols = {'CNY': '¥', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'RUB': '₽'}
        sym = symbols.get(self.currency, self.currency + ' ')
        
        if self.currency == 'USD':
            if self.price_to:
                return f"${self.price_from:,} – ${self.price_to:,}"
            return f"From ${self.price_from:,}"
        
        # Non-USD: show original currency only (no stale USD estimate)
        if self.price_to:
            return f"{sym}{self.price_from:,} – {sym}{self.price_to:,}"
        
        return f"From {sym}{self.price_from:,}"

