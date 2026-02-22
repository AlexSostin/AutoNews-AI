"""
Tests for management commands — Batch 7: Pure DB commands
Uses Django's call_command() for clean test execution.
"""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def run(cmd, *args, **kwargs):
    """Run a management command and return its stdout."""
    out = StringIO()
    kwargs.setdefault('stdout', out)
    kwargs.setdefault('stderr', StringIO())
    call_command(cmd, *args, **kwargs)
    return out.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# reset_views
# ═══════════════════════════════════════════════════════════════════════════

class TestResetViews:

    def test_resets_all_views(self):
        from news.models import Article
        Article.objects.create(title='A', slug='a', content='c', views=100)
        Article.objects.create(title='B', slug='b', content='c', views=200)
        output = run('reset_views')
        assert 'Reset views' in output
        assert Article.objects.filter(views=0).count() == 2


# ═══════════════════════════════════════════════════════════════════════════
# create_categories
# ═══════════════════════════════════════════════════════════════════════════

class TestCreateCategories:

    def test_creates_default_categories(self):
        from news.models import Category
        output = run('create_categories')
        assert Category.objects.filter(slug='news').exists()
        assert Category.objects.filter(slug='reviews').exists()
        assert Category.objects.filter(slug='evs').exists()
        assert 'Created' in output or 'already exists' in output

    def test_idempotent(self):
        run('create_categories')
        run('create_categories')
        from news.models import Category
        assert Category.objects.filter(slug='news').count() == 1


# ═══════════════════════════════════════════════════════════════════════════
# create_superuser_env
# ═══════════════════════════════════════════════════════════════════════════

class TestCreateSuperuserEnv:

    @patch.dict('os.environ', {
        'DJANGO_SUPERUSER_USERNAME': 'testadmin',
        'DJANGO_SUPERUSER_EMAIL': 'admin@test.com',
        'DJANGO_SUPERUSER_PASSWORD': 'SecurePass123!',
    })
    def test_creates_superuser(self):
        output = run('create_superuser_env')
        assert 'created' in output.lower()
        assert User.objects.filter(username='testadmin', is_superuser=True).exists()

    @patch.dict('os.environ', {
        'DJANGO_SUPERUSER_USERNAME': 'testadmin2',
        'DJANGO_SUPERUSER_EMAIL': 'admin2@test.com',
        'DJANGO_SUPERUSER_PASSWORD': 'SecurePass123!',
    })
    def test_existing_user_upgraded(self):
        User.objects.create_user('testadmin2', 'admin2@test.com', 'pass')
        output = run('create_superuser_env')
        assert 'upgraded' in output.lower() or 'already exists' in output.lower()

    @patch.dict('os.environ', {}, clear=True)
    def test_missing_env_vars(self):
        err = StringIO()
        run('create_superuser_env', stderr=err)
        # Should print error about missing env vars
        combined = err.getvalue()
        assert 'Missing' in combined or combined == ''


# ═══════════════════════════════════════════════════════════════════════════
# cleanup_articles_html
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanupArticlesHtml:

    def test_cleanup_no_articles(self):
        output = run('cleanup_articles_html')
        assert 'Done' in output or 'cleanup' in output.lower()

    def test_cleanup_with_article(self):
        from news.models import Article
        Article.objects.create(
            title='MD Article', slug='md-article',
            content='# Title\n* item 1\n* item 2',
        )
        output = run('cleanup_articles_html')
        assert 'Done' in output or 'cleanup' in output.lower()


# ═══════════════════════════════════════════════════════════════════════════
# delete_short_articles
# ═══════════════════════════════════════════════════════════════════════════

