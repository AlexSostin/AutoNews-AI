"""
Tests for the Quality Gate and Video Fact Extractor modules.

Tests cover:
- Quality Gate: all 5 scoring criteria with good, bad, and medium articles
- Video Fact Extractor: JSON parsing, URL normalisation, prompt formatting
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from ai_engine.modules.quality_gate import (
    check_quality_gate,
    QUALITY_GATE_THRESHOLD,
)
from ai_engine.modules.video_fact_extractor import (
    _normalise_youtube_url,
    _parse_json_response,
    format_video_facts_for_prompt,
    extract_facts_from_video,
)


# ══════════════════════════════════════════════════════════════════════
#  Sample HTML articles
# ══════════════════════════════════════════════════════════════════════

GOOD_ARTICLE = """
<h2>2026 BYD Seal 06 GT: 402 hp Electric Hatchback for $25,000</h2>
<p>BYD's latest electric hatchback undercuts most competitors by $10,000 and matches
their range. The Seal 06 GT brings 402 hp and 620 km of WLTP range to a segment
dominated by Tesla and Hyundai. With 800V architecture and a sub-4-second sprint,
this is not just another budget EV — it is a serious performance contender that
happens to cost less than a Model 3.</p>

<div class="spec-bar">
  <div class="spec-item"><div class="spec-label">STARTING PRICE</div><div class="spec-value">$25,000</div></div>
  <div class="spec-item"><div class="spec-label">RANGE</div><div class="spec-value">620 km WLTP</div></div>
  <div class="spec-item"><div class="spec-label">POWER</div><div class="spec-value">402 hp</div></div>
  <div class="spec-item"><div class="spec-label">0-100 KM/H</div><div class="spec-value">3.8 sec</div></div>
  <div class="spec-item"><div class="spec-label">POWERTRAIN</div><div class="spec-value">BEV AWD</div></div>
</div>

<h2>Performance & Specs</h2>
<p>The Seal 06 GT produces 402 hp from its dual-motor AWD setup, sprinting to 100 km/h
in just 3.8 seconds. The 77 kWh NMC battery delivers 620 km of WLTP range, one of the
most efficient EVs in its class. The rear motor handles 268 hp while the front adds
134 hp for balanced torque distribution.</p>

<div class="powertrain-specs">
  <div class="ps-item"><div class="ps-label">POWERTRAIN TYPE</div><div class="ps-val">BEV AWD</div></div>
  <div class="ps-item"><div class="ps-label">BATTERY</div><div class="ps-val">77 kWh (NMC)</div></div>
  <div class="ps-item"><div class="ps-label">RANGE</div><div class="ps-val">620 km WLTP</div></div>
  <div class="ps-item"><div class="ps-label">0-100 KM/H</div><div class="ps-val">3.8 sec</div></div>
</div>

<p>The 800V architecture enables ultra-fast DC charging, going from 10% to 80% in just
18 minutes. Top speed is electronically limited to 230 km/h.</p>

<h2>Design & Interior</h2>
<p>The Seal 06 GT features BYD's latest design language with a low-slung roofline and
aggressive front fascia. The carbon fiber roof saves weight and lowers the center of
gravity. Inside, a 15.6-inch rotating display dominates the dash.</p>

<p>Rear legroom is generous at 910 mm, and the trunk offers 450 liters of cargo space.
The front trunk adds another 50 liters for small items.</p>

<h2>Pricing & Availability</h2>
<div class="price-tag"><span class="price-main">$25,000</span><span class="price-note">Starting · Model Year 2026</span></div>
<p>The Seal 06 GT launches in Q2 2026 across European and Asian markets. Three trim
levels will be available across most markets.</p>

<h2>Pros & Cons</h2>
<div class="pros-cons">
  <div class="pc-block pros">
    <div class="pc-title">Pros</div>
    <ul class="pc-list">
      <li>Exceptional range at 620 km WLTP</li>
      <li>Sub-$25,000 price undercuts rivals by $10k</li>
      <li>3.8s 0-100 is sports car territory</li>
    </ul>
  </div>
  <div class="pc-block cons">
    <div class="pc-title">Cons</div>
    <ul class="pc-list">
      <li>No Apple CarPlay in base trim</li>
      <li>Heavy 2.1-ton curb weight hurts urban agility</li>
    </ul>
  </div>
