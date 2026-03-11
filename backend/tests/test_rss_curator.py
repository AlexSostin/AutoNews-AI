"""
Tests for Smart RSS Curator — the AI-powered editorial assistant.

Covers:
  1. rss_curator engine (scan, cluster, score, ML preference)
  2. CuratorDecisionLog model
  3. API endpoints (curate, curator_decision, merge_generate)
"""

import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from news.models import (
    RSSNewsItem, RSSFeed, Article, Category, Brand,
    CuratorDecisionLog,
)


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

def _create_feed(**kwargs):
    defaults = dict(name='TestFeed', feed_url='https://example.com/feed.xml', is_enabled=True)
    defaults.update(kwargs)
    return RSSFeed.objects.create(**defaults)


def _create_rss_item(feed, **kwargs):
    defaults = dict(
        rss_feed=feed,
        title='Test RSS Item',
        content='Test content about cars',
        excerpt='Short excerpt',
        source_url='https://example.com/article',
        status='new',
    )
    defaults.update(kwargs)
    return RSSNewsItem.objects.create(**defaults)


def _create_article(**kwargs):
    defaults = dict(
        title='Published Article',
        slug='published-article',
        content='Published content',
        is_published=True,
    )
    defaults.update(kwargs)
    return Article.objects.create(**defaults)


# ----------------------------------------------------------------
# 1. RSS Curator Engine Tests
# ----------------------------------------------------------------

class TestScanItems(TestCase):
    """Step 1: Scan — loads correct items."""

    def setUp(self):
        self.feed = _create_feed()

    def test_scan_empty(self):
        from ai_engine.modules.rss_curator import _scan_items
        items = _scan_items(days=7)
        self.assertEqual(len(items), 0)

    def test_scan_filters_new_and_read(self):
        from ai_engine.modules.rss_curator import _scan_items
        _create_rss_item(self.feed, title='New item', status='new')
        _create_rss_item(self.feed, title='Read item', status='read')
        _create_rss_item(self.feed, title='Dismissed', status='dismissed')
        _create_rss_item(self.feed, title='Generated', status='generated')

        items = _scan_items(days=7)
        self.assertEqual(len(items), 2)
        titles = {i.title for i in items}
        self.assertIn('New item', titles)
        self.assertIn('Read item', titles)

    def test_scan_respects_days(self):
        from ai_engine.modules.rss_curator import _scan_items
        item = _create_rss_item(self.feed, title='Recent')
        # Manually set old created_at
        RSSNewsItem.objects.filter(id=item.id).update(
            created_at=timezone.now() - timedelta(days=30)
        )
        items = _scan_items(days=7)
        self.assertEqual(len(items), 0)


class TestClusterItems(TestCase):
    """Step 2: Cluster — groups similar items."""

    def test_empty(self):
        from ai_engine.modules.rss_curator import _cluster_items
        result = _cluster_items([])
        self.assertEqual(result, [])

    def test_single_item(self):
        from ai_engine.modules.rss_curator import _cluster_items
        feed = _create_feed()
        item = _create_rss_item(feed, title='BYD Seal launches in Europe')
        result = _cluster_items([item])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], [0])

    def test_similar_items_cluster_together(self):
        from ai_engine.modules.rss_curator import _cluster_items
        feed = _create_feed()
        items = [
            _create_rss_item(feed, title='BYD Seal 06 launches in Europe', excerpt='BYD Seal 06 European launch'),
            _create_rss_item(feed, title='BYD Seal 06 European launch date revealed', excerpt='BYD Seal 06 launch'),
            _create_rss_item(feed, title='Tesla Model Y gets new color options', excerpt='Tesla Model Y colors'),
        ]
        groups = _cluster_items(items, threshold=0.3)
        # BYD items should cluster, Tesla should be separate
        self.assertGreaterEqual(len(groups), 2)

    def test_different_items_stay_apart(self):
        from ai_engine.modules.rss_curator import _cluster_items
        feed = _create_feed()
        items = [
            _create_rss_item(feed, title='Apple releases new iPhone 16 Pro', excerpt='Apple smartphone'),
            _create_rss_item(feed, title='NASA discovers new exoplanet in habitable zone', excerpt='Space discovery'),
        ]
        groups = _cluster_items(items, threshold=0.45)
        # These should definitely be separate clusters
        self.assertEqual(len(groups), 2)


