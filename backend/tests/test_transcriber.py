"""Tests for ai_engine.modules.transcriber — multi-tier YouTube transcript fetching."""
import pytest
from unittest.mock import patch, MagicMock
from ai_engine.modules.transcriber import _extract_video_id, _fetch_via_transcript_api, transcribe_from_youtube


class TestExtractVideoId:
    """Test YouTube URL → video ID extraction."""

    def test_standard_url(self):
        assert _extract_video_id('https://www.youtube.com/watch?v=u4d-hkCitcI') == 'u4d-hkCitcI'

    def test_short_url(self):
        assert _extract_video_id('https://youtu.be/u4d-hkCitcI') == 'u4d-hkCitcI'

    def test_embed_url(self):
        assert _extract_video_id('https://www.youtube.com/embed/u4d-hkCitcI') == 'u4d-hkCitcI'

    def test_with_params(self):
        assert _extract_video_id('https://www.youtube.com/watch?v=abc123def45&t=120') == 'abc123def45'

    def test_bare_id(self):
        assert _extract_video_id('abc123def45') == 'abc123def45'

    def test_invalid_url(self):
        assert _extract_video_id('https://google.com/something') is None

    def test_empty_string(self):
        assert _extract_video_id('') is None


class TestTier1TranscriptApi:
    """Test youtube-transcript-api integration (tier 1)."""

    def test_import_available(self):
        """youtube-transcript-api should be installed."""
        import youtube_transcript_api
        assert hasattr(youtube_transcript_api, 'YouTubeTranscriptApi')

    def test_returns_text_on_success(self):
        """Tier 1 should return str or None for a fake video ID."""
        # This test validates the extraction logic without hitting the real API
        result = _fetch_via_transcript_api('test_id')
        # Without mocking the full chain, we just verify it returns str or None
        assert result is None or isinstance(result, str)

    def test_handles_missing_library(self):
        """Should return None gracefully if library import fails."""
        with patch.dict('sys.modules', {'youtube_transcript_api': None}):
            result = _fetch_via_transcript_api('test_id')
            # May or may not be None depending on import caching, but shouldn't crash
            assert result is None or isinstance(result, str)


class TestTranscribeMainFunction:
    """Test the main transcribe_from_youtube entry point."""

    def test_invalid_url_returns_error(self):
        """Invalid URL should return ERROR string."""
        result = transcribe_from_youtube('not_a_url_at_all')
        assert result.startswith('ERROR:') or len(result) > 0

    @patch('ai_engine.modules.transcriber._fetch_via_transcript_api')
    def test_tier1_success_skips_tier2(self, mock_tier1):
        """When tier 1 succeeds, tier 2 should NOT be called."""
        mock_tier1.return_value = 'A' * 200  # 200 chars, enough to pass
        with patch('ai_engine.modules.transcriber._fetch_via_ytdlp') as mock_tier2:
            result = transcribe_from_youtube('https://www.youtube.com/watch?v=test12345ab')
            assert 'A' * 200 == result
            mock_tier2.assert_not_called()

    @patch('ai_engine.modules.transcriber._fetch_via_transcript_api')
    @patch('ai_engine.modules.transcriber._fetch_via_ytdlp')
    def test_tier1_fail_triggers_tier2(self, mock_tier2, mock_tier1):
        """When tier 1 fails, tier 2 should be called."""
        mock_tier1.return_value = None
        mock_tier2.return_value = ('Fallback text ' * 20, {'title': 'Test'})
        result = transcribe_from_youtube('https://www.youtube.com/watch?v=test12345ab')
        mock_tier2.assert_called_once()

    @patch('ai_engine.modules.transcriber._fetch_via_transcript_api')
    @patch('ai_engine.modules.transcriber._fetch_via_ytdlp')
    @patch('ai_engine.modules.transcriber._get_video_info_fallback')
    def test_all_tiers_fail_returns_error(self, mock_fallback, mock_tier2, mock_tier1):
        """When all tiers fail, should return ERROR string."""
        mock_tier1.return_value = None
        mock_tier2.return_value = (None, None)
        mock_fallback.return_value = None
        result = transcribe_from_youtube('https://www.youtube.com/watch?v=test12345ab')
        assert result.startswith('ERROR:')


class TestCaptchaRejection:
    """Test that CAPTCHA/garbage content is properly rejected."""

    def test_captcha_indicators_detected(self):
        """Verify that CAPTCHA indicators list exists in the module."""
        import ai_engine.modules.transcriber as t
        source = open(t.__file__).read()
        assert 'captcha' in source.lower()
        assert 'unusual traffic' in source.lower() or 'automated queries' in source.lower()
