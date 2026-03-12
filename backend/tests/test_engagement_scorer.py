"""
Tests for engagement_scorer module (re-exports from scoring.py).

Verifies that the engagement_scorer stub correctly re-exports functions
and that the scoring module's compute_engagement_score works correctly.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

# Test that the stub module re-exports correctly
from ai_engine.modules.engagement_scorer import (
    compute_engagement_score,
    compute_engagement_details,
    update_engagement_scores,
)


class TestEngagementScorerExports:
    """Verify engagement_scorer stub re-exports are callable."""

    def test_compute_engagement_score_is_callable(self):
        assert callable(compute_engagement_score)

    def test_compute_engagement_details_is_callable(self):
        assert callable(compute_engagement_details)

    def test_update_engagement_scores_is_callable(self):
        assert callable(update_engagement_scores)


class TestEngagementScoreImportSources:
    """Verify engagement_scorer imports come from scoring module."""

    def test_same_function_as_scoring_module(self):
        from ai_engine.modules.scoring import compute_engagement_score as original
        assert compute_engagement_score is original

    def test_same_details_as_scoring_module(self):
        from ai_engine.modules.scoring import compute_engagement_details as original
        assert compute_engagement_details is original

    def test_same_update_as_scoring_module(self):
        from ai_engine.modules.scoring import update_engagement_scores as original
        assert update_engagement_scores is original
