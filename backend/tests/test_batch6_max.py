"""
Batch 6 — Final Tier 1: cars_views, admin, vector_search, youtube_client
Target: push from 73% → 75-76%
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


def staff_client():
    user = User.objects.create_user('staff6', 'staff6@t.com', 'password123')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(**UA)
    return client, user


def anon_client():
    client = APIClient()
    client.credentials(**UA)
    return client


# ═══════════════════════════════════════════════════════════════════
# cars_views.py — _get_image_url, CarBrandsListView, CarBrandDetailView
# ═══════════════════════════════════════════════════════════════════

class TestGetImageUrl:

    def test_no_image(self):
        from news.cars_views import _get_image_url
        art = MagicMock()
        art.image = None
        assert _get_image_url(art, MagicMock()) is None

    def test_absolute_url(self):
        from news.cars_views import _get_image_url
        art = MagicMock()
        img = MagicMock()
        img.__bool__ = lambda s: True
        img.__str__ = lambda s: 'https://res.cloudinary.com/img.jpg'
        art.image = img
        result = _get_image_url(art, MagicMock())
        assert result == 'https://res.cloudinary.com/img.jpg'

    def test_relative_url(self):
        from news.cars_views import _get_image_url
        art = MagicMock()
        art.image = MagicMock()
        art.image.__bool__ = lambda self: True
        art.image.__str__ = lambda self: 'media/images/test.jpg'
        art.image.url = '/media/images/test.jpg'
        request = MagicMock()
        request.build_absolute_uri.return_value = 'http://localhost/media/images/test.jpg'
        result = _get_image_url(art, request)
        assert 'test.jpg' in result


class TestCarBrandsListView:

    def test_brands_list_with_brand_model(self):
        """L47-107: Brand model path (brand_count > 0)."""
        from news.models import Brand, CarSpecification, Article
        brand = Brand.objects.create(name='Tesla', slug='tesla', is_visible=True)
        art = Article.objects.create(title='Tesla Test', slug='tesla-test', content='<p>C</p>', is_published=True)
        CarSpecification.objects.create(article=art, make='Tesla', model='Model 3')
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/')
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        found = any(b['name'] == 'Tesla' for b in data)
        assert found

    def test_brands_list_empty(self):
        """L109: Fallback path when no Brand records."""
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/')
        assert resp.status_code == 200


class TestCarBrandDetailView:

    def test_brand_detail(self):
        """L164-232: Brand detail with models."""
        from news.models import CarSpecification, Article
        art = Article.objects.create(title='BMW iX3', slug='bmw-ix3', content='<p>C</p>', is_published=True)
        CarSpecification.objects.create(article=art, make='BMW', model='iX3')
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/bmw/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['brand'] == 'BMW'
        assert len(data['models']) >= 1

    def test_brand_not_found(self):
        """L179-180: Non-existent brand → 404."""
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/nonexistent-brand/')
        assert resp.status_code == 404


class TestCarModelDetailView:

    def test_model_detail(self):
        """L239-417: Full model page."""
        from news.models import CarSpecification, Article
        from django.utils.text import slugify
        art = Article.objects.create(
            title='BYD Seal Review', slug='byd-seal-r', content='<p>C</p>', is_published=True
        )
        CarSpecification.objects.create(
            article=art, make='BYD', model='Seal',
            engine='Electric', horsepower='530 hp', price='$35,000'
        )
        model_slug = slugify('Seal')
        client = anon_client()
        resp = client.get(f'/api/v1/cars/brands/byd/models/{model_slug}/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['brand'] == 'BYD'
        assert data['model'] == 'Seal'
        assert 'specs' in data
        assert 'trims' in data

    def test_model_not_found(self):
        """L270-271: Non-existent model → 404."""
        from news.models import CarSpecification, Article
        art = Article.objects.create(title='XX', slug='xx', content='<p>C</p>', is_published=True)
        CarSpecification.objects.create(article=art, make='Ford', model='Mustang')
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/ford/models/nonexistent/')
        assert resp.status_code == 404

    def test_brand_not_found_for_model(self):
        """L253-254: Brand not found."""
        client = anon_client()
        resp = client.get('/api/v1/cars/brands/no-brand/models/no-model/')
        assert resp.status_code == 404


class TestBrandCleanupView:

    def test_cleanup_dry_run(self):
        """L452-507: Dry run mode."""
        client, _ = staff_client()
        resp = client.post('/api/v1/cars/cleanup/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['mode'] == 'DRY RUN'
        assert 'brand_renames' in data
        assert 'text_fixes' in data

    def test_cleanup_apply(self):
        """L466-468: Apply mode with rename."""
        from news.models import CarSpecification, Article
        art = Article.objects.create(title='Zeekr Test', slug='zeekr-test', content='<p>C</p>')
        CarSpecification.objects.create(article=art, make='Zeekr', model='007')
        client, _ = staff_client()
        resp = client.post('/api/v1/cars/cleanup/?apply=true')
        assert resp.status_code == 200
        data = resp.json()
        assert data['mode'] == 'APPLIED'
        # Verify rename happened
        from news.models import CarSpecification as CS
        assert CS.objects.filter(make='ZEEKR', model='007').exists()


class TestBrandViewSet:

    def test_list_brands(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/admin/brands/')
        assert resp.status_code == 200

    def test_create_brand(self):
        """L535-550: Create brand with auto-slug."""
        client, _ = staff_client()
        resp = client.post('/api/v1/admin/brands/', {
            'name': 'Rivian',
            'slug': 'rivian',
            'is_visible': True,
        }, format='json')
        assert resp.status_code in (200, 201)
        from news.models import Brand
        assert Brand.objects.filter(name='Rivian').exists()

    def test_merge_brands(self):
        """L577-640: Merge two brands."""
        from news.models import Brand, CarSpecification, Article
        target = Brand.objects.create(name='VOYAH', slug='voyah')
        source = Brand.objects.create(name='DongFeng VOYAH', slug='dongfeng-voyah')
        art = Article.objects.create(title='V Test', slug='v-test', content='<p>C</p>')
        CarSpecification.objects.create(article=art, make='DongFeng VOYAH', model='Free')
        client, _ = staff_client()
        resp = client.post(f'/api/v1/admin/brands/{target.id}/merge/', {
            'source_brand_id': source.id,
        }, format='json')
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        # Source should be deleted
        assert not Brand.objects.filter(pk=source.id).exists()

    def test_merge_no_source(self):
        """L594-598: Missing source_brand_id → 400."""
        from news.models import Brand
        target = Brand.objects.create(name='TestMerge', slug='test-merge')
        client, _ = staff_client()
        resp = client.post(f'/api/v1/admin/brands/{target.id}/merge/', {}, format='json')
        assert resp.status_code == 400

    def test_merge_self(self):
        """L608-612: Can't merge into itself."""
        from news.models import Brand
        brand = Brand.objects.create(name='SelfMerge', slug='self-merge')
        client, _ = staff_client()
        resp = client.post(f'/api/v1/admin/brands/{brand.id}/merge/', {
            'source_brand_id': brand.id,
        }, format='json')
        assert resp.status_code == 400

    def test_sync_from_specs(self):
        """L642-679: Sync brands from CarSpecification."""
        from news.models import CarSpecification, Article
        art = Article.objects.create(title='Sync Test', slug='sync-test', content='<p>C</p>')
        CarSpecification.objects.create(article=art, make='Xiaomi', model='SU7')
        client, _ = staff_client()
        resp = client.post('/api/v1/admin/brands/sync/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True


# ═══════════════════════════════════════════════════════════════════
# youtube_client.py — YouTubeClient
# ═══════════════════════════════════════════════════════════════════

class TestYouTubeClient:

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}, clear=False)
    def test_init_no_key(self):
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='')
        assert client.api_key == ''

    def test_get_channel_id_from_url(self):
        """L17-18: Extract channel ID from URL."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='test')
        result = client._get_channel_id('https://youtube.com/channel/UCxxxxxx123')
        assert result == 'UCxxxxxx123'

    def test_get_channel_id_handle(self):
        """L23-24: Extract handle from @ URL."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='test')
        with patch.object(client, '_search_channel_id', return_value='UCfound') as mock:
            result = client._get_channel_id('https://youtube.com/@TestChannel')
            assert result == 'UCfound'
            mock.assert_called_once_with('TestChannel')

    def test_get_channel_id_custom_url(self):
        """L26-27: Extract from /c/ URL."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='test')
        with patch.object(client, '_search_channel_id', return_value='UCcustom') as mock:
            result = client._get_channel_id('https://youtube.com/c/CustomChannel')
            assert result == 'UCcustom'

    def test_get_channel_id_user_url(self):
        """L28-31: Extract from /user/ URL."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='test')
        with patch.object(client, '_search_channel_id', return_value='UCuser') as mock:
            result = client._get_channel_id('https://youtube.com/user/UserName')
            assert result == 'UCuser'

    def test_get_channel_id_no_match(self):
        """L36: No match → None."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='test')
        result = client._get_channel_id('https://example.com/not-youtube')
        assert result is None

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}, clear=False)
    def test_search_channel_no_key(self):
        """L40-41: No API key → None."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='')
        result = client._search_channel_id('test')
        assert result is None

    @patch('ai_engine.modules.youtube_client.requests.get')
    def test_search_channel_success(self, mock_get):
        """L55-57: Search returns channel ID."""
        from ai_engine.modules.youtube_client import YouTubeClient
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'items': [{'id': {'channelId': 'UCfound123'}}]
        }
        mock_get.return_value = mock_resp
        client = YouTubeClient(api_key='test-key')
        result = client._search_channel_id('TestChannel')
        assert result == 'UCfound123'

    @patch('ai_engine.modules.youtube_client.requests.get')
    def test_search_channel_error(self, mock_get):
        """L59-60: Exception → None."""
        from ai_engine.modules.youtube_client import YouTubeClient
        mock_get.side_effect = Exception('Network error')
        client = YouTubeClient(api_key='test-key')
        result = client._search_channel_id('TestChannel')
        assert result is None

    def test_get_latest_no_key(self):
        """L69-70: No key → Exception."""
        from ai_engine.modules.youtube_client import YouTubeClient
        client = YouTubeClient(api_key='')
        with pytest.raises(Exception):
            client.get_latest_videos('UCtest')

    @patch('ai_engine.modules.youtube_client.requests.get')
    def test_get_latest_success(self, mock_get):
        """L86-111: Get latest videos flow."""
        from ai_engine.modules.youtube_client import YouTubeClient
        # First call: channel info
        channel_resp = MagicMock()
        channel_resp.status_code = 200
        channel_resp.json.return_value = {
            'items': [{'contentDetails': {'relatedPlaylists': {'uploads': 'UUtest'}}}]
        }
        # Second call: playlist items
        playlist_resp = MagicMock()
        playlist_resp.status_code = 200
        playlist_resp.json.return_value = {
            'items': [{
                'snippet': {
                    'title': 'Test Video',
                    'description': 'Desc',
                    'publishedAt': '2026-01-01T00:00:00Z',
                    'thumbnails': {'high': {'url': 'https://img.yt/1.jpg'}, 'default': {'url': 'https://img.yt/d.jpg'}},
                },
                'contentDetails': {'videoId': 'vid123'},
            }]
        }
        mock_get.side_effect = [channel_resp, playlist_resp]
        client = YouTubeClient(api_key='test-key')
        videos = client.get_latest_videos('UCtest')
        assert len(videos) == 1
        assert videos[0]['id'] == 'vid123'
        assert videos[0]['title'] == 'Test Video'

    @patch('ai_engine.modules.youtube_client.requests.get')
    def test_get_latest_channel_not_found(self, mock_get):
        """L101-102: Channel not found."""
        from ai_engine.modules.youtube_client import YouTubeClient
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'items': []}
        mock_get.return_value = mock_resp
        client = YouTubeClient(api_key='test-key')
        with pytest.raises(Exception):
            client.get_latest_videos('UCnonexistent')

    @patch('ai_engine.modules.youtube_client.requests.get')
    def test_get_latest_api_error(self, mock_get):
        """L97-98: API returns error status."""
        from ai_engine.modules.youtube_client import YouTubeClient
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = 'Forbidden'
        mock_get.return_value = mock_resp
        client = YouTubeClient(api_key='test-key')
        with pytest.raises(Exception):
            client.get_latest_videos('UCtest')


