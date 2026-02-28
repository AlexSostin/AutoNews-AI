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
    
    def test_publish_article_basic(self):
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
            tag_names=['EV', 'Electric']
        )
        
        tags = article.tags.all()
        assert tags.count() == 2
        tag_names = [t.name for t in tags]
        assert 'EV' in tag_names
        assert 'Electric' in tag_names