class TestScoreItem(TestCase):
    """Step 3: Score — multi-factor 0-100 relevance."""

    def setUp(self):
        self.feed = _create_feed()
        Brand.objects.create(name='BYD', slug='byd')
        Brand.objects.create(name='Tesla', slug='tesla')

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_brand_match_bonus(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='BYD Seal 06 launches', excerpt='New BYD model')
        known = {'BYD', 'Tesla'}
        result = _score_item(item, known)
        self.assertIn('brand_match', result['breakdown'])
        self.assertEqual(result['breakdown']['brand_match'], 25)
        self.assertEqual(result['brand'], 'BYD')

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_topic_bonus(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='All-new electric SUV revealed', excerpt='')
        result = _score_item(item, set())
        self.assertIn('topic_bonus', result['breakdown'])
        self.assertEqual(result['breakdown']['topic_bonus'], 15)

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_specs_bonus(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='Car with 600 km range', excerpt='and 300 hp power')
        result = _score_item(item, set())
        self.assertTrue(result['has_specs'])
        self.assertIn('specs_data', result['breakdown'])

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_multi_source_bonus(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='Hot news', excerpt='')
        item.source_count = 5
        item.save()
        result = _score_item(item, set())
        self.assertIn('multi_source', result['breakdown'])
        self.assertEqual(result['breakdown']['multi_source'], 15)

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate')
    def test_duplicate_penalty(self, mock_dup, mock_pref):
        mock_dup.return_value = {'article_id': 42, 'title': 'Existing Article'}
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='Duplicate content', excerpt='')
        result = _score_item(item, set())
        self.assertIn('duplicate_penalty', result['breakdown'])
        self.assertEqual(result['duplicate_of'], 42)

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_low_editorial_penalty(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='CEO appoints new CTO', excerpt='')
        result = _score_item(item, set())
        self.assertIn('low_editorial', result['breakdown'])
        self.assertEqual(result['breakdown']['low_editorial'], -10)

    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    def test_score_clamped_0_100(self, mock_dup, mock_pref):
        from ai_engine.modules.rss_curator import _score_item
        item = _create_rss_item(self.feed, title='Nothing special', excerpt='')
        result = _score_item(item, set())
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)


class TestPreferenceScore(TestCase):
    """ML learning loop — preference score from CuratorDecisionLog."""

    def test_no_history_returns_zero(self):
        from ai_engine.modules.rss_curator import _compute_preference_score
        score = _compute_preference_score('Some title', 'Some excerpt')
        self.assertEqual(score, 0)

    def test_with_few_approvals(self):
        """Less than 5 approvals → returns 0 (not enough data)."""
        from ai_engine.modules.rss_curator import _compute_preference_score
        feed = _create_feed()
        for i in range(3):
            item = _create_rss_item(feed, title=f'Approved item {i}')
            CuratorDecisionLog.objects.create(
                news_item=item, decision='generate', title_text=item.title,
            )
        score = _compute_preference_score('Another title', 'Another excerpt')
        self.assertEqual(score, 0)


# ----------------------------------------------------------------
# 2. CuratorDecisionLog Model Tests
# ----------------------------------------------------------------

class TestCuratorDecisionLog(TestCase):
    """Test the ML feedback model."""

    def setUp(self):
        self.feed = _create_feed()
        self.item = _create_rss_item(self.feed, title='Test item for decisions')

    def test_create_generate_decision(self):
        log = CuratorDecisionLog.objects.create(
            news_item=self.item,
            decision='generate',
            curator_score=85,
            brand='BYD',
            title_text=self.item.title,
        )
        self.assertEqual(log.decision, 'generate')
        self.assertEqual(log.curator_score, 85)
        self.assertEqual(str(log), '[generate] Test item for decisions')

    def test_create_skip_decision(self):
        log = CuratorDecisionLog.objects.create(
            news_item=self.item,
            decision='skip',
            curator_score=20,
            title_text=self.item.title,
        )
        self.assertEqual(log.decision, 'skip')

    def test_create_merge_decision(self):
        log = CuratorDecisionLog.objects.create(
            news_item=self.item,
            decision='merge',
            cluster_id='cluster_0',
            title_text=self.item.title,
        )
        self.assertEqual(log.cluster_id, 'cluster_0')

    def test_generated_article_fk(self):
        article = _create_article(title='Generated from curator', slug='gen-curator')
        log = CuratorDecisionLog.objects.create(
            news_item=self.item,
            decision='generate',
            generated_article=article,
            title_text=self.item.title,
        )
        self.assertEqual(log.generated_article_id, article.id)


