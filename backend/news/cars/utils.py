"""
Car Catalog — utility functions shared across car views.
"""
from django.utils.text import slugify


def get_image_url(article, request=None):
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
    if request:
        return request.build_absolute_uri(relative)
    return relative


def serialize_vehicle_specs(vs):
    """Serialize a VehicleSpecs instance for compare / detail views."""
    return {
        'id': vs.id,
        'make': vs.make,
        'model_name': vs.model_name,
        'trim_name': vs.trim_name or 'Standard',
        'full_name': f"{vs.make} {vs.model_name}".strip(),
        'drivetrain': vs.get_drivetrain_display() if vs.drivetrain else None,
        'motor_count': vs.motor_count,
        'motor_placement': vs.motor_placement,
        'power_hp': vs.power_hp,
        'power_kw': vs.power_kw,
        'torque_nm': vs.torque_nm,
        'acceleration_0_100': vs.acceleration_0_100,
        'top_speed_kmh': vs.top_speed_kmh,
        'battery_kwh': vs.battery_kwh,
        'range_km': vs.range_km,
        'range_wltp': vs.range_wltp,
        'range_epa': vs.range_epa,
        'range_cltc': vs.range_cltc,
        'combined_range_km': vs.combined_range_km,
        'charging_time_fast': vs.charging_time_fast,
        'charging_time_slow': vs.charging_time_slow,
        'charging_power_max_kw': vs.charging_power_max_kw,
        'transmission': vs.get_transmission_display() if vs.transmission else None,
        'transmission_gears': vs.transmission_gears,
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
        'year': vs.year,
        'country_of_origin': vs.country_of_origin,
        'platform': vs.platform,
        'voltage_architecture': vs.voltage_architecture,
        'suspension_type': vs.suspension_type,
        'extra_specs': vs.extra_specs or {},
        'article_id': vs.article_id,
    }
