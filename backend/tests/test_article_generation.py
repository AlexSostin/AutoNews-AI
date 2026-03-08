"""
Basic tests for article generation (without actual API calls)
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.django_db
class TestArticlePublishing:
    """Tests for article publishing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup category"""
        from news.models import Category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
    
    @patch('ai_engine.modules.scoring.ai_detection_checks', return_value={
        'score': 100, 'recommendation': 'pass', 'issues': []
    })
    def test_publish_article_basic(self, mock_gate):
        """Test basic article publishing"""
        from ai_engine.modules.publisher import publish_article
        
        article = publish_article(
            title='Test Article',
            content='<p>Test content</p>',
            summary='Test summary',
            category_name='Test Category',
            meta_keywords='test, article'
        )
        
        assert article is not None
        assert article.title == 'Test Article'
        assert article.is_published is True
        assert article.meta_keywords == 'test, article'
    
    def test_publish_article_with_tags(self):
        """Test publishing with tags"""
        from ai_engine.modules.publisher import publish_article
        from news.models import Tag
        
        article = publish_article(
            title='Tagged Article',
            content='<p>Content</p>',
            summary='Summary',
            category_name='Test Category',
            tag_names=['EV', 'Electric'],
            is_published=False  # skip quality gate
        )
        
        tags = article.tags.all()
        assert tags.count() == 2
        tag_names = [t.name for t in tags]
        assert 'EV' in tag_names
        assert 'Electric' in tag_names
    
    @patch('ai_engine.modules.scoring.ai_detection_checks', return_value={
        'score': 30, 'recommendation': 'reject', 'issues': ['AI filler detected']
    })
    def test_quality_gate_rejects_low_quality(self, mock_gate):
        """Quality Gate should draft articles with low scores"""
        from ai_engine.modules.publisher import publish_article
        
        article = publish_article(
            title='Bad Quality Article',
            content='<p>Low quality content</p>',
            summary='Bad summary',
            category_name='Test Category',
        )
        
        assert article is not None
        # Quality Gate should have marked it as draft
        article.refresh_from_db()
        assert article.is_published is False
        # Gate result stored in generation_metadata
        gate = article.generation_metadata.get('quality_gate', {})
        assert gate.get('score') == 30
        assert gate.get('recommendation') == 'reject'
