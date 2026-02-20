"""
Tests for content_formatter module — distribute_images_in_content.
"""
import pytest
from ai_engine.modules.content_formatter import distribute_images_in_content


class TestContentFormatter:
    """Tests for HTML image distribution"""

    def test_distribute_no_images(self):
        """No images should return content unchanged"""
        html = '<h2>Title</h2><p>Content here.</p>'
        result = distribute_images_in_content(html, [])
        assert result == html

    def test_distribute_single_image(self):
        """Single image should be inserted into content"""
        html = '<p>Para 1</p><p>Para 2</p><p>Para 3</p><p>Para 4</p>'
        result = distribute_images_in_content(html, ['https://example.com/img1.jpg'])
        assert 'img1.jpg' in result
        assert '<img ' in result

    def test_distribute_multiple_images(self):
        """Multiple images should be distributed evenly"""
        html = '<p>P1</p><p>P2</p><p>P3</p><p>P4</p><p>P5</p><p>P6</p>'
        result = distribute_images_in_content(html, [
            'https://example.com/img1.jpg',
            'https://example.com/img2.jpg',
        ])
        assert 'img1.jpg' in result
        assert 'img2.jpg' in result

    def test_distribute_empty_content(self):
        """Empty content should return empty"""
        result = distribute_images_in_content('', ['https://example.com/img1.jpg'])
        assert result == ''