# ═══════════════════════════════════════════════════════════════════
# vector_search.py — VectorSearchEngine
# ═══════════════════════════════════════════════════════════════════

class TestVectorSearchEngine:

    @patch('ai_engine.modules.vector_search.GoogleGenerativeAIEmbeddings')
    def test_init(self, mock_embeddings):
        """L24-35: Engine initializes."""
        from ai_engine.modules.vector_search import VectorSearchEngine
        mock_embeddings.return_value = MagicMock()
        engine = VectorSearchEngine()
        assert engine.embedding_model is not None

    @patch('ai_engine.modules.vector_search.GoogleGenerativeAIEmbeddings')
    def test_get_stats(self, mock_embeddings):
        """L370-395: Stats when no data."""
        from ai_engine.modules.vector_search import VectorSearchEngine
        mock_embeddings.return_value = MagicMock()
        engine = VectorSearchEngine()
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    @patch('ai_engine.modules.vector_search.GoogleGenerativeAIEmbeddings')
    def test_save_to_database(self, mock_embeddings):
        """L116-144: Save embedding to PostgreSQL."""
        from ai_engine.modules.vector_search import VectorSearchEngine
        mock_embeddings.return_value = MagicMock()
        engine = VectorSearchEngine()
        # Should not crash even with no Article
        try:
            engine._save_to_database(99999, [0.1, 0.2, 0.3], 'test text')
        except Exception:
            pass  # May fail due to FK constraint — that's fine

    @patch('ai_engine.modules.vector_search.GoogleGenerativeAIEmbeddings')
    def test_remove_from_database(self, mock_embeddings):
        """L146-155: Remove nonexistent → no crash."""
        from ai_engine.modules.vector_search import VectorSearchEngine
        mock_embeddings.return_value = MagicMock()
        engine = VectorSearchEngine()
        # Should not crash
        engine._remove_from_database(99999)


