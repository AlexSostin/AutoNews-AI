"""
Car Catalog package — split from the monolithic cars_views.py.

Structure:
  cars/
    utils.py          — Shared helpers (get_image_url, serialize_vehicle_specs)
    public_views.py   — Public API (brands list, brand detail, model detail)
    compare_views.py  — Compare + Picker
    admin_views.py    — BrandViewSet, BrandCleanupView (admin CRUD)
"""
from .public_views import CarBrandsListView, CarBrandDetailView, CarModelDetailView
from .compare_views import CarCompareView, CarPickerListView
from .admin_views import BrandCleanupView, BrandViewSet
from .utils import get_image_url, serialize_vehicle_specs

# Backward compatibility aliases (old code uses _get_image_url)
_get_image_url = get_image_url
_serialize_vehicle_specs = serialize_vehicle_specs

__all__ = [
    'CarBrandsListView',
    'CarBrandDetailView',
    'CarModelDetailView',
    'CarCompareView',
    'CarPickerListView',
    'BrandCleanupView',
    'BrandViewSet',
    'get_image_url',
    'serialize_vehicle_specs',
    '_get_image_url',
    '_serialize_vehicle_specs',
]
