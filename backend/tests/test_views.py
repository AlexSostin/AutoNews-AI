"""
Tests for news/views.py — Django template views
Covers: article_detail (GET + POST comment), serve_media_with_cors, robots_txt
"""
import os
import pytest
from django.test import RequestFactory, override_settings
from django.http import Http404

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def published_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Test Article', slug='test-article',
        content='<p>Content</p>', summary='Summary',
        is_published=True, is_deleted=False,
    )


@pytest.fixture
def unpublished_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Draft', slug='draft-article',
        content='<p>Draft</p>', summary='Draft',
        is_published=False, is_deleted=False,
    )


@pytest.fixture
def deleted_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Deleted', slug='deleted-article',
        content='<p>Gone</p>', summary='Gone',
        is_published=True, is_deleted=True,
    )


@pytest.fixture
def media_dir(tmp_path):
    """Create a temp media dir with a test image file"""
    img = tmp_path / 'test.jpg'
    img.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)  # JPEG header
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════════
# article_detail — GET
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleDetailView:
    """Tests for article_detail(request, slug)"""

    def test_get_published_article(self, rf, published_article):
        from unittest.mock import patch, MagicMock
        from news.views import article_detail
        request = rf.get(f'/article/{published_article.slug}/')
        with patch('django.shortcuts.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            resp = article_detail(request, published_article.slug)
        assert resp.status_code == 200
        # Verify render was called with correct context
        ctx = mock_render.call_args[0][2]
        assert ctx['article'].slug == 'test-article'
        assert 'comments' in ctx

    def test_get_unpublished_returns_404(self, rf, unpublished_article):
        from news.views import article_detail
        request = rf.get(f'/article/{unpublished_article.slug}/')
        from django.http import Http404
        with pytest.raises(Http404):
            article_detail(request, unpublished_article.slug)

    def test_get_deleted_returns_404(self, rf, deleted_article):
        from news.views import article_detail
        request = rf.get(f'/article/{deleted_article.slug}/')
        from django.http import Http404
        with pytest.raises(Http404):
            article_detail(request, deleted_article.slug)

    def test_get_nonexistent_returns_404(self, rf):
        from news.views import article_detail
        request = rf.get('/article/no-such-slug/')
        from django.http import Http404
        with pytest.raises(Http404):
            article_detail(request, 'no-such-slug')

    def test_comments_in_context(self, rf, published_article):
        from unittest.mock import patch, MagicMock
        from news.models import Comment
        from news.views import article_detail
        # Approved comment
        Comment.objects.create(
            article=published_article, name='User',
            email='u@test.com', content='Great!', is_approved=True,
        )
        # Unapproved comment — should NOT appear
        Comment.objects.create(
            article=published_article, name='Spammer',
            email='s@test.com', content='Buy now!', is_approved=False,
        )
        request = rf.get(f'/article/{published_article.slug}/')
        with patch('django.shortcuts.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            article_detail(request, published_article.slug)
        ctx = mock_render.call_args[0][2]
        comments = list(ctx['comments'])
        assert len(comments) == 1
        assert comments[0].name == 'User'


# ═══════════════════════════════════════════════════════════════════════════
# article_detail — POST comment
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleDetailPostComment:
    """Tests for comment submission via article_detail POST"""

    def test_post_comment_creates_unapproved(self, rf, published_article):
        from news.views import article_detail
        request = rf.post(f'/article/{published_article.slug}/', {
            'name': 'Commenter',
            'email': 'commenter@test.com',
            'content': 'Nice article!',
        })
        # Need messages middleware
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))

        resp = article_detail(request, published_article.slug)
        # Should redirect back after success
        assert resp.status_code == 302

        from news.models import Comment
        comment = Comment.objects.filter(article=published_article).first()
        assert comment is not None
        assert comment.name == 'Commenter'
        assert comment.is_approved is False  # requires moderation

    def test_post_comment_missing_fields_renders_page(self, rf, published_article):
        from unittest.mock import patch, MagicMock
        from news.views import article_detail
        request = rf.post(f'/article/{published_article.slug}/', {
            'name': 'Commenter',
            # missing email and content
        })
        with patch('django.shortcuts.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            resp = article_detail(request, published_article.slug)
        # Should render the page (no redirect) since fields are missing
        assert resp.status_code == 200

        from news.models import Comment
        assert Comment.objects.filter(article=published_article).count() == 0

    def test_post_comment_missing_name(self, rf, published_article):
        from unittest.mock import patch, MagicMock
        from news.views import article_detail
        request = rf.post(f'/article/{published_article.slug}/', {
            'email': 'test@test.com',
            'content': 'Hello',
        })
        with patch('django.shortcuts.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            resp = article_detail(request, published_article.slug)
        assert resp.status_code == 200
        from news.models import Comment
        assert Comment.objects.filter(article=published_article).count() == 0

    def test_post_to_unpublished_returns_404(self, rf, unpublished_article):
        from news.views import article_detail
        request = rf.post(f'/article/{unpublished_article.slug}/', {
            'name': 'Hacker', 'email': 'h@h.com', 'content': 'test',
        })
        from django.http import Http404
        with pytest.raises(Http404):
            article_detail(request, unpublished_article.slug)



# ═══════════════════════════════════════════════════════════════════════════
# serve_media_with_cors
# ═══════════════════════════════════════════════════════════════════════════

class TestServeMediaWithCors:
    """Tests for serve_media_with_cors(request, path)"""

    def test_serve_existing_file(self, rf, media_dir):
        from news.views import serve_media_with_cors
        request = rf.get('/media/test.jpg')
        with override_settings(MEDIA_ROOT=str(media_dir)):
            resp = serve_media_with_cors(request, 'test.jpg')
        assert resp.status_code == 200
        assert resp['Access-Control-Allow-Origin'] == '*'
        assert resp['Content-Type'] == 'image/jpeg'

    def test_serve_nonexistent_file_404(self, rf, media_dir):
        from news.views import serve_media_with_cors
        request = rf.get('/media/nope.jpg')
        with override_settings(MEDIA_ROOT=str(media_dir)):
            with pytest.raises(Http404):
                serve_media_with_cors(request, 'nope.jpg')

    def test_cors_headers(self, rf, media_dir):
        from news.views import serve_media_with_cors
        request = rf.get('/media/test.jpg')
        with override_settings(MEDIA_ROOT=str(media_dir)):
            resp = serve_media_with_cors(request, 'test.jpg')
        assert resp['Access-Control-Allow-Methods'] == 'GET, OPTIONS'
        assert resp['Access-Control-Allow-Headers'] == 'Content-Type'

    def test_png_content_type(self, rf, tmp_path):
        from news.views import serve_media_with_cors
        png = tmp_path / 'icon.png'
        png.write_bytes(b'\x89PNG' + b'\x00' * 100)
        request = rf.get('/media/icon.png')
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            resp = serve_media_with_cors(request, 'icon.png')
        assert resp['Content-Type'] == 'image/png'

    def test_unknown_extension_no_override(self, rf, tmp_path):
        from news.views import serve_media_with_cors
        txt = tmp_path / 'readme.txt'
        txt.write_text('hello')
        request = rf.get('/media/readme.txt')
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            resp = serve_media_with_cors(request, 'readme.txt')
        assert resp.status_code == 200
        # Content-Type should NOT be overridden for unknown extensions
        assert resp['Access-Control-Allow-Origin'] == '*'


# ═══════════════════════════════════════════════════════════════════════════
# robots_txt
# ═══════════════════════════════════════════════════════════════════════════

class TestRobotsTxt:
    """Tests for robots_txt(request)"""

    def test_robots_txt_response(self, client):
        resp = client.get('/robots.txt')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/plain'

    def test_robots_txt_content(self, client):
        resp = client.get('/robots.txt')
        body = resp.content.decode()
        assert 'User-agent: *' in body
        assert 'Allow: /' in body
        assert 'Disallow: /admin/' in body
        assert 'Sitemap:' in body
        assert 'sitemap.xml' in body

    def test_robots_txt_disallows_api_admin(self, client):
        resp = client.get('/robots.txt')
        body = resp.content.decode()
        assert 'Disallow: /api/v1/admin/' in body
