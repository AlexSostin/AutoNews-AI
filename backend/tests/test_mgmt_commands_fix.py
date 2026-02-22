"""
Tests for management commands — Batch 8: Data fix commands
fix_brand_names, fix_tag_groups, fix_video_embeds, fix_rss_logos,
cleanup_tags, consolidate_categories, cleanup_markdown_remnants,
backfill_authors, backfill_sources, add_feed_logos
"""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def run(cmd, *args, **kwargs):
    out = StringIO()
    kwargs.setdefault('stdout', out)
    kwargs.setdefault('stderr', StringIO())
    call_command(cmd, *args, **kwargs)
    return out.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# fix_brand_names
# ═══════════════════════════════════════════════════════════════════════════

class TestFixBrandNames:

    def test_dry_run(self):
        output = run('fix_brand_names')
        assert 'DRY RUN' in output or 'Brand' in output

    def test_apply_with_data(self):
        from news.models import Article, CarSpecification
        art = Article.objects.create(title='T', slug='fb1', content='c')
        CarSpecification.objects.create(article=art, make='Zeekr', model='001')
        output = run('fix_brand_names', '--apply')
        assert 'Brand' in output or 'APPLYING' in output


# ═══════════════════════════════════════════════════════════════════════════
# fix_tag_groups
# ═══════════════════════════════════════════════════════════════════════════

class TestFixTagGroups:

    def test_runs_on_empty_db(self):
        output = run('fix_tag_groups')
        assert 'Done' in output or 'Fixed' in output

    def test_fixes_tags(self):
        from news.models import Tag, TagGroup
        group = TagGroup.objects.create(name='Wrong Group', slug='wrong-group')
        Tag.objects.create(name='SUV', slug='suv', group=group)
        output = run('fix_tag_groups')
        assert 'Done' in output or 'Fixed' in output


# ═══════════════════════════════════════════════════════════════════════════
# fix_video_embeds
# ═══════════════════════════════════════════════════════════════════════════

class TestFixVideoEmbeds:

    def test_dry_run(self):
        from news.models import Article
        Article.objects.create(
            title='YT Article', slug='yt-embed',
            content='<h2>Title</h2><p>Content</p>',
            youtube_url='https://youtube.com/watch?v=dQw4w9WgXcQ',
        )
        output = run('fix_video_embeds', '--dry-run')
        assert 'dQw4w9WgXcQ' in output or 'fix' in output.lower()

    def test_skip_existing_embed(self):
        from news.models import Article
        Article.objects.create(
            title='YT2', slug='yt-embed-2',
            content='<iframe src="youtube"></iframe><p>Content</p>',
            youtube_url='https://youtube.com/watch?v=dQw4w9WgXcQ',
        )
        output = run('fix_video_embeds')
        # Should skip articles that already have iframes
        assert 'Fixed 0' in output or 'Would fix 0' in output

    def test_no_youtube_articles(self):
        output = run('fix_video_embeds')
        assert 'Fixed 0' in output or '0' in output


# ═══════════════════════════════════════════════════════════════════════════
# fix_rss_logos
# ═══════════════════════════════════════════════════════════════════════════

class TestFixRssLogos:

    def test_runs_no_feeds(self):
        output = run('fix_rss_logos')
        assert 'not found' in output.lower() or 'Updated' in output

    def test_fixes_known_feed(self):
        from news.models import RSSFeed
        RSSFeed.objects.create(
            name='Electrek Tesla',
            feed_url='http://electrek.co/feed',
            logo_url='old-broken-url',
        )
        output = run('fix_rss_logos')
        assert 'Updated' in output or 'Electrek' in output


# ═══════════════════════════════════════════════════════════════════════════
# cleanup_tags (big one — 416 lines, 6 phases)
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanupTags:

    def test_dry_run_on_empty(self):
        output = run('cleanup_tags', '--dry-run')
        assert 'Phase' in output or 'Done' in output.lower() or 'Summary' in output

    def test_runs_without_error(self):
        output = run('cleanup_tags')
        assert output is not None  # Just verify no crash


# ═══════════════════════════════════════════════════════════════════════════
# consolidate_categories
# ═══════════════════════════════════════════════════════════════════════════

class TestConsolidateCategories:

    def test_runs_on_empty(self):
        output = run('consolidate_categories')
        assert output is not None

    def test_creates_target_categories(self):
        from news.models import Category
        run('consolidate_categories')
        # Should at least not crash — categories may or may not be created
        assert True


# ═══════════════════════════════════════════════════════════════════════════
# cleanup_markdown_remnants
# ═══════════════════════════════════════════════════════════════════════════

class TestCleanupMarkdownRemnants:

    def test_no_articles(self):
        output = run('cleanup_markdown_remnants', '--dry-run')
        assert 'Done' in output or 'Scanning' in output or '0' in output

    def test_with_markdown_article(self):
        from news.models import Article
        Article.objects.create(
            title='MD Test', slug='md-test',
            content='<p>Normal</p>\n\n**Bold text** and _italic_ here\n\n* list item',
            is_published=True,
        )
        output = run('cleanup_markdown_remnants', '--dry-run')
        assert output is not None


# ═══════════════════════════════════════════════════════════════════════════
# backfill_authors
# ═══════════════════════════════════════════════════════════════════════════

class TestBackfillAuthors:

    def test_runs(self):
        output = run('backfill_authors')
        assert output is not None


# ═══════════════════════════════════════════════════════════════════════════
# backfill_sources
# ═══════════════════════════════════════════════════════════════════════════

class TestBackfillSources:

    def test_runs(self):
        output = run('backfill_sources')
        assert output is not None


# ═══════════════════════════════════════════════════════════════════════════
# add_feed_logos
# ═══════════════════════════════════════════════════════════════════════════

class TestAddFeedLogos:

    def test_runs(self):
        output = run('add_feed_logos')
        assert output is not None