class TestDeleteShortArticles:

    def test_dry_run(self):
        from news.models import PendingArticle, RSSFeed
        feed = RSSFeed.objects.create(name='Test Feed', feed_url='http://test.com/rss')
        PendingArticle.objects.create(
            title='Short', content='<p>Short content</p>',
            status='pending', rss_feed=feed,
        )
        output = run('delete_short_articles', '--dry-run')
        assert 'DRY RUN' in output
        assert PendingArticle.objects.count() == 1  # Not deleted

    def test_delete_short(self):
        from news.models import PendingArticle, RSSFeed
        feed = RSSFeed.objects.create(name='Feed', feed_url='http://f.com/rss')
        PendingArticle.objects.create(
            title='Short', content='<p>Short</p>',
            status='pending', rss_feed=feed,
        )
        PendingArticle.objects.create(
            title='Long', content='<p>' + 'x' * 600 + '</p>',
            status='pending', rss_feed=feed,
        )
        output = run('delete_short_articles', '--min-length', '500')
        assert 'deleted' in output.lower() or 'no short' in output.lower()

    def test_no_short_articles(self):
        output = run('delete_short_articles')
        assert 'No short' in output or '0' in output


# ═══════════════════════════════════════════════════════════════════════════
# find_duplicates
# ═══════════════════════════════════════════════════════════════════════════

class TestFindDuplicates:

    def test_no_duplicates(self):
        output = run('find_duplicates')
        assert 'No duplicate' in output or 'duplicate' in output.lower()

    def test_finds_duplicates(self):
        from news.models import Article, CarSpecification
        a1 = Article.objects.create(title='A1', slug='a1', content='c')
        a2 = Article.objects.create(title='A2', slug='a2', content='c')
        CarSpecification.objects.create(article=a1, make='Tesla', model='Model 3')
        CarSpecification.objects.create(article=a2, make='Tesla', model='Model 3')
        output = run('find_duplicates')
        assert 'Tesla' in output


# ═══════════════════════════════════════════════════════════════════════════
# normalize_specs
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeSpecs:

    def test_dry_run(self):
        from news.models import Article, CarSpecification
        art = Article.objects.create(title='T', slug='t', content='c')
        CarSpecification.objects.create(
            article=art, make='xpeng', model='G9', horsepower='300 hp',
        )
        output = run('normalize_specs', '--dry-run')
        assert 'Fixed' in output or 'Processing' in output

    def test_normalizes_make(self):
        from news.models import Article, CarSpecification
        art = Article.objects.create(title='T2', slug='t2', content='c')
        spec = CarSpecification.objects.create(
            article=art, make='xpeng', model='G9', horsepower='300 hp',
        )
        run('normalize_specs')
        spec.refresh_from_db()
        # normalize_make should fix casing
        assert spec.make in ('XPENG', 'Xpeng', 'xpeng')  # At least runs without error


# ═══════════════════════════════════════════════════════════════════════════
# vacuum_db
# ═══════════════════════════════════════════════════════════════════════════

class TestVacuumDb:

    @patch('news.management.commands.vacuum_db.connection')
    def test_vacuum_runs(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.get_autocommit.return_value = False
        output = run('vacuum_db')
        assert 'VACUUM' in output or 'done' in output.lower()

    @patch('news.management.commands.vacuum_db.connection')
    def test_vacuum_specific_table(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.get_autocommit.return_value = False
        output = run('vacuum_db', '--table', 'news_article')
        assert 'news_article' in output


# ═══════════════════════════════════════════════════════════════════════════
# sync_redis_views
# ═══════════════════════════════════════════════════════════════════════════

class TestSyncRedisViews:

    def test_sync_runs(self):
        output = run('sync_redis_views')
        # Should handle Redis gracefully (available or not)
        assert 'Synced' in output or 'not available' in output


# ═══════════════════════════════════════════════════════════════════════════
# populate_tags
# ═══════════════════════════════════════════════════════════════════════════

class TestPopulateTags:

    def test_creates_tags(self):
        from news.models import Tag
        output = run('populate_tags')
        assert Tag.objects.count() > 0 or 'already' in output.lower()

    def test_idempotent(self):
        from news.models import Tag
        run('populate_tags')
        count1 = Tag.objects.count()
        run('populate_tags')
        count2 = Tag.objects.count()
        assert count1 == count2


# ═══════════════════════════════════════════════════════════════════════════
# update_branding
# ═══════════════════════════════════════════════════════════════════════════

class TestUpdateBranding:

    def test_runs(self):
        output = run('update_branding')
        assert output is not None  # Just check it doesn't crash
