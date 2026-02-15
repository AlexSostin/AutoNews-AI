"""
Car Catalog API — read-only endpoints for browsing cars by brand/model.
Data is auto-populated from CarSpecification records attached to articles.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from django.utils.text import slugify
from .models import CarSpecification, Article, Tag


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

    def get(self, request):
        brands = (
            CarSpecification.objects
            .exclude(make='')
            .exclude(make='Not specified')
            .values('make')
            .annotate(
                model_count=Count('model', distinct=True),
                article_count=Count('article', distinct=True),
            )
            .filter(model_count__gt=0)
            .order_by('-article_count')
        )

        result = []
        for b in brands:
            make = b['make']
            # Get first article image as brand thumbnail
            first_spec = (
                CarSpecification.objects
                .filter(make=make, article__is_published=True)
                .select_related('article')
                .first()
            )
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
            .filter(make=brand_name)
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
            .filter(make=brand_name, model=model_name, article__is_published=True)
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