</div>

<h2>How It Compares</h2>
<div class="compare-grid">
  <div class="compare-card featured">
    <div class="compare-badge">This Vehicle</div>
    <div class="compare-card-name">2026 BYD Seal 06 GT</div>
    <div class="compare-row"><span class="k">Power</span><span class="v">402 hp</span></div>
    <div class="compare-row"><span class="k">Range</span><span class="v">620 km</span></div>
    <div class="compare-row"><span class="k">Price</span><span class="v">$25,000</span></div>
  </div>
  <div class="compare-card">
    <div class="compare-card-name">2026 Tesla Model 3</div>
    <div class="compare-row"><span class="k">Power</span><span class="v">366 hp</span></div>
    <div class="compare-row"><span class="k">Range</span><span class="v">565 km</span></div>
    <div class="compare-row"><span class="k">Price</span><span class="v">$35,000</span></div>
  </div>
  <div class="compare-card">
    <div class="compare-card-name">2026 Hyundai Ioniq 6</div>
    <div class="compare-row"><span class="k">Power</span><span class="v">325 hp</span></div>
    <div class="compare-row"><span class="k">Range</span><span class="v">614 km</span></div>
    <div class="compare-row"><span class="k">Price</span><span class="v">$32,000</span></div>
  </div>
</div>
<p>Against the Tesla Model 3 and Hyundai Ioniq 6, the Seal 06 GT offers significantly
more power at a lower price point. The value proposition is clear.</p>

<div class="fm-verdict">
  <div class="verdict-label">FreshMotors Verdict</div>
  <p>The BYD Seal 06 GT is the electric hatchback that finally makes EVs affordable
  without sacrificing performance. With 402 hp, 620 km of range, and a sub-$25,000
  price tag, it undercuts the Tesla Model 3 by $10,000 while matching its range.
  The 3.8-second sprint proves BYD's engineering prowess, and the 800V architecture
  future-proofs the charging experience. The heavy curb weight is a concession, but
  for daily commuters and road trippers prioritizing range and value, the Seal 06 GT
  is an easy recommendation.</p>
</div>

<div class="alt-texts" style="display:none">
ALT_TEXT_1: 2026 BYD Seal 06 GT front three-quarter exterior view
ALT_TEXT_2: 2026 BYD Seal 06 GT interior dashboard
ALT_TEXT_3: 2026 BYD Seal 06 GT rear design detail
</div>
"""

INCOMPLETE_ARTICLE = """
<h2>2026 Mystery Car Review</h2>
<p>This is a new car that promises to deliver great performance.</p>

<h2>Performance</h2>
<p>The car has good performance. Making waves in the landscape.
It is a compelling proposition. Based on the video transcript,
the narrator mentions the car is fast.</p>

<h2>Verdict</h2>
<p>Good car.</p>
"""

NO_COMPETITORS_ARTICLE = """
<h2>2026 NIO ET5: Premium Electric Sedan</h2>
<p>NIO's latest sedan brings premium features at a competitive price point. The ET5
delivers 489 hp from its dual-motor setup and offers battery swap capability that
sets it apart from the competition in a meaningful way.</p>

<div class="spec-bar">
  <div class="spec-item"><div class="spec-label">POWER</div><div class="spec-value">489 hp</div></div>
  <div class="spec-item"><div class="spec-label">RANGE</div><div class="spec-value">580 km CLTC</div></div>
  <div class="spec-item"><div class="spec-label">PRICE</div><div class="spec-value">$38,000</div></div>
</div>

<h2>Performance</h2>
<p>The dual-motor setup produces 489 hp combined, with a 0-100 time of 4.0 seconds.
The 75 kWh battery pack provides 580 km of CLTC range. NIO's battery swap network
adds a unique flexibility advantage for long-distance driving.</p>

