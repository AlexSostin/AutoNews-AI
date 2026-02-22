"""
Tests for Tier 1 utility modules:
- auto_tags.py (smart tagging pipeline)
- feeds.py (RSS/Atom feeds)
- email_service.py (SendGrid email)
- image_utils.py (WebP conversion)
- site_settings.py (singleton settings)
"""
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# auto_tags.py
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeTagName:

    def test_known_brand(self):
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('Tesla')
        assert name == 'Tesla'
        assert group == 'Manufacturers'

    def test_fuel_type(self):
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('ev')
        assert name == 'EV'
        assert group == 'Fuel Types'

    def test_stop_word_rejected(self):
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('the')
        assert name is None

    def test_alias_resolution(self):
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('electric vehicle')
        assert name == 'EV'

    def test_body_type(self):
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('SUV')
        assert name == 'SUV'


class TestFindOrCreateTag:

    def test_creates_new_tag(self):
        from news.auto_tags import find_or_create_tag
        tag, created = find_or_create_tag('ZEEKR', 'Manufacturers')
        assert created is True
        assert tag.name == 'ZEEKR'

    def test_finds_existing_tag(self):
        from news.auto_tags import find_or_create_tag
        find_or_create_tag('BMW', 'Manufacturers')
        tag, created = find_or_create_tag('BMW', 'Manufacturers')
        assert created is False

    def test_assigns_group(self):
        from news.auto_tags import find_or_create_tag
        from news.models import TagGroup
        tag, _ = find_or_create_tag('EV', 'Fuel Types')
        assert tag.group is not None
        assert tag.group.name == 'Fuel Types'


class TestExtractTagsFromStructuredData:

    def test_extracts_from_car_spec(self):
        from news.auto_tags import extract_tags_from_structured_data
        from news.models import Article, CarSpecification
        art = Article.objects.create(title='T', slug='struct-tag', content='c')
        CarSpecification.objects.create(article=art, make='Tesla', model='Model 3')
        tags = extract_tags_from_structured_data(art)
        tag_names = [t[0].lower() for t in tags]
        assert any('tesla' in n for n in tag_names)


class TestExtractTagsFromTitle:

    def test_extracts_brand_from_title(self):
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        art = Article.objects.create(
            title='New Tesla Model Y Review 2026',
            slug='title-tag', content='Electric SUV content',
        )
        tags = extract_tags_from_title(art)
        tag_names = [t[0].lower() for t in tags]
        assert any('tesla' in n for n in tag_names)


class TestAutoTagArticle:

    def test_tags_article_without_ai(self):
        from news.auto_tags import auto_tag_article
        from news.models import Article, CarSpecification
        art = Article.objects.create(
            title='BMW iX xDrive50 Review', slug='auto-tag-test',
            content='BMW electric SUV review content here.',
        )
        CarSpecification.objects.create(article=art, make='BMW', model='iX')
        result = auto_tag_article(art, use_ai=False)
        assert 'total' in result
        assert result['total'] >= 0

    @patch('news.auto_tags.extract_tags_with_ai')
    def test_tags_article_with_ai(self, mock_ai):
        from news.auto_tags import auto_tag_article
        from news.models import Article
        mock_ai.return_value = [('Autonomous', 'Tech & Features')]
        art = Article.objects.create(
            title='Self-driving car news', slug='ai-tag-test',
            content='Content about autonomous driving.',
        )
        result = auto_tag_article(art, use_ai=True)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# feeds.py
# ═══════════════════════════════════════════════════════════════════════════