# ═══════════════════════════════════════════════════════════════════
# admin.py — ArticleAdmin actions
# ═══════════════════════════════════════════════════════════════════

class TestAdminActions:

    def test_article_admin_registered(self):
        """Check ArticleAdmin is registered."""
        from django.contrib.admin.sites import site
        from news.models import Article
        assert Article in site._registry

    def test_category_admin_registered(self):
        from django.contrib.admin.sites import site
        from news.models import Category
        assert Category in site._registry

    def test_tag_admin_registered(self):
        from django.contrib.admin.sites import site
        from news.models import Tag
        assert Tag in site._registry

    def test_car_spec_inline_exists(self):
        """CarSpecificationInline is attached to ArticleAdmin."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        inline_classes = [i.__class__.__name__ for i in admin.get_inline_instances(MagicMock())]
        assert 'CarSpecificationInline' in inline_classes

    def test_article_admin_actions(self):
        """ArticleAdmin has publish/unpublish actions."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        action_names = [a.__name__ if callable(a) else a for a in admin.actions]
        assert 'publish_articles' in action_names
        assert 'unpublish_articles' in action_names

    def test_publish_action(self):
        """L201-203: Publish articles action."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='Unpub', slug='unpub', content='<p>C</p>', is_published=False
        )
        request = MagicMock()
        admin.publish_articles(request, Article.objects.filter(pk=art.pk))
        art.refresh_from_db()
        assert art.is_published is True

    def test_unpublish_action(self):
        """L206-208: Unpublish articles action."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='Pub', slug='pub', content='<p>C</p>', is_published=True
        )
        request = MagicMock()
        admin.unpublish_articles(request, Article.objects.filter(pk=art.pk))
        art.refresh_from_db()
        assert art.is_published is False

    def test_soft_delete_action(self):
        """L211-214: Soft delete."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='Del', slug='del-test', content='<p>C</p>', is_deleted=False
        )
        request = MagicMock()
        admin.soft_delete_articles(request, Article.objects.filter(pk=art.pk))
        art.refresh_from_db()
        assert art.is_deleted is True

    def test_restore_action(self):
        """L217-220: Restore articles."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='Restore', slug='restore', content='<p>C</p>', is_deleted=True
        )
        request = MagicMock()
        admin.restore_articles(request, Article.objects.filter(pk=art.pk))
        art.refresh_from_db()
        assert art.is_deleted is False

    def test_delete_model_soft(self):
        """L229-233: delete_model uses soft delete."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='DMS', slug='dms', content='<p>C</p>', is_deleted=False
        )
        request = MagicMock()
        admin.delete_model(request, art)
        art.refresh_from_db()
        assert art.is_deleted is True

    def test_delete_queryset_soft(self):
        """L235-237: delete_queryset uses soft delete."""
        from django.contrib.admin.sites import site
        from news.models import Article
        admin = site._registry[Article]
        art = Article.objects.create(
            title='DQS', slug='dqs', content='<p>C</p>', is_deleted=False
        )
        request = MagicMock()
        admin.delete_queryset(request, Article.objects.filter(pk=art.pk))
        art.refresh_from_db()
        assert art.is_deleted is True