<h2>Pricing</h2>
<div class="price-tag"><span class="price-main">$38,000</span><span class="price-note">Starting · 2026</span></div>
<p>Available in China and European markets starting Q3 2026.</p>

<h2>Pros & Cons</h2>
<div class="pros-cons">
  <div class="pc-block pros">
    <div class="pc-title">Pros</div>
    <ul class="pc-list">
      <li>489 hp dual-motor performance</li>
      <li>Battery swap support for instant charging</li>
    </ul>
  </div>
  <div class="pc-block cons">
    <div class="pc-title">Cons</div>
    <ul class="pc-list">
      <li>CLTC range overstates real-world figures</li>
    </ul>
  </div>
</div>

<div class="fm-verdict">
  <div class="verdict-label">FreshMotors Verdict</div>
  <p>The NIO ET5 is a capable electric sedan that competes on both performance and
  features. With 489 hp and unique battery swap capability it offers a flexibility
  that no rival currently matches. However the CLTC range figure will be significantly
  lower in real-world European driving conditions. For buyers in markets served by
  NIO's swap station network, this is a strong alternative to established rivals
  at a similar price with more power and a premium interior.</p>
</div>

<div class="alt-texts" style="display:none">
ALT_TEXT_1: 2026 NIO ET5 exterior
ALT_TEXT_2: 2026 NIO ET5 interior
ALT_TEXT_3: NIO battery swap station
</div>
"""


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Overall Tests
# ══════════════════════════════════════════════════════════════════════

class TestQualityGateOverall:

    def test_good_article_passes(self):
        result = check_quality_gate(GOOD_ARTICLE, has_competitor_data=True)
        assert result['passed'] is True
        assert result['score'] >= QUALITY_GATE_THRESHOLD

    def test_incomplete_article_fails(self):
        result = check_quality_gate(INCOMPLETE_ARTICLE)
        assert result['passed'] is False
        assert result['score'] < QUALITY_GATE_THRESHOLD

    def test_empty_content_fails(self):
        result = check_quality_gate('')
        assert result['passed'] is False
        assert result['score'] == 0
        assert 'Empty article content' in result['issues']

    def test_result_has_required_keys(self):
        result = check_quality_gate(GOOD_ARTICLE)
        assert 'score' in result
        assert 'passed' in result
        assert 'details' in result
        assert 'issues' in result
        assert isinstance(result['score'], int)
        assert isinstance(result['passed'], bool)

    def test_all_criteria_present_in_details(self):
        result = check_quality_gate(GOOD_ARTICLE)
        expected = {'spec_completeness', 'competitors', 'structure',
                    'content_depth', 'tone'}
        assert set(result['details'].keys()) == expected

    def test_each_criterion_has_score_and_max(self):
        result = check_quality_gate(GOOD_ARTICLE)
        for name, detail in result['details'].items():
            assert 'score' in detail, f"{name} missing 'score'"
            assert 'max' in detail, f"{name} missing 'max'"
            assert detail['max'] == 20

    def test_max_score_is_100(self):
        result = check_quality_gate(GOOD_ARTICLE)
        assert result['score'] <= 100


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Spec Completeness
# ══════════════════════════════════════════════════════════════════════

class TestSpecCompleteness:

    def test_full_spec_bar_scores_high(self):
        result = check_quality_gate(GOOD_ARTICLE)
        spec = result['details']['spec_completeness']
        assert spec['score'] >= 16

    def test_missing_spec_bar_scores_zero(self):
        result = check_quality_gate(INCOMPLETE_ARTICLE)
        assert result['details']['spec_completeness']['score'] == 0

    def test_partial_spec_bar(self):
        result = check_quality_gate(NO_COMPETITORS_ARTICLE)
        spec = result['details']['spec_completeness']
        assert 6 <= spec['score'] <= 14


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Competitor Scoring
# ══════════════════════════════════════════════════════════════════════

class TestCompetitorScoring:

    def test_compare_grid_scores_high(self):
        result = check_quality_gate(GOOD_ARTICLE, has_competitor_data=True)
        assert result['details']['competitors']['score'] >= 16

    def test_no_competitors_when_unavailable(self):
        """Don't penalize missing competitors if data wasn't available."""
        result = check_quality_gate(NO_COMPETITORS_ARTICLE, has_competitor_data=False)
        assert result['details']['competitors']['score'] >= 12


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Structure
# ══════════════════════════════════════════════════════════════════════

class TestStructureCompleteness:

    def test_all_sections_present(self):
        result = check_quality_gate(GOOD_ARTICLE)
        assert result['details']['structure']['score'] >= 15

    def test_missing_sections_detected(self):
        result = check_quality_gate(INCOMPLETE_ARTICLE)
        assert result['details']['structure']['score'] < 8


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Content Depth
# ══════════════════════════════════════════════════════════════════════

class TestContentDepth:

    def test_long_article_scores_high(self):
        result = check_quality_gate(GOOD_ARTICLE)
        # Sample article is ~500 words — scores 10+ for depth
        assert result['details']['content_depth']['score'] >= 10

    def test_short_article_scores_low(self):
        result = check_quality_gate(INCOMPLETE_ARTICLE)
        assert result['details']['content_depth']['score'] < 10


# ══════════════════════════════════════════════════════════════════════
#  Quality Gate — Tone
# ══════════════════════════════════════════════════════════════════════

class TestToneScoring:

    def test_clean_article_full_marks(self):
        result = check_quality_gate(GOOD_ARTICLE)
        assert result['details']['tone']['score'] >= 18

    def test_filler_and_leaks_penalized(self):
        result = check_quality_gate(INCOMPLETE_ARTICLE)
        tone = result['details']['tone']
        # Has "compelling proposition", "making waves", "based on the video transcript"
        assert tone['score'] < 15

    def test_source_leaks_detected(self):
        html = '<p>Based on the video, the narrator mentions the car is fast. From the transcript we learn more.</p>'
        result = check_quality_gate(html)
        assert result['details']['tone']['score'] < 15


# ══════════════════════════════════════════════════════════════════════
#  Video Fact Extractor — URL Normalisation
# ══════════════════════════════════════════════════════════════════════

class TestURLNormalisation:

    def test_standard_url(self):
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        assert _normalise_youtube_url(url) == url

    def test_short_url(self):
        url = 'https://youtu.be/dQw4w9WgXcQ'
        assert _normalise_youtube_url(url) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_embed_url(self):
        url = 'https://www.youtube.com/embed/dQw4w9WgXcQ'
        assert _normalise_youtube_url(url) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_shorts_url(self):
        url = 'https://www.youtube.com/shorts/dQw4w9WgXcQ'
        assert _normalise_youtube_url(url) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_url_with_params(self):
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120'
        # Normalisation extracts video ID → rebuilds canonical URL
        assert _normalise_youtube_url(url) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_empty_url(self):
        assert _normalise_youtube_url('') == ''

    def test_invalid_url(self):
        assert _normalise_youtube_url('https://example.com') == ''


# ══════════════════════════════════════════════════════════════════════
#  Video Fact Extractor — JSON Parsing
# ══════════════════════════════════════════════════════════════════════

class TestJSONParsing:

    def test_valid_json(self):
        data = {
            'specs': {'horsepower': '402', 'range_km': '620'},
            'competitors_mentioned': ['Tesla Model 3'],
            'reviewer_verdict_summary': 'Best value EV',
            'key_visual_facts': ['carbon roof visible'],
        }
        result = _parse_json_response(json.dumps(data))
        assert result['specs']['horsepower'] == '402'
        assert 'Tesla Model 3' in result['competitors_mentioned']

    def test_json_with_markdown_fences(self):
        text = '```json\n{"specs": {"horsepower": "300"}, "competitors_mentioned": []}\n```'
        result = _parse_json_response(text)
        assert result['specs']['horsepower'] == '300'

    def test_json_embedded_in_text(self):
        text = 'Here is the data: {"specs": {"horsepower": "250"}} end.'
        result = _parse_json_response(text)
        assert result['specs']['horsepower'] == '250'

    def test_invalid_json(self):
        result = _parse_json_response('This is not JSON at all')
        assert result == {}

    def test_empty_string(self):
        result = _parse_json_response('')
        assert result == {}

    def test_missing_keys_filled_with_defaults(self):
        result = _parse_json_response('{"specs": {"hp": "400"}}')
        assert 'competitors_mentioned' in result
        assert result['competitors_mentioned'] == []
        assert result['reviewer_verdict_summary'] is None


# ══════════════════════════════════════════════════════════════════════
#  Video Fact Extractor — Prompt Formatting
# ══════════════════════════════════════════════════════════════════════

class TestFormatVideoFacts:

    def test_full_facts(self):
        facts = {
            'specs': {'horsepower': '402', 'range_km': '620 km WLTP', 'top_speed_kmh': None},
            'competitors_mentioned': ['Tesla Model 3', 'Hyundai Ioniq 6'],
            'reviewer_verdict_summary': 'Best value EV of 2026',
            'key_visual_facts': ['carbon fiber roof', 'quad exhaust tips'],
        }
        text = format_video_facts_for_prompt(facts)
        assert 'Horsepower: 402' in text
        assert 'Range Km: 620 km WLTP' in text
        assert 'Tesla Model 3' in text
        assert 'Best value EV' in text
        assert 'carbon fiber roof' in text
        assert 'VIDEO ANALYSIS' in text

    def test_empty_facts(self):
        assert format_video_facts_for_prompt({}) == ''

    def test_all_null_specs(self):
        facts = {
            'specs': {'horsepower': None, 'range_km': 'null'},
            'competitors_mentioned': [],
            'reviewer_verdict_summary': None,
            'key_visual_facts': [],
        }
        assert format_video_facts_for_prompt(facts) == ''

    def test_partial_facts(self):
        facts = {
            'specs': {'horsepower': '300'},
            'competitors_mentioned': [],
            'reviewer_verdict_summary': None,
            'key_visual_facts': [],
        }
        text = format_video_facts_for_prompt(facts)
        assert 'Horsepower: 300' in text
        assert 'COMPETITORS' not in text


# ══════════════════════════════════════════════════════════════════════
#  Video Fact Extractor — Full Pipeline (mocked)
# ══════════════════════════════════════════════════════════════════════

class TestExtractFactsFromVideo:

    @patch('ai_engine.modules.video_fact_extractor._get_gemini_client')
    def test_returns_empty_when_no_client(self, mock_client):
        mock_client.return_value = None
        result = extract_facts_from_video('https://youtu.be/abc12345678')
        assert result == {}

    def test_returns_empty_for_empty_url(self):
        result = extract_facts_from_video('')
        assert result == {}

    @patch('ai_engine.modules.video_fact_extractor._get_gemini_client')
    def test_handles_api_error_gracefully(self, mock_client):
        """API error should return empty dict, not raise."""
        client = MagicMock()
        client.models.generate_content.side_effect = Exception('API error')
        mock_client.return_value = client
        result = extract_facts_from_video('https://youtu.be/abc12345678')
        assert result == {}

    @patch('ai_engine.modules.video_fact_extractor._get_gemini_client')
    def test_successful_extraction(self, mock_client):
        """Mock a successful Gemini response and verify parsing."""
        response = MagicMock()
        response.text = json.dumps({
            'specs': {'horsepower': '500', 'range_km': '700 km WLTP'},
            'competitors_mentioned': ['BMW i4'],
            'reviewer_verdict_summary': 'Excellent EV',
            'key_visual_facts': ['panoramic roof'],
        })
        response.usage_metadata = None

        client = MagicMock()
        client.models.generate_content.return_value = response
        mock_client.return_value = client

        result = extract_facts_from_video('https://www.youtube.com/watch?v=abc12345678')
        assert result['specs']['horsepower'] == '500'
        assert 'BMW i4' in result['competitors_mentioned']
        assert result['reviewer_verdict_summary'] == 'Excellent EV'

    def test_returns_empty_for_invalid_url(self):
        result = extract_facts_from_video('https://example.com/not-youtube')
        assert result == {}
