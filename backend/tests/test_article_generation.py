"""
Basic tests for article generation (without actual API calls)
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add ai_engine to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'ai_engine'))


class TestContentFormatting:
    """Tests for content formatting functions"""
    
    def test_distribute_images_basic(self):
        """Test basic image distribution"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>Para 1</p><p>Para 2</p><p>Para 3</p>'
        images = ['/img1.jpg']
        
        result = distribute_images_in_content(content, images)
        
        # Should contain the image
        assert '/img1.jpg' in result
        assert '<img' in result
    
    def test_distribute_multiple_images(self):
        """Test distributing multiple images"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>P1</p>' * 10
        images = ['/img1.jpg', '/img2.jpg', '/img3.jpg']
        
        result = distribute_images_in_content(content, images)
        
        # All images should be in content
        for img in images:
            assert img in result
    
    def test_distribute_images_no_content(self):
        """Test with empty content"""
        from modules.content_formatter import distribute_images_in_content
        
        result = distribute_images_in_content('', ['/img1.jpg'])
        
        # Should not crash
        assert isinstance(result, str)
    
    def test_distribute_images_no_images(self):
        """Test with no images"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>Para 1</p>'
        result = distribute_images_in_content(content, [])
        
        # Should return original content
        assert result == content

    """Tests for content formatting functions"""
    
    def test_distribute_images_basic(self):
        """Test basic image distribution"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>Para 1</p><p>Para 2</p><p>Para 3</p>'
        images = ['/img1.jpg']
        
        result = distribute_images_in_content(content, images)
        
        # Should contain the image
        assert '/img1.jpg' in result
        assert '<img' in result
    
    def test_distribute_multiple_images(self):
        """Test distributing multiple images"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>P1</p>' * 10
        images = ['/img1.jpg', '/img2.jpg', '/img3.jpg']
        
        result = distribute_images_in_content(content, images)
        
        # All images should be in content
        for img in images:
            assert img in result
    
    def test_distribute_images_no_content(self):
        """Test with empty content"""
        from modules.content_formatter import distribute_images_in_content
        
        result = distribute_images_in_content('', ['/img1.jpg'])
        
        # Should not crash
        assert isinstance(result, str)
    
    def test_distribute_images_no_images(self):
        """Test with no images"""
        from modules.content_formatter import distribute_images_in_content
        
        content = '<p>Para 1</p>'
        result = distribute_images_in_content(content, [])
        
        # Should return original content
        assert result == content


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
