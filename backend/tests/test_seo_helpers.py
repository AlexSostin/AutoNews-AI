"""
Unit tests for SEO helper functions
"""
import pytest
import sys
from pathlib import Path

# Add ai_engine to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'ai_engine'))

from modules.seo_helpers import generate_seo_keywords, extract_keywords_from_content


class TestGenerateSEOKeywords:
    """Tests for generate_seo_keywords function"""
    
    def test_basic_keyword_generation(self, sample_analysis):
        """Test basic keyword generation from analysis"""
        keywords = generate_seo_keywords(sample_analysis, "2024 Tesla Model 3 Review")
        
        assert isinstance(keywords, str)
        assert 'Tesla' in keywords
        assert 'Model 3' in keywords
        assert len(keywords.split(',')) <= 7  # Max 7 keywords
    
    def test_electric_vehicle_keywords(self):
        """Test EV-specific keywords"""
        analysis = {
            'make': 'Nissan',
            'model': 'Leaf',
            'year': 2024,
            'category': 'Electric Vehicle'
        }
        keywords = generate_seo_keywords(analysis, "Nissan Leaf")
        
        assert 'electric vehicle' in keywords.lower() or 'ev' in keywords.lower()
    
    def test_hybrid_keywords(self):
        """Test hybrid-specific keywords"""
        analysis = {
            'make': 'Toyota',
            'model': 'Prius',
            'category': 'Hybrid'
        }
        keywords = generate_seo_keywords(analysis, "Toyota Prius")
        
        assert 'hybrid' in keywords.lower()
    
    def test_suv_keywords(self):
        """Test SUV-specific keywords"""
        analysis = {
            'make': 'BMW',
            'model': 'X5',
            'category': 'Luxury SUV'
        }
        keywords = generate_seo_keywords(analysis, "BMW X5")
        
        assert 'suv' in keywords.lower()
    
    def test_unknown_values_handling(self):
        """Test handling of Unknown values"""
        analysis = {
            'make': 'Unknown',
            'model': 'Unknown',
            'category': 'General'
        }
        keywords = generate_seo_keywords(analysis, "Car Review")
        
        # Should still generate some keywords
        assert isinstance(keywords, str)
        assert len(keywords) > 0
    
    def test_empty_analysis(self):
        """Test with empty analysis dict"""
        keywords = generate_seo_keywords({}, "Test Title")
        
        # Should not crash
        assert isinstance(keywords, str)
    
    def test_string_analysis_safety(self):
        """Test that function handles string input gracefully (regression test)"""
        # This was the bug we fixed - analysis was a string
        keywords = generate_seo_keywords("not a dict", "Test Title")
        
        # Should not crash, just return empty or minimal keywords
        assert isinstance(keywords, str)


class TestExtractKeywordsFromContent:
    """Tests for extract_keywords_from_content function"""
    
    def test_basic_extraction(self):
        """Test basic keyword extraction"""
        content = "<p>Tesla Model 3 is an electric vehicle with great performance.</p>"
        keywords = extract_keywords_from_content(content, max_keywords=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        # HTML tags should be removed
        assert not any('</p>' in kw for kw in keywords)
    
    def test_stop_words_filtered(self):
        """Test that stop words are filtered out"""
        content = "The car is good and it has tested features."
        keywords = extract_keywords_from_content(content, max_keywords=10)
        
        # Common stop words should not appear
        stop_words = {'the', 'is', 'and', 'it', 'has'}
        for keyword in keywords:
            assert keyword not in stop_words
        
        # Content words should appear
        assert 'car' in keywords or 'good' in keywords or 'tested' in keywords or 'features' in keywords
    
    def test_html_tag_removal(self):
        """Test HTML tag removal"""
        content = "<h1>Title</h1><p>Content with <strong>bold</strong> text</p>"
        keywords = extract_keywords_from_content(content)
        
        # No HTML tags in keywords
        for keyword in keywords:
            assert '<' not in keyword
            assert '>' not in keyword
    
    def test_empty_content(self):
        """Test with empty content"""
        keywords = extract_keywords_from_content("")
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
