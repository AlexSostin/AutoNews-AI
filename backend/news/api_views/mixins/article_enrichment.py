"""
Article enrichment mixin — handles specs extraction, re-enrichment,
bulk re-enrichment, and debug endpoints.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import re
import logging

from news.api_views._shared import invalidate_article_cache

logger = logging.getLogger(__name__)


class ArticleEnrichmentMixin:
    """Mixin for article enrichment actions on ArticleViewSet."""

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def extract_specs(self, request, slug=None):
        """
        Extract vehicle specifications from article using AI
        POST /api/v1/articles/{slug}/extract-specs/
        """
        from news.models import VehicleSpecs
        from news.serializers import VehicleSpecsSerializer
        
        article = self.get_object()
        
        try:
            from ai_engine.modules.specs_extractor import extract_vehicle_specs
            
            specs_data = extract_vehicle_specs(
                title=article.title,
                content=article.content,
                summary=article.summary or ""
            )
            
            vehicle_specs, created = VehicleSpecs.objects.update_or_create(
                article=article,
                defaults=specs_data
            )
            
            serializer = VehicleSpecsSerializer(vehicle_specs)
            
            return Response({
                'success': True,
                'created': created,
                'specs': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error extracting specs for article {article.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated],
            url_path='re-enrich')
    def re_enrich(self, request, slug=None):
        """
        Re-enrich article metadata using AI (Deep Specs + A/B Titles + Web Search).
        Does NOT modify article content — safe to run on any published article.
        POST /api/v1/articles/{slug}/re-enrich/
        """
        from news.models import CarSpecification
        
        article = self.get_object()
        results = {
            'deep_specs': None,
            'ab_titles': None,
            'web_search': None,
        }
        errors = []

        # --- Step 1: Web Search Enrichment ---
        specs_dict = None
        web_context = ''
        try:
            car_spec = CarSpecification.objects.filter(article=article).first()

            if car_spec and car_spec.make:
                _year = None
                _y_match = re.search(r'\b(20[2-3]\d)\b', article.title)
                if _y_match:
                    _year = int(_y_match.group(1))
                elif car_spec.release_date:
                    _ry = re.search(r'(20[2-3]\d)', car_spec.release_date)
                    if _ry:
                        _year = int(_ry.group(1))
                specs_dict = {
                    'make': car_spec.make or '',
                    'model': car_spec.model or '',
                    'trim': car_spec.trim or '',
                    'year': _year,
                    'horsepower': car_spec.horsepower,
                    'torque': car_spec.torque or '',
                    'acceleration': car_spec.zero_to_sixty or '',
                    'top_speed': car_spec.top_speed or '',
                    'drivetrain': car_spec.drivetrain or '',
                    'price': car_spec.price or '',
                }
            else:
                specs_dict = self._parse_specs_from_title(article.title)

            if specs_dict and specs_dict.get('make'):
                try:
                    from ai_engine.modules.searcher import get_web_context
                    web_context = get_web_context(specs_dict)
                    results['web_search'] = {
                        'success': True,
                        'context_length': len(web_context),
                    }
                except Exception as ws_err:
                    errors.append(f'Web search: {ws_err}')
                    results['web_search'] = {'success': False, 'error': str(ws_err)}
            else:
                results['web_search'] = {'success': False, 'error': 'No make/model found'}

        except Exception as e:
            errors.append(f'Web search setup: {e}')
            results['web_search'] = {'success': False, 'error': str(e)}

        # --- Step 2: Deep Specs Enrichment ---
        try:
            from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
            vehicle_specs = generate_deep_vehicle_specs(
                article,
                specs=specs_dict,
                web_context=web_context,
                provider='gemini'
            )
            if vehicle_specs:
                results['deep_specs'] = {
                    'success': True,
                    'make': vehicle_specs.make,
                    'model': vehicle_specs.model_name,
                    'trim': vehicle_specs.trim_name or 'Standard',
                    'fields_filled': sum(1 for f in vehicle_specs._meta.fields if getattr(vehicle_specs, f.name) is not None),
                }
            else:
                results['deep_specs'] = {'success': False, 'error': 'No specs generated'}
        except Exception as ds_err:
            errors.append(f'Deep specs: {ds_err}')
            results['deep_specs'] = {'success': False, 'error': str(ds_err)}

        # --- Step 3: A/B Title Variants ---
        try:
            from ai_engine.main import generate_title_variants
            from news.models import ArticleTitleVariant
            existing_count = ArticleTitleVariant.objects.filter(article=article).count()

            if existing_count == 0:
                generate_title_variants(article, provider='gemini')
                new_count = ArticleTitleVariant.objects.filter(article=article).count()
                results['ab_titles'] = {
                    'success': True,
                    'variants_created': new_count,
                }
            else:
                results['ab_titles'] = {
                    'success': True,
                    'skipped': True,
                    'existing_variants': existing_count,
                    'message': 'A/B variants already exist',
                }
        except Exception as ab_err:
            errors.append(f'A/B titles: {ab_err}')
            results['ab_titles'] = {'success': False, 'error': str(ab_err)}

        # --- Step 4: Smart Auto-Tags ---
        try:
            from news.auto_tags import auto_tag_article
            tag_result = auto_tag_article(article, use_ai=True)
            results['smart_tags'] = {
                'success': True,
                'new_tags_created': tag_result['created'],
                'existing_tags_matched': tag_result['matched'],
                'total_added': tag_result['total'],
                'ai_used': tag_result['ai_used'],
            }
        except Exception as tag_err:
            errors.append(f'Smart tags: {tag_err}')
            results['smart_tags'] = {'success': False, 'error': str(tag_err)}

        # --- Summary ---
        success_count = sum(1 for r in results.values() if r and r.get('success'))
        total = len(results)

        try:
            from news.models import AdminActionLog
            AdminActionLog.log(article, request.user, 're_enrich', success=success_count > 0, details={
                'steps_completed': f'{success_count}/{total}',
                'deep_specs': results.get('deep_specs', {}).get('success', False),
                'ab_titles': results.get('ab_titles', {}).get('success', False),
                'web_search': results.get('web_search', {}).get('success', False),
                'make': results.get('deep_specs', {}).get('make', ''),
                'model': results.get('deep_specs', {}).get('model_name', ''),
            })
        except Exception:
            pass

        return Response({
            'success': success_count > 0,
            'message': f'{success_count}/{total} enrichment steps completed',
            'results': results,
            'errors': errors if errors else None,
        })

    def _parse_specs_from_title(self, title):
        """Multi-pattern title parser for make/model extraction."""
        year = None
        make = None
        model_name = None

        m = re.match(r'(\d{4})\s+(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Comparison|Test))?$', title, re.IGNORECASE)
        if m:
            year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()
        if not make:
            m = re.match(r'(?:First\s+Drive|Review|Test\s+Drive)[:\s]+(\d{4})\s+(\S+)\s+(.+?)(?:\s+-\s+.+)?$', title, re.IGNORECASE)
            if m:
                year, make, model_name = int(m.group(1)), m.group(2), m.group(3).strip()
                if ' - ' in model_name:
                    model_name = model_name.split(' - ')[0].strip()
        if not make:
            m = re.match(r'(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Walkaround|Comparison|Test))', title, re.IGNORECASE)
            if m:
                make, model_name = m.group(1), m.group(2).strip()
        if not make:
            try:
                from news.auto_tags import KNOWN_BRANDS, BRAND_DISPLAY_NAMES
                title_lower = title.lower()
                for brand in KNOWN_BRANDS:
                    if title_lower.startswith(brand) or title_lower.startswith(brand + ' '):
                        make = BRAND_DISPLAY_NAMES.get(brand, brand.title())
                        rest = title[len(brand):].strip()
                        model_match = re.match(r'(\S+(?:\s+\S+)?)', rest)
                        if model_match:
                            model_name = model_match.group(1)
                        break
            except ImportError:
                pass
        if not year:
            y_match = re.search(r'\b(20[2-3]\d)\b', title)
            if y_match:
                year = int(y_match.group(1))
        if make and model_name:
            return {'make': make, 'model': model_name, 'year': year}
        return None

    @action(detail=False, methods=['post'], url_path='bulk-re-enrich')
    def bulk_re_enrich(self, request):
        """
        Bulk re-enrich multiple articles — background thread + polling.
        POST /api/v1/articles/bulk-re-enrich/
        Body: { "mode": "missing"|"selected"|"all", "article_ids": [...] }
        """
        import threading
        import uuid as _uuid
        from django.core.cache import cache
        from news.models import Article, VehicleSpecs, CarSpecification
        from news.models import ArticleTitleVariant

        mode = request.data.get('mode', 'missing')
        article_ids = request.data.get('article_ids', [])

        published = Article.objects.filter(is_published=True, is_deleted=False)

        if mode == 'selected' and article_ids:
            articles = published.filter(id__in=article_ids)
        elif mode == 'missing':
            articles_with_specs = VehicleSpecs.objects.values_list('article_id', flat=True)
            articles_with_ab = ArticleTitleVariant.objects.values_list('article_id', flat=True)
            articles = published.exclude(
                id__in=set(articles_with_specs) & set(articles_with_ab)
            )
        else:
            articles = published

        total_articles = articles.count()
        article_id_list = list(articles.order_by('id').values_list('id', flat=True))
        task_id = str(_uuid.uuid4())[:8]

        cache.set(f'bulk_enrich_{task_id}', {
            'status': 'running',
            'current': 0,
            'total': total_articles,
            'results': [],
            'success_count': 0,
            'error_count': 0,
            'message': 'Starting enrichment...',
            'elapsed_seconds': 0,
        }, timeout=3600)

        def _process_task():
            """Background thread — processes articles and updates cache."""
            import time as _time
            from django.core.cache import cache as _cache
            from django.db import connection

            success_total = 0
            errors_total = 0
            all_results = []
            start_time = _time.time()

            if total_articles == 0:
                _cache.set(f'bulk_enrich_{task_id}', {
                    'status': 'done', 'current': 0, 'total': 0,
                    'results': [], 'success_count': 0, 'error_count': 0,
                    'message': 'All articles are fully enriched!', 'elapsed_seconds': 0,
                }, timeout=3600)
                return

            for idx, art_id in enumerate(article_id_list, 1):
                try:
                    article = Article.objects.get(id=art_id)
                except Article.DoesNotExist:
                    continue

                article_result = {
                    'id': article.id,
                    'title': article.title[:80],
                    'steps': {},
                    'errors': [],
                }

                # Step 1: Web Search
                specs_dict = None
                web_context = ''
                try:
                    car_spec = CarSpecification.objects.filter(article=article).first()
                    if car_spec and car_spec.make:
                        _year = None
                        _y_match = re.search(r'\b(20[2-3]\d)\b', article.title)
                        if _y_match:
                            _year = int(_y_match.group(1))
                        elif car_spec.release_date:
                            _ry = re.search(r'(20[2-3]\d)', car_spec.release_date)
                            if _ry:
                                _year = int(_ry.group(1))
                        specs_dict = {
                            'make': car_spec.make or '',
                            'model': car_spec.model or '',
                            'trim': car_spec.trim or '',
                            'year': _year,
                        }
                    else:
                        specs_dict = self._parse_specs_from_title(article.title)

                    if specs_dict and specs_dict.get('make'):
                        try:
                            from ai_engine.modules.searcher import get_web_context
                            web_context = get_web_context(specs_dict)
                            article_result['steps']['web_search'] = True
                        except Exception:
                            pass
                except Exception:
                    pass

                # Step 2: Deep Specs
                existing_vs = VehicleSpecs.objects.filter(article=article).first()
                has_populated_specs = existing_vs and (existing_vs.power_hp or existing_vs.torque_nm) and existing_vs.length_mm
                
                if has_populated_specs and existing_vs.battery_kwh and existing_vs.battery_kwh < 50:
                    if (existing_vs.range_km and existing_vs.range_km > 500) or \
                       (existing_vs.range_cltc and existing_vs.range_cltc > 500):
                        has_populated_specs = False

                if not has_populated_specs and specs_dict and specs_dict.get('make'):
                    try:
                        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                        vehicle_specs = generate_deep_vehicle_specs(
                            article, specs=specs_dict, web_context=web_context, provider='gemini'
                        )
                        if vehicle_specs:
                            key_fields = {}
                            for fn in ['power_hp', 'torque_nm', 'battery_kwh', 'range_km', 'range_cltc', 'length_mm', 'weight_kg', 'price_from']:
                                val = getattr(vehicle_specs, fn, None)
                                if val is not None:
                                    key_fields[fn] = val
                            total_filled = sum(1 for f in vehicle_specs._meta.fields if getattr(vehicle_specs, f.name) is not None and f.name not in ('id',))
                            article_result['steps']['deep_specs'] = True
                            article_result['deep_specs_detail'] = {
                                'make': vehicle_specs.make,
                                'model': vehicle_specs.model_name,
                                'fields_filled': total_filled,
                                'key': key_fields,
                            }
                        else:
                            article_result['steps']['deep_specs'] = False
                    except Exception as e:
                        article_result['errors'].append(f'Deep specs: {e}')
                        article_result['steps']['deep_specs'] = False
                elif has_populated_specs:
                    article_result['steps']['deep_specs'] = 'skipped'
                    vs = existing_vs
                    
                    if specs_dict and specs_dict.get('make'):
                        try:
                            from ai_engine.modules.deep_specs import _clean_model_name
                            from news.auto_tags import BRAND_DISPLAY_NAMES
                            norm_make = BRAND_DISPLAY_NAMES.get((specs_dict.get('make', '') or '').lower().strip(), specs_dict.get('make', ''))
                            cleaned_model = _clean_model_name(vs.model_name, norm_make)
                            vs_update_fields = []
                            if vs.model_name != cleaned_model:
                                vs.model_name = cleaned_model
                                vs_update_fields.append('model_name')
                            if vs.make != norm_make:
                                vs.make = norm_make
                                vs_update_fields.append('make')
                            if vs_update_fields:
                                vs.save(update_fields=vs_update_fields)
                        except Exception:
                            pass
                    
                    key_fields = {}
                    for fn in ['power_hp', 'torque_nm', 'battery_kwh', 'range_km', 'range_cltc', 'length_mm', 'weight_kg', 'price_from']:
                        val = getattr(vs, fn, None)
                        if val is not None:
                            key_fields[fn] = val
                    article_result['deep_specs_detail'] = {
                        'make': vs.make,
                        'model': vs.model_name,
                        'fields_filled': sum(1 for f in vs._meta.fields if getattr(vs, f.name) is not None and f.name not in ('id',)),
                        'key': key_fields,
                    }
                else:
                    article_result['steps']['deep_specs'] = 'no_specs'

                # Step 3: A/B Titles
                has_ab = ArticleTitleVariant.objects.filter(article=article).exists()
                if not has_ab:
                    try:
                        from ai_engine.main import generate_title_variants
                        generate_title_variants(article, provider='gemini')
                        article_result['steps']['ab_titles'] = True
                    except Exception as e:
                        article_result['errors'].append(f'A/B titles: {e}')
                else:
                    article_result['steps']['ab_titles'] = 'skipped'

                # Step 4: Smart Auto-Tags
                try:
                    from news.auto_tags import auto_tag_article
                    tag_result = auto_tag_article(article, use_ai=True)
                    created_count = len(tag_result['created'])
                    matched_count = len(tag_result['matched'])
                    article_result['steps']['smart_tags'] = created_count + matched_count
                    if tag_result['created']:
                        article_result['steps']['tags_created'] = tag_result['created']
                    if tag_result['ai_used']:
                        article_result['steps']['ai_used'] = True
                except Exception as e:
                    article_result['errors'].append(f'Smart tags: {e}')

                if article_result['errors']:
                    errors_total += 1
                else:
                    success_total += 1

                all_results.append(article_result)

                elapsed = round(_time.time() - start_time, 1)
                _cache.set(f'bulk_enrich_{task_id}', {
                    'status': 'running',
                    'current': idx,
                    'total': total_articles,
                    'results': all_results[-10:],
                    'success_count': success_total,
                    'error_count': errors_total,
                    'message': f'Processing {idx}/{total_articles}...',
                    'elapsed_seconds': elapsed,
                }, timeout=3600)

            # Final state
            elapsed = round(_time.time() - start_time, 1)
            ds_generated = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') is True)
            ds_skipped = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') == 'skipped')
            ds_failed = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') is False)
            ds_no_specs = sum(1 for r in all_results if r.get('steps', {}).get('deep_specs') == 'no_specs')
            total_fields = sum(r.get('deep_specs_detail', {}).get('fields_filled', 0) for r in all_results)
            tags_added = sum(r.get('steps', {}).get('smart_tags', 0) for r in all_results if isinstance(r.get('steps', {}).get('smart_tags'), int))

            summary = {
                'deep_specs': {
                    'generated': ds_generated, 'skipped': ds_skipped,
                    'failed': ds_failed, 'no_data': ds_no_specs,
                    'total_fields_filled': total_fields,
                },
                'tags_added': tags_added,
                'duration': elapsed,
            }

            _cache.set(f'bulk_enrich_{task_id}', {
                'status': 'done',
                'current': total_articles,
                'total': total_articles,
                'results': all_results,
                'success_count': success_total,
                'error_count': errors_total,
                'message': f'Bulk enrichment completed: {success_total}/{total_articles} articles processed in {elapsed}s',
                'elapsed_seconds': elapsed,
                'summary': summary,
            }, timeout=3600)

            connection.close()

        thread = threading.Thread(target=_process_task, daemon=True)
        thread.start()

        return Response({
            'task_id': task_id,
            'total': total_articles,
            'message': f'Enrichment started for {total_articles} articles',
        })

    @action(detail=False, methods=['get'], url_path='bulk-re-enrich-status')
    def bulk_re_enrich_status(self, request):
        """Poll enrichment progress."""
        from django.core.cache import cache

        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=400)

        state = cache.get(f'bulk_enrich_{task_id}')
        if not state:
            return Response({'error': 'Task not found or expired'}, status=404)

        return Response(state)

    @action(detail=False, methods=['get'], url_path='debug-vehicle-specs')
    def debug_vehicle_specs(self, request):
        """Debug endpoint — dump all VehicleSpecs (admin only)."""
        from news.models import VehicleSpecs

        make = request.query_params.get('make', '')
        model = request.query_params.get('model', '')

        qs = VehicleSpecs.objects.all()
        if make:
            qs = qs.filter(make__iexact=make)
        if model:
            qs = qs.filter(model_name__iexact=model)

        results = []
        for vs in qs.order_by('make', 'model_name')[:50]:
            fields = {}
            for f in vs._meta.fields:
                val = getattr(vs, f.name)
                if val is not None and f.name not in ('id',):
                    fields[f.name] = str(val) if not isinstance(val, (int, float, bool, type(None))) else val
            results.append(fields)

        return Response({
            'count': qs.count(),
            'results': results,
        })
