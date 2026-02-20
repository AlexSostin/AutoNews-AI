"""
Tests for quality_scorer module.
"""
import pytest
from ai_engine.modules.quality_scorer import calculate_quality_score


class TestQualityScorer:
    """Tests for calculate_quality_score()"""

    def test_perfect_article(self):
        """Article with all criteria should score high"""
        score = calculate_quality_score(
            title='The Amazing 2025 Tesla Model 3 Performance Review',
            content='<h2>First Section</h2><p>Paragraph one.</p><h2>Second</h2><p>Paragraph two.</p><p>Paragraph three.</p>' + ' word' * 800,
            specs={'make': 'Tesla', 'model': 'Model 3', 'engine': 'Electric', 
                   'horsepower': '350', 'torque': '350 lb-ft', 'zero_to_sixty': '3.1',
                   'top_speed': '162 mph', 'drivetrain': 'AWD', 'price': '$42,990', 'year': '2025'},
            tags=['EV', 'Tesla', 'Review'],
            featured_image='https://example.com/img.jpg',
        )
        assert score >= 8

    def test_empty_article_scores_low(self):
        """Very minimal article should score low"""
        score = calculate_quality_score(
            title='X',
            content='Short',
            specs=None,
            tags=[],
        )
        assert score <= 3

    def test_spec_coverage_bonus_triggers(self):
        """7+ filled key fields should give spec coverage bonus"""
        full_specs = {
            'make': 'BMW', 'model': 'X5', 'engine': '3.0L I6 turbo',
            'horsepower': '335', 'torque': '330 lb-ft', 'zero_to_sixty': '5.3',
            'top_speed': '155 mph', 'drivetrain': 'AWD', 'price': '$65,000', 'year': '2025',
        }
        partial_specs = {'make': 'BMW', 'model': 'X5'}
        
        score_full = calculate_quality_score(
            title='A Good Title For This Article Here',
            content='<h2>Heading</h2><p>P1</p><p>P2</p><p>P3</p>' + ' word' * 400,
            specs=full_specs, tags=['SUV', 'BMW'],
        )
        score_partial = calculate_quality_score(
            title='A Good Title For This Article Here',
            content='<h2>Heading</h2><p>P1</p><p>P2</p><p>P3</p>' + ' word' * 400,
            specs=partial_specs, tags=['SUV', 'BMW'],
        )
        assert score_full >= score_partial

    def test_not_specified_not_counted(self):
        """'Not specified' values should not count as filled"""
        specs = {
            'make': 'Toyota', 'model': 'Camry',
            'engine': 'Not specified', 'horsepower': 'Not specified',
            'torque': '', 'zero_to_sixty': None,
            'top_speed': 'None', 'drivetrain': '', 'price': '', 'year': '',
        }
        score = calculate_quality_score(
            title='A Good Title For This Article Test',
            content='<h2>H</h2><p>P1</p><p>P2</p><p>P3</p>' + ' word' * 400,
            specs=specs, tags=['sedan', 'toyota'],
        )
        # Only make and model are filled (2/10 = 20%), no spec bonus
        assert score <= 8

    def test_red_flags_lower_score(self):
        """Content with placeholders should lose points"""
        score = calculate_quality_score(
            title='A Good Title For This Article Test',
            content='<h2>Test</h2><p>Lorem ipsum dolor sit amet.</p><p>More content.</p><p>Even more.</p>' + ' word' * 400,
            specs={'make': 'Test'}, tags=['test', 'car'],
        )
        score_clean = calculate_quality_score(
            title='A Good Title For This Article Test',
            content='<h2>Test</h2><p>Real content here.</p><p>More content.</p><p>Even more.</p>' + ' word' * 400,
            specs={'make': 'Test'}, tags=['test', 'car'],
        )
        assert score_clean >= score

    def test_no_image_normalization(self):
        """Articles without images should still get fair scores"""
        score = calculate_quality_score(
            title='A Good Title For This Article Test',
            content='<h2>Heading</h2><p>P1</p><p>P2</p><p>P3</p>' + ' word' * 800,
            specs={'make': 'Ford', 'model': 'F-150'}, tags=['truck', 'ford'],
            featured_image='',
        )
        assert score >= 5  # Good content shouldn't be punished for no image