class TestFeeds:

    def test_latest_rss_feed(self):
        from news.models import Article
        Article.objects.create(
            title='Feed Article', slug='feed-art',
            content='Content', is_published=True,
        )
        factory = RequestFactory()
        request = factory.get('/feed/rss/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        from news.feeds import LatestArticlesFeed
        feed = LatestArticlesFeed()
        items = feed.items()
        assert items.count() >= 1

    def test_feed_item_methods(self):
        from news.models import Article
        art = Article.objects.create(
            title='Feed Item', slug='feed-item',
            content='Content here', summary='Summary', is_published=True,
        )
        from news.feeds import LatestArticlesFeed
        feed = LatestArticlesFeed()
        assert feed.item_title(art) == 'Feed Item'
        assert 'Summary' in feed.item_description(art)
        assert feed.item_pubdate(art) == art.created_at
        assert feed.item_updateddate(art) == art.updated_at
        assert feed.item_enclosure_mime_type(art) == 'image/webp'

    def test_feed_no_image(self):
        from news.models import Article
        art = Article.objects.create(
            title='No Image', slug='no-img',
            content='Content', is_published=True,
        )
        from news.feeds import LatestArticlesFeed
        feed = LatestArticlesFeed()
        assert feed.item_enclosure_url(art) is None
        assert feed.item_enclosure_length(art) == 0

    def test_category_feed(self):
        from news.models import Article, Category
        cat = Category.objects.create(name='EVs', slug='evs')
        art = Article.objects.create(
            title='EV Article', slug='ev-art',
            content='EV content', is_published=True,
        )
        art.categories.add(cat)
        from news.feeds import CategoryFeed
        feed = CategoryFeed()
        assert feed.title(cat) == 'AutoNews - EVs Articles'


# ═══════════════════════════════════════════════════════════════════════════
# email_service.py
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailService:

    def test_no_api_key(self):
        from news.email_service import EmailService
        with patch.dict('os.environ', {}, clear=True):
            svc = EmailService()
            assert svc.client is None
            result = svc.send_email('test@test.com', 'Hi', '<p>Hello</p>')
            assert result is False

    @patch('news.email_service.SendGridAPIClient')
    def test_send_email_success(self, mock_sg):
        from news.email_service import EmailService
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        mock_sg.return_value = mock_client
        with patch.dict('os.environ', {'SENDGRID_API_KEY': 'test-key'}):
            svc = EmailService()
            result = svc.send_email('user@test.com', 'Subject', '<p>Body</p>')
            assert result is True

    @patch('news.email_service.SendGridAPIClient')
    def test_send_email_failure(self, mock_sg):
        from news.email_service import EmailService
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception('API error')
        mock_sg.return_value = mock_client
        with patch.dict('os.environ', {'SENDGRID_API_KEY': 'test-key'}):
            svc = EmailService()
            result = svc.send_email('user@test.com', 'Subject', '<p>Body</p>')
            assert result is False

    @patch('news.email_service.SendGridAPIClient')
    def test_newsletter_welcome(self, mock_sg):
        from news.email_service import EmailService
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        mock_sg.return_value = mock_client
        with patch.dict('os.environ', {'SENDGRID_API_KEY': 'test-key'}):
            svc = EmailService()
            result = svc.send_newsletter_welcome('newcomer@test.com')
            assert result is True


# ═══════════════════════════════════════════════════════════════════════════
# image_utils.py
# ═══════════════════════════════════════════════════════════════════════════

def _make_test_image(mode='RGB', size=(100, 100), fmt='PNG'):
    """Create a test image file."""
    img = Image.new(mode, size, color='red')
    buf = BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(f'test.{fmt.lower()}', buf.read(), content_type=f'image/{fmt.lower()}')


class TestImageUtils:

    def test_convert_to_webp(self):
        from news.image_utils import convert_to_webp
        img_file = _make_test_image()
        result = convert_to_webp(img_file)
        assert result.name.endswith('.webp')

    def test_convert_rgba_to_webp(self):
        from news.image_utils import convert_to_webp
        img_file = _make_test_image(mode='RGBA')
        result = convert_to_webp(img_file)
        assert result.name.endswith('.webp')

    def test_optimize_image(self):
        from news.image_utils import optimize_image
        img_file = _make_test_image(size=(3000, 2000))
        result = optimize_image(img_file, max_width=1920, max_height=1080)
        assert result.name.endswith('.webp')

    def test_optimize_small_image(self):
        from news.image_utils import optimize_image
        img_file = _make_test_image(size=(200, 100))
        result = optimize_image(img_file, max_width=1920, max_height=1080)
        assert result.name.endswith('.webp')

    def test_convert_invalid_file(self):
        from news.image_utils import convert_to_webp
        bad_file = SimpleUploadedFile('bad.png', b'not an image', content_type='image/png')
        result = convert_to_webp(bad_file)
        # Should return original file on error
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# site_settings.py
# ═══════════════════════════════════════════════════════════════════════════

class TestSiteSettings:

    def test_load_creates_instance(self):
        from news.models import SiteSettings
        settings = SiteSettings.load()
        assert settings.pk == 1
        assert settings.site_name is not None  # May be 'AutoNews' or 'Fresh Motors'

    def test_singleton_pattern(self):
        from news.models import SiteSettings
        s1 = SiteSettings.load()
        s2 = SiteSettings.load()
        assert s1.pk == s2.pk == 1

    def test_save_forces_pk_1(self):
        from news.models import SiteSettings
        obj = SiteSettings(site_name='Custom')
        obj.save()
        assert obj.pk == 1

    def test_str(self):
        from news.models import SiteSettings
        settings = SiteSettings.load()
        assert str(settings) == 'Site Settings'