# ----------------------------------------------------------------
# 3. API Endpoint Tests
# ----------------------------------------------------------------

class TestCuratorAPI(APITestCase):
    """Test /rss-news-items/curate/ and /curator_decision/ endpoints."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='curator_admin', password='pass1234', email='admin@test.com'
        )
        self.client.force_authenticate(user=self.admin)
        self.feed = _create_feed()

    @patch('ai_engine.modules.rss_curator._generate_cluster_summary')
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    def test_curate_returns_clusters(self, mock_pref, mock_dup, mock_summary):
        mock_summary.return_value = {
            'topic': 'Test Topic',
            'suggestion': 'Good article candidate',
            'merge_recommended': False,
        }

        _create_rss_item(self.feed, title='BYD Seal first drive review', excerpt='BYD Seal test')
        _create_rss_item(self.feed, title='Tesla Model Y refresh', excerpt='Tesla refresh')

        res = self.client.post('/api/v1/rss-news-items/curate/', {
            'days': 7,
            'include_ai_summary': True,
        }, format='json')

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertEqual(res.data['items_scanned'], 2)
        self.assertIsInstance(res.data['clusters'], list)
        self.assertIn('stats', res.data)

    @patch('ai_engine.modules.rss_curator._generate_cluster_summary')
    @patch('ai_engine.modules.rss_curator._check_duplicate', return_value=None)
    @patch('ai_engine.modules.rss_curator._compute_preference_score', return_value=0)
    def test_curate_empty_feed(self, mock_pref, mock_dup, mock_summary):
        res = self.client.post('/api/v1/rss-news-items/curate/', {
            'days': 7,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['items_scanned'], 0)
        self.assertEqual(res.data['clusters'], [])

    def test_curator_decision_generate(self):
        item = _create_rss_item(self.feed, title='Item to generate')

        with patch.object(
            type(self.client), 'post',
            wraps=self.client.post,
        ):
            res = self.client.post('/api/v1/rss-news-items/curator_decision/', {
                'item_id': item.id,
                'decision': 'skip',
                'cluster_id': 'cluster_0',
                'score': 75,
                'brand': 'BYD',
            }, format='json')

        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['success'])
        self.assertEqual(res.data['decision'], 'skip')

        # Verify log was created
        log = CuratorDecisionLog.objects.get(news_item=item)
        self.assertEqual(log.decision, 'skip')
        self.assertEqual(log.curator_score, 75)
        self.assertEqual(log.brand, 'BYD')

        # Verify item was dismissed
        item.refresh_from_db()
        self.assertEqual(item.status, 'dismissed')

    def test_curator_decision_invalid(self):
        item = _create_rss_item(self.feed, title='Test')
        res = self.client.post('/api/v1/rss-news-items/curator_decision/', {
            'item_id': item.id,
            'decision': 'invalid_choice',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_curator_decision_missing_item(self):
        res = self.client.post('/api/v1/rss-news-items/curator_decision/', {
            'item_id': 99999,
            'decision': 'skip',
        }, format='json')
        self.assertEqual(res.status_code, 404)

    def test_merge_generate_too_few(self):
        item = _create_rss_item(self.feed, title='Solo item')
        res = self.client.post('/api/v1/rss-news-items/merge_generate/', {
            'ids': [item.id],
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('At least 2', res.data['error'])

    def test_merge_generate_too_many(self):
        items = [_create_rss_item(self.feed, title=f'Item {i}') for i in range(6)]
        res = self.client.post('/api/v1/rss-news-items/merge_generate/', {
            'ids': [i.id for i in items],
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Maximum 5', res.data['error'])

    def test_curate_requires_authentication(self):
        self.client.force_authenticate(user=None)
        res = self.client.post('/api/v1/rss-news-items/curate/', {}, format='json')
        self.assertIn(res.status_code, [401, 403])
