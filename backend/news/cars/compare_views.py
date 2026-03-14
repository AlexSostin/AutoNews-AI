"""
Car Catalog — compare and picker endpoints.

Endpoints:
  GET /api/v1/cars/compare/?car1=brand/model&car2=brand/model
  GET /api/v1/cars/picker/
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .utils import get_image_url, serialize_vehicle_specs


class CarCompareView(APIView):
    """
    GET /api/v1/cars/compare/?car1={brand}/{model}&car2={brand}/{model}

    Compare two cars side-by-side using VehicleSpecs data.
    Returns specs for both cars + winner highlights for numeric fields.
    """
    permission_classes = [AllowAny]

    # Fields where higher is better
    HIGHER_IS_BETTER = {
        'power_hp', 'power_kw', 'torque_nm', 'top_speed_kmh',
        'battery_kwh', 'range_km', 'range_wltp', 'range_epa', 'range_cltc',
        'combined_range_km', 'charging_power_max_kw', 'seats',
        'cargo_liters', 'cargo_liters_max', 'ground_clearance_mm',
        'towing_capacity_kg', 'voltage_architecture', 'wheelbase_mm',
    }

    # Fields where lower is better
    LOWER_IS_BETTER = {
        'acceleration_0_100', 'weight_kg', 'price_usd_from',
    }

    def _find_vehicle_specs(self, car_path):
        """
        Find the best VehicleSpecs for a car path like 'bmw/ix3'.
        Returns (VehicleSpecs, article_image_url) or (None, None).
        """
        from ..models import VehicleSpecs

        parts = car_path.strip('/').split('/')
        if len(parts) != 2:
            return None, None

        brand_slug, model_slug = parts

        # Find matching make
        all_makes = (
            VehicleSpecs.objects
            .exclude(make='')
            .values_list('make', flat=True)
            .distinct()
        )
        make_name = None
        for make in all_makes:
            if slugify(make) == brand_slug:
                make_name = make
                break

        if not make_name:
            return None, None

        # Find matching model
        all_models = (
            VehicleSpecs.objects
            .filter(make__iexact=make_name)
            .exclude(model_name='')
            .values_list('model_name', flat=True)
            .distinct()
        )
        model_name = None
        for m in all_models:
            if slugify(m) == model_slug:
                model_name = m
                break

        if not model_name:
            return None, None

        # Get the best (most complete) VehicleSpecs
        vs = (
            VehicleSpecs.objects
            .filter(make__iexact=make_name, model_name__iexact=model_name)
            .select_related('article')
            .order_by('-id')
            .first()
        )

        # Get image
        image = None
        if vs and vs.article:
            image = get_image_url(vs.article, self.request)

        return vs, image

    def get(self, request):
        car1_path = request.query_params.get('car1', '')
        car2_path = request.query_params.get('car2', '')

        if not car1_path or not car2_path:
            return Response(
                {'error': 'Both car1 and car2 query params required (format: brand/model)'},
                status=400
            )

        vs1, img1 = self._find_vehicle_specs(car1_path)
        vs2, img2 = self._find_vehicle_specs(car2_path)

        if not vs1:
            return Response({'error': f'Car not found: {car1_path}'}, status=404)
        if not vs2:
            return Response({'error': f'Car not found: {car2_path}'}, status=404)

        spec1 = serialize_vehicle_specs(vs1)
        spec2 = serialize_vehicle_specs(vs2)

        spec1['image'] = img1
        spec2['image'] = img2

        # Add article slug for linking
        if vs1.article:
            spec1['article_slug'] = vs1.article.slug
        if vs2.article:
            spec2['article_slug'] = vs2.article.slug

        # Calculate winners
        winners = {}
        for field in self.HIGHER_IS_BETTER | self.LOWER_IS_BETTER:
            v1 = spec1.get(field)
            v2 = spec2.get(field)
            if v1 is not None and v2 is not None:
                try:
                    v1_num = float(v1)
                    v2_num = float(v2)
                    if v1_num == v2_num:
                        winners[field] = 'tie'
                    elif field in self.HIGHER_IS_BETTER:
                        winners[field] = 'car1' if v1_num > v2_num else 'car2'
                    else:
                        winners[field] = 'car1' if v1_num < v2_num else 'car2'
                except (ValueError, TypeError):
                    pass

        return Response({
            'car1': spec1,
            'car2': spec2,
            'winners': winners,
        })


class CarPickerListView(APIView):
    """
    GET /api/v1/cars/picker/ — List all brands with their models for the compare picker.
    Lightweight endpoint returning just {brand, slug, models: [{name, slug}]}.
    """
    permission_classes = [AllowAny]

    @method_decorator(cache_page(600, key_prefix='cars_picker'))  # Cache for 10 minutes
    def get(self, request):
        from ..models import VehicleSpecs
        from django.db.models import Q

        # Only include vehicles that have at least some meaningful spec data
        # (power, battery, or range) — otherwise they're useless for comparison
        has_specs = (
            Q(power_hp__isnull=False) |
            Q(battery_kwh__isnull=False) |
            Q(range_wltp__isnull=False) |
            Q(range_km__isnull=False) |
            Q(acceleration_0_100__isnull=False)
        )

        # Get all unique make/model combinations with specs
        combos = (
            VehicleSpecs.objects
            .filter(has_specs)
            .exclude(make='')
            .exclude(model_name='')
            .values('make', 'model_name')
            .distinct()
            .order_by('make', 'model_name')
        )

        # Group by slugified make to avoid case-variant duplicates
        # (e.g. 'Zeekr' and 'ZEEKR' both become slug 'zeekr')
        brands = {}
        for combo in combos:
            make = combo['make']
            model = combo['model_name']
            brand_slug = slugify(make)

            if brand_slug not in brands:
                brands[brand_slug] = {
                    'name': make,
                    'slug': brand_slug,
                    'models': [],
                    '_model_slugs': set(),  # dedup tracker
                }
            model_slug = slugify(model)
            if model_slug not in brands[brand_slug]['_model_slugs']:
                brands[brand_slug]['_model_slugs'].add(model_slug)
                brands[brand_slug]['models'].append({
                    'name': model,
                    'slug': model_slug,
                })

        # Remove internal dedup tracker before returning
        result = []
        for b in sorted(brands.values(), key=lambda x: x['name']):
            result.append({
                'name': b['name'],
                'slug': b['slug'],
                'models': b['models'],
            })
        return Response(result)
