from rest_framework import viewsets, status, filters
from django.db.models import Avg, Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission, AllowAny, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from ..models import (
    Article, Category, Tag, TagGroup, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber, NewsletterHistory,
    YouTubeChannel, RSSFeed, RSSNewsItem, PendingArticle, AdminNotification,
    VehicleSpecs, NewsletterSubscriber, BrandAlias, AutomationSettings
)
from ..serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, TagGroupSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer, SubscriberSerializer, NewsletterHistorySerializer,
    YouTubeChannelSerializer, RSSFeedSerializer, RSSNewsItemSerializer, PendingArticleSerializer,
    AdminNotificationSerializer, VehicleSpecsSerializer, BrandAliasSerializer,
    AutomationSettingsSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)



class CarSpecificationViewSet(viewsets.ModelViewSet):
    queryset = CarSpecification.objects.select_related('article').all()
    serializer_class = CarSpecificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None  # Return all specs (no global PAGE_SIZE limit)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['make', 'model', 'trim', 'model_name', 'engine', 'article__title']
    ordering_fields = ['make', 'model', 'price', 'horsepower']
    ordering = ['make', 'model']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def re_extract(self, request, pk=None):
        """Re-run AI/regex spec extraction for an existing CarSpecification.
        POST /api/v1/car-specifications/{id}/re_extract/
        """
        spec = self.get_object()
        article = spec.article

        try:
            from news.spec_extractor import extract_specs_from_content, save_specs_for_article
            specs = extract_specs_from_content(article)
            if specs and specs.get('make') and specs['make'] != 'Not specified':
                result = save_specs_for_article(article, specs)
                if result:
                    serializer = self.get_serializer(result)
                    return Response({
                        'success': True,
                        'message': f'Re-extracted: {result.make} {result.model}',
                        'spec': serializer.data,
                    })
            return Response({
                'success': False,
                'message': 'Could not extract specs from article content',
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Re-extract failed for spec {pk}: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def extract_for_article(self, request):
        """Create/update CarSpecification from an article ID.
        POST /api/v1/car-specifications/extract_for_article/
        Body: { "article_id": 86 }
        """
        article_id = request.data.get('article_id')
        if not article_id:
            return Response({'success': False, 'message': 'article_id is required'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            article = Article.objects.get(id=article_id, is_published=True)
        except Article.DoesNotExist:
            return Response({'success': False, 'message': 'Article not found or not published'},
                          status=status.HTTP_404_NOT_FOUND)

        try:
            from news.spec_extractor import extract_specs_from_content, save_specs_for_article
            specs = extract_specs_from_content(article)
            if specs and specs.get('make') and specs['make'] != 'Not specified':
                result = save_specs_for_article(article, specs)
                if result:
                    serializer = self.get_serializer(result)
                    return Response({
                        'success': True,
                        'created': not CarSpecification.objects.filter(
                            article=article).exclude(id=result.id).exists(),
                        'message': f'Extracted: {result.make} {result.model}',
                        'spec': serializer.data,
                    })
            return Response({
                'success': False,
                'message': 'Could not extract specs from article content',
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Extract specs failed for article {article_id}: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BrandAliasViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing brand aliases (name normalizations)."""
    queryset = BrandAlias.objects.all()
    serializer_class = BrandAliasSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    ordering = ['canonical_name', 'alias']

class VehicleSpecsViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing detailed vehicle specifications (multi-trim)."""
    queryset = VehicleSpecs.objects.select_related('article').all()
    serializer_class = VehicleSpecsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['make', 'model_name', 'trim_name', 'article__title']
    ordering = ['make', 'model_name', 'trim_name']

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def ai_fill(self, request):
        """Extract vehicle specs from pasted text using Gemini AI.
        POST /api/v1/vehicle-specs/ai_fill/
        Body: { "text": "...specs text...", "article_id": 123 (optional) }
        Returns parsed specs as JSON ready to save.
        """
        text = request.data.get('text', '').strip()
        article_id = request.data.get('article_id')

        if not text:
            return Response({'success': False, 'message': 'Text is required'},
                          status=status.HTTP_400_BAD_REQUEST)

        if len(text) < 20:
            return Response({'success': False, 'message': 'Text too short for extraction'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Build the extraction prompt
        system_prompt = """You are a precise vehicle specification extractor. 
Extract ONLY factual data from the provided text. If a value is not mentioned, use null.
Return ONLY valid JSON with no markdown, no code fences, no explanation.
CRITICAL: If the text contains MULTIPLE trims/variants of the same car, return a JSON ARRAY with one object per trim."""

        extraction_prompt = f"""Extract vehicle specifications from this text and return as JSON.

TEXT:
{text[:12000]}

For EACH trim/variant found, return an object with this structure (use null for unknown values):
{{
    "make": "brand name like Zeekr, BMW, Tesla" or null,
    "model_name": "model like 007 GT, iX3, Model 3" or null,
    "trim_name": "trim/variant like RWD 75 kWh, Long Range AWD, Performance" or null,
    "drivetrain": "FWD" or "RWD" or "AWD" or "4WD" or null,
    "motor_count": integer or null,
    "motor_placement": "front" or "rear" or "front+rear" or null,
    "power_hp": integer or null,
    "power_kw": integer or null,
    "torque_nm": integer or null,
    "acceleration_0_100": float (seconds) or null,
    "top_speed_kmh": integer or null,
    "battery_kwh": float or null,
    "range_km": integer or null,
    "range_wltp": integer or null,
    "range_epa": integer or null,
    "range_cltc": integer or null,
    "charging_time_fast": "string like '11 min 10-80%'" or null,
    "charging_time_slow": "string" or null,
    "charging_power_max_kw": integer or null,
    "transmission": "automatic" or "manual" or "CVT" or "single-speed" or "dual-clutch" or null,
    "transmission_gears": integer or null,
    "body_type": "sedan" or "SUV" or "hatchback" or "coupe" or "truck" or "crossover" or "wagon" or "shooting_brake" or "van" or "convertible" or "pickup" or "liftback" or "fastback" or "MPV" or "roadster" or "cabriolet" or "targa" or "limousine" or null,
    "fuel_type": "EV" or "Hybrid" or "PHEV" or "Gas" or "Diesel" or "Hydrogen" or null,
    "seats": integer or null,
    "length_mm": integer or null,
    "width_mm": integer or null,
    "height_mm": integer or null,
    "wheelbase_mm": integer or null,
    "weight_kg": integer or null,
    "cargo_liters": integer or null,
    "cargo_liters_max": integer (with seats folded) or null,
    "ground_clearance_mm": integer or null,
    "towing_capacity_kg": integer or null,
    "price_from": integer (starting price in local currency) or null,
    "price_to": integer or null,
    "currency": "USD" or "EUR" or "CNY" or "RUB" or "GBP" or "JPY" or null,
    "year": integer or null,
    "model_year": integer or null,
    "country_of_origin": "string" or null,
    "platform": "string like SEA, MEB, E-GMP" or null,
    "voltage_architecture": integer (e.g. 400, 800) or null,
    "suspension_type": "string" or null,
    "extra_specs": {{}} or object with any additional specs not covered above
}}

RULES:
- If the text describes MULTIPLE trims/variants, return a JSON ARRAY: [ {{...}}, {{...}}, ... ]
- If the text describes ONLY ONE car/trim, return a SINGLE JSON object: {{...}}
- Always fill make, model_name, and trim_name from context
- CRITICAL: ALL text values MUST be in English. If the source text is in Russian, Chinese, or any other language, you MUST translate ALL field values to English. Examples:
  - "передняя — McPherson; задняя — многорычажная" → "Front: McPherson; Rear: Multi-link"
  - "Топ с дроном" → "Top with Drone"
  - "Базовая" → "Base"
  - "одноступенчатая" → "single-speed"
  - Do NOT leave ANY Cyrillic, Chinese, or other non-Latin characters in any field value
- Convert all measurements to the units specified (mm, km, kg, kW, HP, Nm, etc.)
- For prices: keep the original currency in price_from/price_to/currency fields. Additionally, add these estimated conversion fields:
  - "price_usd_est": estimated price in USD (integer, approximate conversion)
  - "price_eur_est": estimated price in EUR (integer, approximate conversion)
- Extract ALL available fields, not just a few — be thorough
- Return ONLY the JSON, nothing else"""

        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result = provider.generate_completion(
                extraction_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=8000,
            )

            # Parse the JSON response
            import json
            import re
            # Clean up potential markdown code fences
            cleaned = result.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)

            # Normalize to list (single object → [object])
            specs_list = parsed if isinstance(parsed, list) else [parsed]

            # If article_id provided, save all trims
            if article_id:
                try:
                    article = Article.objects.get(id=article_id)
                    # Auto-populate make/model from CarSpecification
                    from news.models import CarSpecification
                    cs_make, cs_model = None, None
                    try:
                        cs = CarSpecification.objects.get(article=article)
                        if cs.make and cs.make != 'Not specified':
                            cs_make = cs.make
                        if cs.model and cs.model != 'Not specified':
                            cs_model = cs.model
                    except CarSpecification.DoesNotExist:
                        pass

                    saved_specs = []
                    for specs_data in specs_list:
                        if cs_make:
                            specs_data.setdefault('make', cs_make)
                        if cs_model:
                            specs_data.setdefault('model_name', cs_model)

                        # Move estimated prices to extra_specs (not model fields)
                        extra = specs_data.get('extra_specs') or {}
                        for price_key in ('price_usd_est', 'price_eur_est'):
                            if price_key in specs_data and specs_data[price_key]:
                                extra[price_key] = specs_data.pop(price_key)
                        if extra:
                            specs_data['extra_specs'] = extra

                        # Build lookup — use make+model+trim if available
                        defaults = {k: v for k, v in specs_data.items() if v is not None}
                        defaults['article'] = article
                        if specs_data.get('make') and specs_data.get('model_name') and specs_data.get('trim_name'):
                            lookup = {
                                'make': specs_data['make'],
                                'model_name': specs_data['model_name'],
                                'trim_name': specs_data['trim_name'],
                            }
                        else:
                            lookup = {'article': article}

                        vehicle_spec, created = VehicleSpecs.objects.update_or_create(
                            **lookup,
                            defaults=defaults,
                        )
                        saved_specs.append({
                            'id': vehicle_spec.id,
                            'trim': specs_data.get('trim_name', ''),
                            'created': created,
                        })

                    return Response({
                        'success': True,
                        'message': f'Extracted {len(specs_list)} trim(s), saved to article #{article_id}',
                        'saved': saved_specs,
                        'extracted': specs_list,
                    })
                except Article.DoesNotExist:
                    return Response({
                        'success': True,
                        'message': f'Extracted {len(specs_list)} trim(s) (article not found, not saved)',
                        'extracted': specs_list,
                    })

            return Response({
                'success': True,
                'message': f'Extracted {len(specs_list)} trim(s) successfully',
                'extracted': specs_list,
            })

        except json.JSONDecodeError as e:
            logger.error(f'AI Fill JSON parse error: {e}, raw: {result[:500]}')
            return Response({
                'success': False,
                'message': f'AI returned invalid JSON: {str(e)}',
                'raw_response': result[:1000],
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.error(f'AI Fill failed: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def save_specs(self, request, pk=None):
        """Save/update specific fields for a VehicleSpec.
        POST /api/v1/vehicle-specs/{id}/save_specs/
        Body: { field_name: value, ... }
        """
        vehicle_spec = self.get_object()
        serializer = self.get_serializer(vehicle_spec, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Specs saved successfully',
                'specs': serializer.data,
            })
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

