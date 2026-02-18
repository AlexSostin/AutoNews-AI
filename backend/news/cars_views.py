"""
Car Catalog API — read-only endpoints for browsing cars by brand/model.
Data is auto-populated from CarSpecification records attached to articles.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db.models import Count, Q
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import CarSpecification, Article, Tag, Brand, BrandAlias
from .serializers import BrandSerializer


def _get_image_url(article, request):
    """Get absolute image URL for an article."""
    if not article.image:
        return None
    # Check raw DB value FIRST — if it's already an absolute URL,
    # don't call .url which would double it via Cloudinary storage
    raw = str(article.image)
    if raw.startswith('http://') or raw.startswith('https://'):
        return raw
    # Use .url for relative paths (goes through storage backend)
    relative = article.image.url if hasattr(article.image, 'url') else raw
    if not relative:
        return None
    if relative.startswith('http://') or relative.startswith('https://'):
        return relative
    return request.build_absolute_uri(relative)


class CarBrandsListView(APIView):
    """GET /api/v1/cars/brands/ — List all brands with model counts."""
    permission_classes = [AllowAny]

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def get(self, request):
        # Use Brand model if populated, otherwise fall back to old aggregation
        brand_count = Brand.objects.count()
        
        if brand_count > 0:
            # New path: read from managed Brand model
            brands = (
                Brand.objects
                .filter(is_visible=True, parent__isnull=True)  # Top-level visible only
                .select_related('parent')
                .prefetch_related('sub_brands')
            )
            
            # Prefetch all first specs for images in ONE query
            all_specs = (
                CarSpecification.objects
                .filter(article__is_published=True)
                .exclude(make='')
                .exclude(make='Not specified')
                .select_related('article')
                .order_by('make', 'id')
            )
            spec_by_make = {}
            for spec in all_specs:
                key = spec.make.lower()
                if key not in spec_by_make:
                    spec_by_make[key] = spec
            
            result = []
            for brand in brands:
                # Get image from first spec (or logo if uploaded)
                image = None
                if brand.logo:
                    raw = str(brand.logo)
                    if raw.startswith('http://') or raw.startswith('https://'):
                        image = raw
                    elif hasattr(brand.logo, 'url'):
                        image = request.build_absolute_uri(brand.logo.url)
                
                if not image:
                    first_spec = spec_by_make.get(brand.name.lower())
                    if first_spec:
                        image = _get_image_url(first_spec.article, request)
                
                result.append({
                    'id': brand.id,
                    'name': brand.name,
                    'slug': brand.slug,
                    'model_count': brand.get_model_count(),
                    'article_count': brand.get_article_count(),
                    'image': image,
                    'country': brand.country,
                    'description': brand.description,
                    'sub_brands': [
                        {'name': s.name, 'slug': s.slug}
                        for s in brand.sub_brands.filter(is_visible=True)
                    ],
                })
            
            # Sort: manual sort_order first (desc), then by article_count
            result.sort(key=lambda x: (-x.get('article_count', 0),))
            # Brands with sort_order > 0 go first
            result.sort(key=lambda x: 0 if not any(
                b.sort_order for b in brands if b.name == x['name']
            ) else -1)
            
            return Response(result)
        
        # Fallback: old aggregation (no Brand records yet)
        from django.db.models.functions import Upper
        brands_qs = (
            CarSpecification.objects
            .exclude(make='')
            .exclude(make='Not specified')
            .annotate(make_upper=Upper('make'))
            .values('make_upper')
            .annotate(
                model_count=Count('model', distinct=True),
                article_count=Count('article', distinct=True),
            )
            .filter(model_count__gt=0)
            .order_by('-article_count')
        )

        all_specs = (
            CarSpecification.objects
            .filter(article__is_published=True)
            .exclude(make='')
            .exclude(make='Not specified')
            .select_related('article')
            .order_by('make', 'id')
        )
        spec_by_make = {}
        for spec in all_specs:
            key = spec.make.upper()
            if key not in spec_by_make:
                spec_by_make[key] = spec

        result = []
        for b in brands_qs:
            make_upper = b['make_upper']
            first_spec = spec_by_make.get(make_upper)
            if not first_spec:
                continue

            make = first_spec.make
            image = _get_image_url(first_spec.article, request)

            result.append({
                'name': make,
                'slug': slugify(make),
                'model_count': b['model_count'],
                'article_count': b['article_count'],
                'image': image,
            })

        return Response(result)


class CarBrandDetailView(APIView):
    """GET /api/v1/cars/brands/{slug}/ — All models for a brand."""
    permission_classes = [AllowAny]

    def get(self, request, brand_slug):
        # Find brand name from slug (case-insensitive match)
        all_makes = (
            CarSpecification.objects
            .exclude(make='')
            .exclude(make='Not specified')
            .values_list('make', flat=True)
            .distinct()
        )
        brand_name = None
        for make in all_makes:
            if slugify(make) == brand_slug:
                brand_name = make
                break

        if not brand_name:
            return Response({'error': 'Brand not found'}, status=404)

        # Get all unique models for this brand (case-insensitive make match)
        models = (
            CarSpecification.objects
            .filter(make__iexact=brand_name, article__is_published=True)
            .exclude(model='')
            .exclude(model='Not specified')
            .values('model')
            .annotate(
                trim_count=Count('trim', distinct=True),
                article_count=Count('article', distinct=True),
            )
            .order_by('-article_count')
        )

        result_models = []
        for m in models:
            model_name = m['model']
            # Get the "best" spec (most detailed) for display
            spec = (
                CarSpecification.objects
                .filter(make__iexact=brand_name, model=model_name, article__is_published=True)
                .select_related('article')
                .first()
            )
            if not spec:
                continue

            image = _get_image_url(spec.article, request)

            price_date = ''
            if spec.price and spec.article.created_at:
                price_date = spec.article.created_at.strftime('%b %Y')

            result_models.append({
                'model': model_name,
                'slug': slugify(model_name),
                'trim_count': m['trim_count'],
                'article_count': m['article_count'],
                'engine': spec.engine or '',
                'horsepower': spec.horsepower or '',
                'price': spec.price or '',
                'price_date': price_date,
                'image': image,
            })

        return Response({
            'brand': brand_name,
            'slug': brand_slug,
            'model_count': len(result_models),
            'models': result_models,
        })


class CarModelDetailView(APIView):
    """GET /api/v1/cars/brands/{brand}/{model}/ — Full model page with specs."""
    permission_classes = [AllowAny]

    def get(self, request, brand_slug, model_slug):
        # Find brand name
        all_makes = (
            CarSpecification.objects
            .exclude(make='')
            .values_list('make', flat=True)
            .distinct()
        )
        brand_name = None
        for make in all_makes:
            if slugify(make) == brand_slug:
                brand_name = make
                break

        if not brand_name:
            return Response({'error': 'Brand not found'}, status=404)

        # Find model name
        all_models = (
            CarSpecification.objects
            .filter(make__iexact=brand_name)
            .exclude(model='')
            .values_list('model', flat=True)
            .distinct()
        )
        model_name = None
        for m in all_models:
            if slugify(m) == model_slug:
                model_name = m
                break

        if not model_name:
            return Response({'error': 'Model not found'}, status=404)

        # Get all specs (trims) for this model
        specs = (
            CarSpecification.objects
            .filter(make__iexact=brand_name, model=model_name, article__is_published=True)
            .select_related('article')
            .order_by('-article__created_at')
        )

        if not specs.exists():
            return Response({'error': 'No published articles for this model'}, status=404)

        # Build trim variants
        trims = []
        images = []
        for spec in specs:
            image = _get_image_url(spec.article, request)
            if image and image not in images:
                images.append(image)

            trims.append({
                'trim': spec.trim if spec.trim and spec.trim != 'Not specified' else 'Standard',
                'engine': spec.engine or '',
                'horsepower': spec.horsepower or '',
                'torque': spec.torque or '',
                'zero_to_sixty': spec.zero_to_sixty or '',
                'top_speed': spec.top_speed or '',
                'drivetrain': spec.drivetrain or '',
                'price': spec.price or '',
                'release_date': spec.release_date or '',
                'article_id': spec.article.id,
                'article_title': spec.article.title,
                'article_slug': spec.article.slug,
            })

        # Get related articles (by brand tag)
        related_articles = (
            Article.objects
            .filter(
                is_published=True,
                tags__slug=slugify(brand_name),
            )
            .exclude(
                id__in=[s.article.id for s in specs]
            )
            .order_by('-created_at')[:5]
            .values('id', 'title', 'slug', 'created_at')
        )

        # Primary spec (first/newest one)
        primary = specs.first()
        price_date = ''
        if primary.price and primary.article.created_at:
            price_date = primary.article.created_at.strftime('%b %Y')

        # Get all VehicleSpecs trims for this car model
        vehicle_specs_list = []
        try:
            from .models import VehicleSpecs
            all_vs = VehicleSpecs.objects.filter(
                make__iexact=brand_name,
                model_name__iexact=model_name,
            ).order_by('trim_name')
            
            # Fallback: if no make/model match, try via primary article
            if not all_vs.exists() and primary:
                all_vs = VehicleSpecs.objects.filter(article=primary.article)
            
            for vs in all_vs:
                vehicle_specs_list.append({
                    'id': vs.id,
                    'trim_name': vs.trim_name or 'Standard',
                    'make': vs.make,
                    'model_name': vs.model_name,
                    'drivetrain': vs.get_drivetrain_display() if vs.drivetrain else None,
                    'motor_count': vs.motor_count,
                    'motor_placement': vs.motor_placement,
                    'power_hp': vs.power_hp,
                    'power_kw': vs.power_kw,
                    'power_display': vs.get_power_display(),
                    'torque_nm': vs.torque_nm,
                    'acceleration_0_100': vs.acceleration_0_100,
                    'top_speed_kmh': vs.top_speed_kmh,
                    'battery_kwh': vs.battery_kwh,
                    'range_km': vs.range_km,
                    'range_wltp': vs.range_wltp,
                    'range_epa': vs.range_epa,
                    'range_cltc': vs.range_cltc,
                    'combined_range_km': vs.combined_range_km,
                    'range_display': vs.get_range_display(),
                    'charging_time_fast': vs.charging_time_fast,
                    'charging_time_slow': vs.charging_time_slow,
                    'charging_power_max_kw': vs.charging_power_max_kw,
                    'transmission': vs.get_transmission_display() if vs.transmission else None,
                    'body_type': vs.get_body_type_display() if vs.body_type else None,
                    'fuel_type': vs.get_fuel_type_display() if vs.fuel_type else None,
                    'seats': vs.seats,
                    'length_mm': vs.length_mm,
                    'width_mm': vs.width_mm,
                    'height_mm': vs.height_mm,
                    'wheelbase_mm': vs.wheelbase_mm,
                    'weight_kg': vs.weight_kg,
                    'cargo_liters': vs.cargo_liters,
                    'cargo_liters_max': vs.cargo_liters_max,
                    'ground_clearance_mm': vs.ground_clearance_mm,
                    'towing_capacity_kg': vs.towing_capacity_kg,
                    'price_from': vs.price_from,
                    'price_to': vs.price_to,
                    'currency': vs.currency,
                    'price_usd_from': vs.price_usd_from,
                    'price_usd_to': vs.price_usd_to,
                    'price_updated_at': vs.price_updated_at.strftime('%b %Y') if vs.price_updated_at else None,
                    'price_display': vs.get_price_display(),
                    'year': vs.year,
                    'country_of_origin': vs.country_of_origin,
                    'platform': vs.platform,
                    'voltage_architecture': vs.voltage_architecture,
                    'suspension_type': vs.suspension_type,
                    'extra_specs': vs.extra_specs or {},
                })
        except Exception:
            pass

        return Response({
            'brand': brand_name,
            'brand_slug': brand_slug,
            'model': model_name,
            'model_slug': model_slug,
            'full_name': f"{brand_name} {model_name}",
            'specs': {
                'engine': primary.engine or '',
                'horsepower': primary.horsepower or '',
                'torque': primary.torque or '',
                'zero_to_sixty': primary.zero_to_sixty or '',
                'top_speed': primary.top_speed or '',
                'drivetrain': primary.drivetrain or '',
                'price': primary.price or '',
                'price_date': price_date,
                'release_date': primary.release_date or '',
            },
            'vehicle_specs': vehicle_specs_list[0] if vehicle_specs_list else None,
            'vehicle_specs_list': vehicle_specs_list,
            'images': images,
            'trims': trims,
            'related_articles': list(related_articles),
        })


class BrandCleanupView(APIView):
    """POST /api/v1/cars/cleanup/ — Run brand normalization (admin only).
    
    Query params:
        ?apply=true  — Apply changes (default: dry run)
    """
    from rest_framework.permissions import IsAdminUser
    permission_classes = [IsAdminUser]

    # Brand rename rules
    BRAND_RENAMES = {
        'DongFeng VOYAH': 'VOYAH',
        'Dongfeng VOYAH': 'VOYAH',
        'dongfeng voyah': 'VOYAH',
        'Zeekr': 'ZEEKR',
        'zeekr': 'ZEEKR',
    }

    RUSSIAN_TO_ENGLISH = {
        'передняя': 'front',
        'задняя': 'rear',
        'многорычажная': 'multi-link',
        'независимая': 'independent',
        'пневматическая': 'air',
        'подвеска': 'suspension',
        'мин': 'min',
        'ч': 'h',
        'часов': 'hours',
        'часа': 'hours',
        'минут': 'min',
    }

    def post(self, request):
        from .models import VehicleSpecs
        apply = request.query_params.get('apply', '').lower() == 'true'
        report = {'mode': 'APPLIED' if apply else 'DRY RUN', 'brand_renames': [], 'text_fixes': []}

        # 1. Fix brand names
        for old_make, new_make in self.BRAND_RENAMES.items():
            cs_count = CarSpecification.objects.filter(make=old_make).count()
            vs_count = VehicleSpecs.objects.filter(make=old_make).count()
            if cs_count > 0 or vs_count > 0:
                report['brand_renames'].append({
                    'old': old_make, 'new': new_make,
                    'car_specs': cs_count, 'vehicle_specs': vs_count,
                })
                if apply:
                    CarSpecification.objects.filter(make=old_make).update(make=new_make)
                    VehicleSpecs.objects.filter(make=old_make).update(make=new_make)

        # 2. Fix Russian text
        text_fields = ['trim_name', 'suspension_type', 'motor_placement',
                       'charging_time_fast', 'charging_time_slow', 'platform', 'transmission']

        for spec in VehicleSpecs.objects.all():
            changes = {}
            for field in text_fields:
                value = getattr(spec, field) or ''
                if not value:
                    continue
                new_value = value
                for ru, en in self.RUSSIAN_TO_ENGLISH.items():
                    if ru in new_value:
                        new_value = new_value.replace(ru, en).strip()
                new_value = ' '.join(new_value.split()).strip(' —-,;')
                if new_value != value:
                    changes[field] = {'old': value, 'new': new_value}

            if changes:
                report['text_fixes'].append({
                    'id': spec.id,
                    'car': f"{spec.make} {spec.model_name} {spec.trim_name}",
                    'changes': changes,
                })
                if apply:
                    for field, vals in changes.items():
                        setattr(spec, field, vals['new'])
                    spec.save(update_fields=list(changes.keys()))

        # 3. Brand summary
        brands = list(
            CarSpecification.objects.exclude(make='')
            .values_list('make', flat=True).distinct().order_by('make')
        )
        report['current_brands'] = brands
        report['total_fixes'] = len(report['brand_renames']) + len(report['text_fixes'])

        return Response(report)


class BrandViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD for Brands + merge action.
    
    GET    /api/v1/admin/brands/        — List all brands (incl. hidden)
    POST   /api/v1/admin/brands/        — Create brand
    PATCH  /api/v1/admin/brands/{id}/   — Edit brand
    DELETE /api/v1/admin/brands/{id}/   — Delete brand
    POST   /api/v1/admin/brands/{id}/merge/ — Merge another brand into this one
    """
    serializer_class = BrandSerializer
    permission_classes = [IsAdminUser]
    queryset = Brand.objects.all()

    def get_queryset(self):
        qs = Brand.objects.select_related('parent').prefetch_related('sub_brands')
        # Allow filtering
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        visible = self.request.query_params.get('visible')
        if visible is not None:
            qs = qs.filter(is_visible=visible.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        """Auto-generate slug if not provided."""
        name = serializer.validated_data.get('name', '')
        slug = serializer.validated_data.get('slug')
        if not slug:
            slug = slugify(name)
            # Ensure unique
            base_slug = slug
            counter = 1
            while Brand.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
        serializer.save(slug=slug)
        # Invalidate cache
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()

    def perform_update(self, serializer):
        """Auto-update slug if name changed and slug not explicitly set."""
        instance = serializer.instance
        new_name = serializer.validated_data.get('name', instance.name)
        new_slug = serializer.validated_data.get('slug')
        
        if new_name != instance.name and not new_slug:
            new_slug = slugify(new_name)
            base_slug = new_slug
            counter = 1
            while Brand.objects.filter(slug=new_slug).exclude(pk=instance.pk).exists():
                new_slug = f"{base_slug}-{counter}"
                counter += 1
            serializer.save(slug=new_slug)
        else:
            serializer.save()
        # Invalidate cache
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()

    def perform_destroy(self, instance):
        instance.delete()
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()

    @action(detail=True, methods=['post'], url_path='merge')
    def merge(self, request, pk=None):
        """
        Merge another brand into this one.
        
        POST /api/v1/admin/brands/{target_id}/merge/
        Body: { "source_brand_id": <id_of_brand_to_merge> }
        
        What happens:
        1. All CarSpecification.make matching source → renamed to target
        2. BrandAlias created: source.name → target.name
        3. Sub-brands of source → re-parented to target
        4. Source brand is deleted
        """
        target_brand = self.get_object()
        source_id = request.data.get('source_brand_id')
        
        if not source_id:
            return Response(
                {'error': 'source_brand_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            source_brand = Brand.objects.get(pk=source_id)
        except Brand.DoesNotExist:
            return Response(
                {'error': f'Brand with id {source_id} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if source_brand.pk == target_brand.pk:
            return Response(
                {'error': 'Cannot merge a brand into itself'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # 1. Rename CarSpecification.make from source to target
        updated_count = CarSpecification.objects.filter(
            make__iexact=source_brand.name
        ).update(make=target_brand.name)
        
        # 2. Create BrandAlias for future reference
        BrandAlias.objects.get_or_create(
            alias=source_brand.name,
            defaults={'canonical_name': target_brand.name},
        )
        
        # 3. Re-parent sub-brands
        source_brand.sub_brands.update(parent=target_brand)
        
        # 4. Delete source brand
        source_name = source_brand.name
        source_brand.delete()
        
        # Invalidate cache
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()
        
        return Response({
            'success': True,
            'message': f'Merged "{source_name}" into "{target_brand.name}"',
            'specs_updated': updated_count,
        })

    @action(detail=False, methods=['post'], url_path='sync')
    def sync_from_specs(self, request):
        """
        Sync brands from CarSpecification — create missing Brand records.
        Useful after importing new articles.
        
        POST /api/v1/admin/brands/sync/
        """
        makes = (
            CarSpecification.objects
            .exclude(make='')
            .exclude(make='Not specified')
            .values_list('make', flat=True)
            .distinct()
        )
        
        created = []
        for make in makes:
            # Resolve through aliases
            canonical = BrandAlias.resolve(make)
            if not Brand.objects.filter(name__iexact=canonical).exists():
                slug = slugify(canonical)
                base_slug = slug
                counter = 1
                while Brand.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                Brand.objects.create(name=canonical, slug=slug)
                created.append(canonical)
        
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()
        
        return Response({
            'success': True,
            'created_brands': created,
            'total_created': len(created),
        })
