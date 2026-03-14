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
import json

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.prompt_sanitizer import sanitize_for_prompt
except ImportError:
    sanitize_for_prompt = lambda text, max_length=15000: text[:max_length]



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
                result = save_specs_for_article(article, specs, force_update=True)
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

    # ─── Deduplication helpers ───────────────────────────────────────────────

    SPEC_FIELDS = ['trim', 'engine', 'horsepower', 'torque',
                   'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'release_date']

    _EMPTY_VALUES = frozenset({
        '', 'not specified', 'none', 'n/a', 'unknown', '-', '—', 'not available',
    })

    def _is_real_value(self, val):
        """Return True only if val contains meaningful data (not placeholder strings)."""
        return str(val or '').strip().lower() not in self._EMPTY_VALUES

    def _coverage_score(self, spec):
        """Count how many spec fields have real (non-placeholder) values."""
        return sum(1 for f in self.SPEC_FIELDS if self._is_real_value(getattr(spec, f, '')))

    def _serialize_spec_for_dedup(self, spec):
        """Lightweight serialization for the duplicates response."""
        return {
            'id': spec.id,
            'article': spec.article_id,
            'article_title': spec.article.title if spec.article else '',
            'make': spec.make,
            'model': spec.model,
            'trim': spec.trim,
            'engine': spec.engine,
            'horsepower': spec.horsepower,
            'torque': spec.torque,
            'zero_to_sixty': spec.zero_to_sixty,
            'top_speed': spec.top_speed,
            'drivetrain': spec.drivetrain,
            'price': spec.price,
            'release_date': spec.release_date,
            'is_verified': spec.is_verified,
            'coverage_score': self._coverage_score(spec),
        }

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='duplicates')
    def duplicates(self, request):
        """
        GET /api/v1/car-specifications/duplicates/
        Return groups of CarSpecification records sharing the same make+model
        with 2+ entries. Each group includes coverage scores and suggested master.
        """
        from django.db.models import Count

        # Find make+model combos with 2+ specs
        dupes = (
            CarSpecification.objects
            .exclude(make='').exclude(make='Not specified')
            .values('make', 'model')
            .annotate(count=Count('id'))
            .filter(count__gte=2)
            .order_by('make', 'model')
        )

        hide_verified = request.query_params.get('hide_verified', 'false').lower() == 'true'

        groups = []
        for d in dupes:
            specs = (
                CarSpecification.objects
                .filter(make=d['make'], model=d['model'])
                .select_related('article')
                .order_by('id')
            )
            # Skip groups that already have a verified master (Variant 3 UX filter)
            if hide_verified and specs.filter(is_verified=True).exists():
                continue

            records = [self._serialize_spec_for_dedup(s) for s in specs]
            # Suggest master = verified record first, then highest coverage score
            verified = [r for r in records if r['is_verified']]
            best = verified[0] if verified else max(records, key=lambda r: r['coverage_score'])
            groups.append({
                'make': d['make'],
                'model': d['model'],
                'count': d['count'],
                'has_verified': bool(verified),
                'suggested_master_id': best['id'],
                'records': records,
            })

        return Response({
            'total_groups': len(groups),
            'groups': groups,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='merge')
    def merge(self, request):
        """
        POST /api/v1/car-specifications/merge/
        Body: { "master_id": int, "delete_ids": [int, ...] }

        Takes master record. For each field in SPEC_FIELDS: if master is empty
        and any of the deleted records has a value, fill master from the one with
        highest coverage (best data wins). Then deletes the specified records.
        """
        master_id = request.data.get('master_id')
        delete_ids = request.data.get('delete_ids', [])

        if not master_id:
            return Response({'error': 'master_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not delete_ids:
            return Response({'error': 'delete_ids must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            master = CarSpecification.objects.select_related('article').get(id=master_id)
        except CarSpecification.DoesNotExist:
            return Response({'error': f'Master spec {master_id} not found'}, status=status.HTTP_404_NOT_FOUND)

        others = list(CarSpecification.objects.filter(id__in=delete_ids).select_related('article'))
        if not others:
            return Response({'error': 'No valid delete_ids found'}, status=status.HTTP_404_NOT_FOUND)

        # Merge: fill empty fields on master from the best source
        # Sort others by coverage score desc so we pick the richest donor first
        others_sorted = sorted(others, key=self._coverage_score, reverse=True)
        updated_fields = []
        for field in self.SPEC_FIELDS:
            if not getattr(master, field, ''):
                for donor in others_sorted:
                    donor_val = getattr(donor, field, '')
                    if donor_val:
                        setattr(master, field, donor_val)
                        updated_fields.append(field)
                        break  # stop at first non-empty donor

        # Fill empty fields from donors and prepare save fields list
        all_save_fields = list(updated_fields)

        # Auto-verify master — human reviewed and confirmed the merge
        from django.utils import timezone
        master.is_verified = True
        master.verified_at = timezone.now()
        all_save_fields += ['is_verified', 'verified_at']

        master.save(update_fields=all_save_fields)

        # Delete the duplicates
        deleted_count = CarSpecification.objects.filter(id__in=delete_ids).delete()[0]

        logger.info(
            f'Merged CarSpec: master={master_id} '
            f'absorbed {deleted_count} duplicate(s) for {master.make} {master.model}. '
            f'Fields filled from donors: {updated_fields or "none"}. '
            f'Master auto-verified.'
        )

        serializer = self.get_serializer(master)
        return Response({
            'success': True,
            'message': f'Merged {deleted_count} duplicate(s) into master — {master.make} {master.model} ✓ verified',
            'fields_filled': updated_fields,
            'master': serializer.data,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='ai-pick')
    def ai_pick(self, request):
        """
        POST /api/v1/car-specifications/ai-pick/
        Body: { "spec_ids": [9, 35, 98] }

        Calls Gemini to review all spec records in the group and return the best
        value for each field with reasoning. Does NOT mutate any data.

        Response:
        {
            "make": "BYD",
            "model": "Leopard 5",
            "suggested_master_id": 9,
            "best_fields": {
                "engine": { "value": "PHEV / 31.8 kWh / AWD", "from_id": 9, "reason": "Consistent across 2 sources" },
                "horsepower": { "value": "677 HP", "from_id": 9, "reason": "55 HP in #98 is likely OCR error" },
                ...
            }
        }
        """
        spec_ids = request.data.get('spec_ids', [])
        if not spec_ids or len(spec_ids) < 2:
            return Response({'error': 'spec_ids must contain at least 2 IDs'},
                            status=status.HTTP_400_BAD_REQUEST)

        specs = list(
            CarSpecification.objects.filter(id__in=spec_ids).select_related('article')
        )
        if len(specs) < 2:
            return Response({'error': 'Not enough specs found'}, status=status.HTTP_404_NOT_FOUND)

        # ── Build prompt ──────────────────────────────────────────────────────
        field_labels = {
            'trim': 'Trim/Version', 'engine': 'Engine', 'horsepower': 'Horsepower',
            'torque': 'Torque', 'zero_to_sixty': '0-60 mph / 0-100 km/h time',
            'top_speed': 'Top Speed', 'drivetrain': 'Drivetrain (AWD/FWD/RWD/4WD)',
            'price': 'Price', 'release_date': 'Release Date',
        }

        car_name = f"{specs[0].make} {specs[0].model}".strip()

        records_text = ''
        for spec in specs:
            records_text += f'\n--- Record ID #{spec.id} (Article: "{(spec.article.title if spec.article else "N/A")[:80]}") ---\n'
            for f, label in field_labels.items():
                val = getattr(spec, f, '') or ''
                records_text += f'  {label}: {val or "(empty)"}\n'

        prompt = f"""You are a car specification expert. I have {len(specs)} duplicate database records for the {car_name}.

Your job: for each spec field, pick the MOST ACCURATE value from these records.

RECORDS:
{records_text}

RULES:
1. Pick the value that is FACTUALLY most accurate for this specific car model
2. If a value looks like an extraction error (e.g. HP that is far off from the model's known specs), reject it and flag it
3. If values differ per trim/variant (e.g. different power levels), prefer the most common or base configuration
4. If a value is "Not specified", "None", or empty — it is meaningless, prefer any real value instead
5. ALL output field values must be in English
6. Return ONLY valid JSON, no prose, no markdown fences

Return this exact JSON structure:
{{
  "suggested_master_id": <int: ID of the record that overall has the best data>,
  "best_fields": {{
    "trim":         {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "engine":       {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "horsepower":   {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "torque":       {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "zero_to_sixty":{{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "top_speed":    {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "drivetrain":   {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "price":        {{ "value": "...", "from_id": <int or null>, "reason": "..." }},
    "release_date": {{ "value": "...", "from_id": <int or null>, "reason": "..." }}
  }}
}}

For "from_id": use the record ID the value came from, or null if the value is synthesized/chosen as empty.
"""

        try:
            from ai_engine.modules.ai_provider import get_ai_provider
            provider = get_ai_provider('gemini')
            result = provider.generate_completion(
                prompt,
                system_prompt='You are a precise automotive data expert. Return only valid JSON.',
                temperature=0.1,
                max_tokens=2000,
            )

            # Strip markdown code fences if present
            cleaned = result.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            parsed = json.loads(cleaned.strip())

            # Validate structure
            if 'best_fields' not in parsed:
                raise ValueError('Missing best_fields in Gemini response')

            return Response({
                'success': True,
                'make': specs[0].make,
                'model': specs[0].model,
                'suggested_master_id': parsed.get('suggested_master_id', specs[0].id),
                'best_fields': parsed['best_fields'],
                'records_reviewed': len(specs),
            })

        except json.JSONDecodeError as e:
            logger.error(f'ai-pick JSON parse error for {car_name}: {e}')
            return Response({
                'success': False,
                'message': 'AI returned invalid JSON. Try again.',
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.error(f'ai-pick failed for {car_name}: {e}')
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

    @action(detail=False, methods=['get'], url_path='brand-tree')
    def brand_tree(self, request):
        """
        GET /api/v1/brand-aliases/brand-tree/
        Returns full brand ownership tree for the intelligence dashboard.
        """
        from ..models import Brand
        from ..serializers import BrandSerializer

        # Get all top-level brands (no parent)
        top_brands = Brand.objects.filter(
            parent__isnull=True
        ).prefetch_related('sub_brands').order_by('name')

        tree = []
        for brand in top_brands:
            children = brand.sub_brands.all().order_by('name')
            article_count = brand.get_article_count()
            # A parent has_content if it or any child has articles
            child_list = []
            children_have_content = False
            for c in children:
                c_count = c.get_article_count()
                if c_count > 0:
                    children_have_content = True
                child_list.append({
                    'id': c.id,
                    'name': c.name,
                    'slug': c.slug,
                    'country': c.country,
                    'website': c.website,
                    'logo_url': c.logo_url,
                    'description': c.description,
                    'article_count': c_count,
                    'has_content': c_count > 0,
                })
            brand_data = {
                'id': brand.id,
                'name': brand.name,
                'slug': brand.slug,
                'country': brand.country,
                'website': brand.website,
                'logo_url': brand.logo_url,
                'description': brand.description,
                'is_parent': len(child_list) > 0,
                'article_count': article_count,
                'has_content': article_count > 0 or children_have_content,
                'children': child_list,
            }
            tree.append(brand_data)

        return Response({
            'total_brands': Brand.objects.count(),
            'total_groups': Brand.objects.filter(
                sub_brands__isnull=False
            ).distinct().count(),
            'tree': tree,
        })

    @action(detail=False, methods=['get'], url_path='brand-audit')
    def brand_audit(self, request):
        """
        GET /api/v1/brand-aliases/brand-audit/
        Scan articles for brand data issues:
        1. unknown_brand — CarSpec.make doesn't match any Brand
        2. stale_alias — CarSpec.make could be normalized via alias
        3. no_spec — published article has no CarSpec at all
        """
        from ..models import Brand

        brand_names = set(
            Brand.objects.values_list('name', flat=True)
        )
        brand_names_lower = {n.lower() for n in brand_names}

        # Pre-load aliases for stale detection (keyed by alias lowercase)
        aliases_by_lower = {}
        for a in BrandAlias.objects.all():
            aliases_by_lower.setdefault(a.alias.lower(), []).append(a)

        issues = []

        # Find articles with CarSpec make not matching any Brand
        specs = CarSpecification.objects.filter(
            article__is_published=True
        ).exclude(
            make=''
        ).exclude(
            make='Not specified'
        ).select_related('article')[:500]

        for spec in specs:
            make_lower = spec.make.lower()
            if make_lower not in brand_names_lower:
                suggestion = BrandAlias.resolve(spec.make) if spec.make else None
                issues.append({
                    'type': 'unknown_brand',
                    'article_id': spec.article_id,
                    'article_title': spec.article.title[:80] if spec.article else '',
                    'current_make': spec.make,
                    'suggestion': suggestion,
                })
            elif make_lower in aliases_by_lower:
                # Check if any alias (without model_prefix constraint) applies
                for alias_obj in aliases_by_lower[make_lower]:
                    if alias_obj.model_prefix:
                        # Only flag if model actually starts with the prefix
                        model_name = spec.model or ''
                        if model_name.lower().startswith(alias_obj.model_prefix.lower()):
                            issues.append({
                                'type': 'stale_alias',
                                'article_id': spec.article_id,
                                'article_title': spec.article.title[:80] if spec.article else '',
                                'current_make': spec.make,
                                'suggestion': alias_obj.canonical_name,
                            })
                            break
                    elif alias_obj.canonical_name != spec.make:
                        issues.append({
                            'type': 'stale_alias',
                            'article_id': spec.article_id,
                            'article_title': spec.article.title[:80] if spec.article else '',
                            'current_make': spec.make,
                            'suggestion': alias_obj.canonical_name,
                        })
                        break

        # Find articles with no CarSpec at all
        articles_without_spec = Article.objects.filter(
            is_published=True
        ).exclude(
            Exists(CarSpecification.objects.filter(article=OuterRef('pk')))
        ).values('id', 'title')[:20]

        for a in articles_without_spec:
            issues.append({
                'type': 'no_spec',
                'article_id': a['id'],
                'article_title': a['title'][:80],
                'current_make': None,
                'suggestion': None,
            })

        return Response({
            'total_issues': len(issues),
            'issues': issues[:50],  # Cap at 50
        })

    @action(detail=False, methods=['post'], url_path='fix-brand')
    def fix_brand(self, request):
        """
        POST /api/v1/brand-aliases/fix-brand/
        Quick-fix a CarSpec's make by resolving through aliases or updating directly.
        Body: { "article_id": 123, "new_make": "Avatr" }  (new_make optional — uses alias resolution if omitted)
        """
        from ..models import Brand

        article_id = request.data.get('article_id')
        new_make = request.data.get('new_make', '').strip()

        if not article_id:
            return Response({'success': False, 'message': 'article_id is required'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            spec = CarSpecification.objects.get(article_id=article_id)
        except CarSpecification.DoesNotExist:
            return Response({'success': False, 'message': 'CarSpec not found'},
                          status=status.HTTP_404_NOT_FOUND)

        old_make = spec.make

        if new_make:
            # Direct assignment
            spec.make = new_make
        else:
            # Try alias resolution
            resolved = BrandAlias.resolve(spec.make)
            if resolved and resolved != spec.make:
                spec.make = resolved
            else:
                return Response({
                    'success': False,
                    'message': f'No alias found for "{spec.make}". Provide new_make explicitly.',
                })

        spec.save(update_fields=['make'])

        return Response({
            'success': True,
            'message': f'Fixed: {old_make} → {spec.make}',
            'old_make': old_make,
            'new_make': spec.make,
        })

    @action(detail=False, methods=['post'], url_path='sync-populate', permission_classes=[IsAdminUser])
    def sync_populate(self, request):
        """
        POST /api/v1/brand-aliases/sync-populate/
        One-click: populate brand hierarchy + sync from specs + auto-merge duplicates.
        """
        from ..models import Brand
        from django.utils.text import slugify
        from django.core.management import call_command
        from io import StringIO

        results = {'populated': 0, 'updated': 0, 'aliases_created': 0, 'merged': 0, 'synced': 0, 'log': []}

        # ── Step 1: Run populate_brand_data management command ──
        try:
            out = StringIO()
            call_command('populate_brand_data', '--force', stdout=out)
            output_text = out.getvalue()
            results['log'].append('✅ Brand data populated')
            # Count results from output
            for line in output_text.split('\n'):
                if 'Created brand' in line:
                    results['populated'] += 1
                elif 'Updated' in line:
                    results['updated'] += 1
                elif 'Alias:' in line:
                    results['aliases_created'] += 1
        except Exception as e:
            results['log'].append(f'⚠️ Populate failed: {str(e)[:200]}')
            logger.error(f'sync-populate: populate_brand_data failed: {e}')

        # ── Step 2: Sync brands from CarSpecification ──
        try:
            known_brands = set(Brand.objects.values_list('name', flat=True))
            known_lower = {n.lower(): n for n in known_brands}
            alias_map = {a.alias.lower(): a.canonical_name for a in BrandAlias.objects.all()}

            spec_makes = (
                CarSpecification.objects
                .exclude(make='')
                .exclude(make='Not specified')
                .values_list('make', flat=True)
                .distinct()
            )
            for make in spec_makes:
                # Resolve through aliases first
                resolved = alias_map.get(make.lower(), make)
                if resolved.lower() not in known_lower:
                    Brand.objects.get_or_create(
                        name=resolved,
                        defaults={'slug': slugify(resolved), 'is_visible': True},
                    )
                    results['synced'] += 1
                    results['log'].append(f'+ Brand from specs: {resolved}')
        except Exception as e:
            results['log'].append(f'⚠️ Sync failed: {str(e)[:200]}')
            logger.error(f'sync-populate: sync failed: {e}')

        # ── Step 3: Auto-merge obvious duplicates ──
        KNOWN_MERGES = [
            ('HUAWEI AVATR', 'Avatr'),
            ('Huawei Avatr', 'Avatr'),
            ('Zeekr (Geely)', 'ZEEKR'),
            ('ZEEKR (Geely)', 'ZEEKR'),
            ('Geely ZEEKR', 'ZEEKR'),
            ('DongFeng VOYAH', 'VOYAH'),
            ('Dongfeng VOYAH', 'VOYAH'),
            ('Great Wall Motors', 'GWM'),
            ('Great Wall', 'GWM'),
        ]
        for source_name, target_name in KNOWN_MERGES:
            try:
                source = Brand.objects.filter(name__iexact=source_name).first()
                target = Brand.objects.filter(name__iexact=target_name).first()
                if source and target and source.id != target.id:
                    # Move CarSpecs from source to target
                    moved = CarSpecification.objects.filter(make__iexact=source.name).update(make=target.name)
                    # Create alias if not exists
                    BrandAlias.objects.get_or_create(
                        alias=source.name,
                        defaults={'canonical_name': target.name},
                    )
                    # Re-parent sub-brands
                    source.sub_brands.update(parent=target)
                    # Delete source brand
                    source.delete()
                    results['merged'] += 1
                    results['log'].append(f'🔀 Merged: {source_name} → {target_name} ({moved} specs moved)')
            except Exception as e:
                results['log'].append(f'⚠️ Merge {source_name}→{target_name} failed: {str(e)[:100]}')

        total_actions = results['populated'] + results['updated'] + results['aliases_created'] + results['merged'] + results['synced']
        return Response({
            'success': True,
            'message': f'Sync complete: {total_actions} actions performed',
            'results': results,
        })

    @action(detail=False, methods=['post'], url_path='normalize-makes', permission_classes=[IsAdminUser])
    def normalize_makes(self, request):
        """
        POST /api/v1/brand-aliases/normalize-makes/
        Normalize all make names in VehicleSpecs and CarSpecification
        using BRAND_DISPLAY_NAMES (e.g. 'Zeekr'/'ZEEKR' → canonical form).
        """
        from news.models.vehicles import normalize_make

        fixed_vehicle_specs = 0
        fixed_car_specs = 0
        changes = []

        # Fix VehicleSpecs
        for vs in VehicleSpecs.objects.exclude(make=''):
            normalized = normalize_make(vs.make)
            if normalized != vs.make:
                changes.append(f'VehicleSpecs #{vs.id}: "{vs.make}" → "{normalized}"')
                VehicleSpecs.objects.filter(id=vs.id).update(make=normalized)
                fixed_vehicle_specs += 1

        # Fix CarSpecification
        for cs in CarSpecification.objects.exclude(make=''):
            normalized = normalize_make(cs.make)
            if normalized != cs.make:
                changes.append(f'CarSpec #{cs.id}: "{cs.make}" → "{normalized}"')
                CarSpecification.objects.filter(id=cs.id).update(make=normalized)
                fixed_car_specs += 1

        total = fixed_vehicle_specs + fixed_car_specs
        return Response({
            'success': True,
            'message': f'Normalized {total} records ({fixed_vehicle_specs} VehicleSpecs, {fixed_car_specs} CarSpecs)',
            'fixed_vehicle_specs': fixed_vehicle_specs,
            'fixed_car_specs': fixed_car_specs,
            'changes': changes[:50],  # cap log at 50 lines
        })

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
{sanitize_for_prompt(text, max_length=12000)}

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

    # ── Comparison endpoints ─────────────────────────────────────────────────

    DATA_HEALTH_FIELDS = [
        'power_hp', 'torque_nm', 'acceleration_0_100', 'top_speed_kmh',
        'battery_kwh', 'range_wltp', 'range_km', 'price_from',
        'length_mm', 'weight_kg', 'cargo_liters', 'drivetrain',
    ]

    def _spec_health(self, spec):
        """Count how many key comparison fields are filled."""
        filled = sum(1 for f in self.DATA_HEALTH_FIELDS if getattr(spec, f, None) is not None)
        return {'filled': filled, 'total': len(self.DATA_HEALTH_FIELDS)}

    def _spec_summary(self, spec):
        """Lightweight spec dict for the pairs response."""
        image_url = None
        try:
            if spec.article and spec.article.image:
                image_url = spec.article.image.url
        except Exception:
            pass
        return {
            'id': spec.id,
            'make': spec.make,
            'model_name': spec.model_name,
            'trim_name': spec.trim_name,
            'body_type': spec.body_type,
            'body_type_display': spec.get_body_type_display() if spec.body_type else None,
            'fuel_type': spec.fuel_type,
            'fuel_type_display': spec.get_fuel_type_display() if spec.fuel_type else None,
            'power_hp': spec.power_hp,
            'battery_kwh': spec.battery_kwh,
            'range_wltp': spec.range_wltp,
            'range_km': spec.range_km,
            'price_from': spec.price_from,
            'price_to': spec.price_to,
            'currency': spec.currency,
            'price_display': spec.get_price_display(),
            'acceleration_0_100': spec.acceleration_0_100,
            'image_url': image_url,
        }

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated],
            url_path='comparison-pairs')
    def comparison_pairs(self, request):
        """
        GET /api/v1/vehicle-specs/comparison-pairs/
        Returns scored vehicle pairs for comparison articles.
        Query params: ?segment=SUV&fuel=EV&brands=BYD,Tesla&limit=30
        """
        from itertools import combinations
        from django.utils.text import slugify

        qs = VehicleSpecs.objects.select_related('article').exclude(make='').exclude(model_name='').filter(
            body_type__isnull=False,
            fuel_type__isnull=False,
        )

        # Apply filters
        segment = request.query_params.get('segment')
        fuel = request.query_params.get('fuel')
        brands = request.query_params.get('brands')
        limit = int(request.query_params.get('limit', 30))

        if segment:
            qs = qs.filter(body_type__iexact=segment)
        if fuel:
            qs = qs.filter(fuel_type__iexact=fuel)

        all_specs = list(qs)
        
        brand_list = []
        if brands:
            brand_list = [b.strip().lower() for b in brands.split(',') if b.strip()]

        # Group by segment
        segments_map = {}
        for spec in all_specs:
            key = (spec.body_type, spec.fuel_type)
            segments_map.setdefault(key, []).append(spec)

        # Generate and score pairs
        raw_pairs = []
        for (bt, ft), specs in segments_map.items():
            if len(specs) < 2:
                continue
            for a, b in combinations(specs, 2):
                if a.make.lower() == b.make.lower():
                    continue  # No intra-brand comparisons

                # If brands filter is active, AT LEAST ONE car must match the selected brands
                if brand_list:
                    if a.make.lower() not in brand_list and b.make.lower() not in brand_list:
                        continue

                score = 0
                for spec in (a, b):
                    if spec.power_hp:
                        score += 2
                    if spec.price_from:
                        score += 3
                    if spec.range_km or spec.range_wltp:
                        score += 2
                    if spec.battery_kwh:
                        score += 1
                    if spec.acceleration_0_100:
                        score += 2
                    if spec.length_mm:
                        score += 1

                if a.price_from and b.price_from:
                    ratio = min(a.price_from, b.price_from) / max(a.price_from, b.price_from)
                    if ratio >= 0.6:
                        score += 5

                raw_pairs.append((score, a, b))

        raw_pairs.sort(key=lambda x: -x[0])

        # Check for existing comparison articles
        pairs = []
        for score, a, b in raw_pairs[:limit]:
            slug_a = slugify(f"{a.make}-{a.model_name}-vs-{b.make}-{b.model_name}-comparison")[:200]
            slug_b = slugify(f"{b.make}-{b.model_name}-vs-{a.make}-{a.model_name}-comparison")[:200]

            existing = Article.objects.filter(
                slug__in=[slug_a, slug_b], is_deleted=False,
            ).values('id', 'slug', 'is_published', 'title').first()

            pairs.append({
                'score': score,
                'spec_a': self._spec_summary(a),
                'spec_b': self._spec_summary(b),
                'data_health': {
                    'a': self._spec_health(a),
                    'b': self._spec_health(b),
                },
                'existing_article': existing,
                'segment': f"{a.fuel_type} {a.get_body_type_display()}" if a.body_type else '',
            })

        # Segment summary
        seg_summary = {}
        for (bt, ft), specs in segments_map.items():
            label = f"{ft} {bt}"
            seg_summary[label] = len(specs)

        return Response({
            'total_vehicles': len(all_specs),
            'total_pairs': len(raw_pairs),
            'showing': len(pairs),
            'segments': seg_summary,
            'pairs': pairs,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='generate-comparison')
    def generate_comparison(self, request):
        """
        POST /api/v1/vehicle-specs/generate-comparison/
        Body: { "spec_a_id": 1, "spec_b_id": 2, "provider": "gemini" }
        Generates a comparison article and saves as draft.
        """
        spec_a_id = request.data.get('spec_a_id')
        spec_b_id = request.data.get('spec_b_id')
        provider = request.data.get('provider', 'gemini')

        if not spec_a_id or not spec_b_id:
            return Response({'error': 'spec_a_id and spec_b_id are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        if provider not in ('gemini', 'groq'):
            provider = 'gemini'

        try:
            spec_a = VehicleSpecs.objects.get(id=spec_a_id)
            spec_b = VehicleSpecs.objects.get(id=spec_b_id)
        except VehicleSpecs.DoesNotExist:
            return Response({'error': 'One or both VehicleSpecs not found'},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            from ai_engine.modules.comparison_generator import generate_comparison as gen_comp

            result = gen_comp(spec_a, spec_b, provider=provider)

            # Ensure unique slug
            slug = result['slug']
            base_slug = slug
            counter = 1
            while Article.objects.filter(slug=slug, is_deleted=False).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Create draft article
            article = Article.objects.create(
                title=result['title'],
                slug=slug,
                content=result['content'],
                content_original=result['content'],
                summary=result['summary'],
                seo_description=result['seo_description'][:160],
                is_published=False,
                is_news_only=False,
                generation_metadata={
                    'source': 'comparison_generator',
                    'provider': provider,
                    'spec_a': f"{spec_a.make} {spec_a.model_name}",
                    'spec_b': f"{spec_b.make} {spec_b.model_name}",
                    'word_count': result['word_count'],
                },
            )

            # Assign Comparisons category
            from news.models import Category, Tag
            comp_cat, _ = Category.objects.get_or_create(
                name='Comparisons', defaults={'slug': 'comparisons'},
            )
            article.categories.add(comp_cat)

            # Set featured image from spec_a's source article
            image_url = result.get('image_url_a') or result.get('image_url_b')
            if image_url:
                # For Cloudinary, the image field stores the cloud path
                # Try to copy from the source article directly
                for sp in (spec_a, spec_b):
                    try:
                        if sp.article and sp.article.image:
                            article.image = sp.article.image
                            article.image_source = 'uploaded'
                            article.save(update_fields=['image', 'image_source'])
                            break
                    except Exception:
                        pass

            # Set image_2 from the other vehicle's article
            try:
                if article.image and spec_b.article and spec_b.article.image:
                    if str(article.image) != str(spec_b.article.image):
                        article.image_2 = spec_b.article.image
                        article.save(update_fields=['image_2'])
                elif article.image and spec_a.article and spec_a.article.image:
                    if str(article.image) != str(spec_a.article.image):
                        article.image_2 = spec_a.article.image
                        article.save(update_fields=['image_2'])
            except Exception:
                pass

            # Auto-assign brand tags
            for spec in (spec_a, spec_b):
                brand_tag = Tag.objects.filter(name__iexact=spec.make).first()
                if brand_tag:
                    article.tags.add(brand_tag)

            # CarSpecification for primary vehicle
            CarSpecification.objects.update_or_create(
                article=article,
                defaults={'make': spec_a.make, 'model': spec_a.model_name, 'trim': spec_a.trim_name or ''},
            )

            from ..serializers import ArticleListSerializer
            return Response({
                'success': True,
                'article': ArticleListSerializer(article).data,
                'word_count': result['word_count'],
                'message': f'Generated: {result["title"]}',
            })

        except Exception as e:
            logger.error(f'Comparison generation failed: {e}', exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated],
            url_path='recent-comparisons')
    def recent_comparisons(self, request):
        """
        GET /api/v1/vehicle-specs/recent-comparisons/
        Returns the 20 most recent comparison articles for the "Recently Generated" panel.
        """
        articles = Article.objects.filter(
            categories__name='Comparisons',
            is_deleted=False,
        ).order_by('-created_at')[:20]

        results = []
        for art in articles:
            meta = art.generation_metadata or {}
            image_url = None
            if art.image:
                try:
                    image_url = art.image.url if hasattr(art.image, 'url') else str(art.image)
                except Exception:
                    pass
            results.append({
                'id': art.id,
                'title': art.title,
                'slug': art.slug,
                'is_published': art.is_published,
                'created_at': art.created_at.isoformat() if art.created_at else None,
                'image_url': image_url,
                'spec_a': meta.get('spec_a', ''),
                'spec_b': meta.get('spec_b', ''),
                'word_count': meta.get('word_count', 0),
                'provider': meta.get('provider', ''),
            })

        return Response({'articles': results})

