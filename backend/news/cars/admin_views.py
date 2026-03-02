"""
Car Catalog — admin endpoints for brand management.

Endpoints:
  POST  /api/v1/cars/cleanup/                — Brand normalization
  CRUD  /api/v1/admin/brands/                — Brand management
  POST  /api/v1/admin/brands/{id}/merge/     — Merge brands
  POST  /api/v1/admin/brands/bulk-merge/     — Bulk merge
  GET   /api/v1/admin/brands/{id}/articles/  — List brand articles
  POST  /api/v1/admin/brands/{id}/move-article/ — Move article
  POST  /api/v1/admin/brands/sync/           — Sync from specs
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db.models import Q
from django.utils.text import slugify

from ..models import CarSpecification, Brand, BrandAlias
from ..serializers import BrandSerializer


class BrandCleanupView(APIView):
    """POST /api/v1/cars/cleanup/ — Run brand normalization (admin only).

    Query params:
        ?apply=true  — Apply changes (default: dry run)
    """
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
        from ..models import VehicleSpecs
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
            # Find brand IDs that have matching specs/articles
            matching_brand_names = (
                CarSpecification.objects
                .filter(
                    Q(model__icontains=search) |
                    Q(article__title__icontains=search)
                )
                .exclude(make='')
                .values_list('make', flat=True)
                .distinct()
            )
            # Match by brand name OR by having matching articles
            brand_q = Q(name__icontains=search)
            for make in matching_brand_names:
                brand_q |= Q(name__iexact=make)
            qs = qs.filter(brand_q)
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

    @action(detail=False, methods=['post'], url_path='bulk-merge')
    def bulk_merge(self, request):
        """
        Merge multiple brands at once.

        POST /api/v1/admin/brands/bulk-merge/
        Body: { "merges": [{"source": "HUAWEI AITO", "target": "AITO"}, ...] }
        """
        merges = request.data.get('merges', [])
        if not merges:
            return Response({'error': 'merges list is required'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        total_specs = 0
        for m in merges:
            source_name = m.get('source', '').strip()
            target_name = m.get('target', '').strip()
            if not source_name or not target_name:
                results.append({'error': f'Invalid merge: {m}'})
                continue

            try:
                source_brand = Brand.objects.get(name__iexact=source_name)
            except Brand.DoesNotExist:
                results.append({'skipped': f'"{source_name}" not found'})
                continue

            try:
                target_brand = Brand.objects.get(name__iexact=target_name)
            except Brand.DoesNotExist:
                results.append({'skipped': f'Target "{target_name}" not found'})
                continue

            if source_brand.pk == target_brand.pk:
                results.append({'skipped': f'"{source_name}" is the same as target'})
                continue

            # Rename specs
            updated = CarSpecification.objects.filter(
                make__iexact=source_brand.name
            ).update(make=target_brand.name)
            total_specs += updated

            # Create alias
            BrandAlias.objects.get_or_create(
                alias=source_brand.name,
                defaults={'canonical_name': target_brand.name},
            )

            # Re-parent sub-brands
            source_brand.sub_brands.update(parent=target_brand)

            # Delete source
            src_name = source_brand.name
            source_brand.delete()
            results.append({'merged': f'"{src_name}" → "{target_brand.name}"', 'specs_updated': updated})

        from news.api_views import invalidate_article_cache
        invalidate_article_cache()

        return Response({
            'success': True,
            'results': results,
            'total_specs_updated': total_specs,
        })

    @action(detail=True, methods=['get'], url_path='articles')
    def articles(self, request, pk=None):
        """
        List articles belonging to this brand.

        GET /api/v1/admin/brands/{id}/articles/
        """
        brand = self.get_object()

        # Get all names (brand + sub-brands)
        names = [brand.name]
        for sub in brand.sub_brands.all():
            names.append(sub.name)
        # Build case-insensitive query for brand + sub-brands
        q = Q()
        for n in names:
            q |= Q(make__iexact=n)

        specs = (
            CarSpecification.objects
            .filter(q)
            .select_related('article')
            .order_by('-article__created_at')
        )

        articles = []
        for spec in specs:
            art = spec.article
            if not art:
                continue
            image = None
            if art.image:
                raw = str(art.image)
                if raw.count('https://') > 1:
                    raw = raw[raw.rfind('https://'):]
                if raw.startswith('http'):
                    image = raw
                elif hasattr(art.image, 'url'):
                    image = art.image.url

            articles.append({
                'id': art.id,
                'spec_id': spec.id,
                'title': art.title,
                'slug': art.slug,
                'make': spec.make,
                'model': spec.model,
                'image': image,
                'is_published': art.is_published,
                'created_at': art.created_at.isoformat() if art.created_at else None,
            })

        return Response({
            'brand': brand.name,
            'articles': articles,
            'count': len(articles),
        })

    @action(detail=True, methods=['post'], url_path='move-article')
    def move_article(self, request, pk=None):
        """
        Move a single article (CarSpecification) to this brand.

        POST /api/v1/admin/brands/{id}/move-article/
        Body: { "spec_id": 123 }
        """
        target_brand = self.get_object()
        spec_id = request.data.get('spec_id')

        if not spec_id:
            return Response({'error': 'spec_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            spec = CarSpecification.objects.get(pk=spec_id)
        except CarSpecification.DoesNotExist:
            return Response({'error': 'CarSpecification not found'}, status=status.HTTP_404_NOT_FOUND)

        old_make = spec.make
        spec.make = target_brand.name
        spec.is_make_locked = True
        spec.save(update_fields=['make', 'is_make_locked'])

        from news.api_views import invalidate_article_cache
        invalidate_article_cache()

        return Response({
            'success': True,
            'message': f'Moved article from "{old_make}" to "{target_brand.name}"',
            'spec_id': spec.id,
            'article_id': spec.article_id,
        })

    # Known brand name variations → canonical mapping
    KNOWN_ALIASES = {
        'HUAWEI AITO': 'AITO',
        'HUAWEI AVATR': 'Avatr',
        'HUAWEI Avatr': 'Avatr',
        'SAIC IM': 'IM',
        'GWM WEY': 'GWM',
        'DongFeng VOYAH': 'VOYAH',
        'Dongfeng VOYAH': 'VOYAH',
    }

    @action(detail=False, methods=['post'], url_path='sync')
    def sync_from_specs(self, request):
        """
        Sync brands from CarSpecification — create missing Brand records.
        Uses BrandAlias table + built-in KNOWN_ALIASES to prevent duplicates.

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
            # 1. Check built-in aliases first
            canonical = self.KNOWN_ALIASES.get(make, make)
            # 2. Then check BrandAlias table
            canonical = BrandAlias.resolve(canonical)

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
