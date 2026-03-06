"""
Tests for CarSpecification deduplication system:
  - _coverage_score (bug fix: 'Not specified' must count as empty)
  - GET /car-specifications/duplicates/
  - POST /car-specifications/merge/
  - POST /car-specifications/ai-pick/
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from news.models import CarSpecification, Article

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _article(title='Test Article'):
    n = Article.objects.count()
    return Article.objects.create(
        title=f'{title} {n}',
        slug=f'test-dedup-{n}',
        content='<p>Content</p>',
    )


def _spec(make='BYD', model='Seal', article=None, **kwargs):
    """Create a CarSpecification with sensible defaults."""
    if article is None:
        article = _article(f'{make} {model} Article')
    return CarSpecification.objects.create(
        article=article,
        make=make,
        model=model,
        **kwargs,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Unit: _coverage_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoverageScore:
    """The bug fix: placeholder strings must NOT count as filled fields."""

    def _viewset(self):
        from news.api_views.vehicles import CarSpecificationViewSet
        return CarSpecificationViewSet()

    def test_all_real_values(self):
        vs = self._viewset()
        spec = _spec(
            trim='Ultra', engine='PHEV/40kWh', horsepower='400 HP',
            torque='600 Nm', zero_to_sixty='5.0s', top_speed='200 km/h',
            drivetrain='AWD', price='350,000 CNY', release_date='2026',
        )
        assert vs._coverage_score(spec) == 9

    def test_not_specified_counts_as_empty(self):
        """Core bug fix: 'Not specified' should NOT increase coverage score."""
        vs = self._viewset()
        spec = _spec(
            trim='Not specified',
            engine='PHEV/40kWh',
            horsepower='Not specified',
            torque='600 Nm',
            zero_to_sixty='none',  # lowercase
            top_speed='N/A',
        )
        # Only 'engine' and 'torque' are real → score = 2
        assert vs._coverage_score(spec) == 2

    def test_empty_string_counts_as_empty(self):
        vs = self._viewset()
        spec = _spec(trim='', engine='', horsepower='')
        assert vs._coverage_score(spec) == 0

    def test_none_value_counts_as_empty(self):
        """None from getattr default (field not set) is treated as empty."""
        vs = self._viewset()
        # Fields default to '' in DB (NOT NULL), use '' to simulate missing data
        spec = _spec(trim='', engine='', horsepower='400 HP')
        # Only horsepower is real → score = 1
        assert vs._coverage_score(spec) == 1

    def test_is_real_value_handles_python_none(self):
        """_is_real_value(None) should return False (treat as empty)."""
        vs = self._viewset()
        assert not vs._is_real_value(None)
        assert not vs._is_real_value(0)  # Edge: 0 becomes '0', not a placeholder


    def test_mixed_valid_and_placeholder(self):
        vs = self._viewset()
        spec = _spec(
            trim='Ultra',
            engine='Not specified',
            horsepower='677 HP',
            torque='none',
            drivetrain='AWD',
        )
        # trim, horsepower, drivetrain → 3 real values
        assert vs._coverage_score(spec) == 3

    def test_is_real_value_case_insensitive(self):
        vs = self._viewset()
        # All casing variants should be treated as empty
        assert not vs._is_real_value('NOT SPECIFIED')
        assert not vs._is_real_value('None')
        assert not vs._is_real_value('NONE')
        assert not vs._is_real_value('N/A')
        assert not vs._is_real_value('Unknown')
        # Real values must pass
        assert vs._is_real_value('677 HP')
        assert vs._is_real_value('0')  # Edge: zero is a real value


# ═══════════════════════════════════════════════════════════════════════════════
# API: GET /car-specifications/duplicates/
# ═══════════════════════════════════════════════════════════════════════════════

class TestDuplicatesEndpoint:

    def test_returns_duplicate_groups(self, authenticated_client):
        """Two specs with same make+model appear as one group."""
        _spec('Toyota', 'Camry', horsepower='200 HP')
        _spec('Toyota', 'Camry', horsepower='210 HP', trim='Sport')
        res = authenticated_client.get('/api/v1/car-specifications/duplicates/')
        assert res.status_code == 200
        data = res.json()
        assert 'groups' in data
        groups = data['groups']
        camry = next((g for g in groups if g['make'] == 'Toyota' and g['model'] == 'Camry'), None)
        assert camry is not None
        assert camry['count'] == 2

    def test_single_spec_not_in_duplicates(self, authenticated_client):
        """A make+model with only one record is NOT returned."""
        _spec('Honda', 'Civic', horsepower='150 HP')
        res = authenticated_client.get('/api/v1/car-specifications/duplicates/')
        assert res.status_code == 200
        groups = res.json()['groups']
        civic = [g for g in groups if g['make'] == 'Honda' and g['model'] == 'Civic']
        assert len(civic) == 0

    def test_coverage_scores_present(self, authenticated_client):
        """Each record in a group has a coverage_score."""
        _spec('Zeekr', '7X', horsepower='475 HP', engine='Dual Motor', drivetrain='AWD')
        _spec('Zeekr', '7X', horsepower='', engine='', drivetrain='')
        res = authenticated_client.get('/api/v1/car-specifications/duplicates/')
        groups = res.json()['groups']
        zeekr = next(g for g in groups if g['make'] == 'Zeekr')
        for rec in zeekr['records']:
            assert 'coverage_score' in rec

    def test_suggested_master_is_highest_coverage(self, authenticated_client):
        """suggested_master_id points to the record with the most real fields."""
        spec_low = _spec('NIO', 'ET9', horsepower='', engine='')  # 0 fields
        spec_high = _spec('NIO', 'ET9',
                          horsepower='650 HP', engine='Dual Motor',
                          torque='850 Nm', drivetrain='AWD')  # 4 fields
        res = authenticated_client.get('/api/v1/car-specifications/duplicates/')
        groups = res.json()['groups']
        nio = next(g for g in groups if g['make'] == 'NIO')
        # Master should be the high-coverage record
        assert nio['suggested_master_id'] == spec_high.id

    def test_requires_authentication(self, api_client):
        res = api_client.get('/api/v1/car-specifications/duplicates/')
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# API: POST /car-specifications/merge/
# ═══════════════════════════════════════════════════════════════════════════════

class TestMergeEndpoint:

    def test_merge_deletes_duplicates(self, authenticated_client):
        """After merge, delete_ids records are gone."""
        master = _spec('AITO', 'M8', horsepower='272 HP', engine='EV/80kWh', drivetrain='RWD')
        donor1 = _spec('AITO', 'M8', horsepower='305 HP', engine='electric motors')
        donor2 = _spec('AITO', 'M8', horsepower='', engine='')

        res = authenticated_client.post('/api/v1/car-specifications/merge/', {
            'master_id': master.id,
            'delete_ids': [donor1.id, donor2.id],
        }, format='json')

        assert res.status_code == 200
        assert not CarSpecification.objects.filter(id__in=[donor1.id, donor2.id]).exists()
        assert CarSpecification.objects.filter(id=master.id).exists()

    def test_merge_fills_empty_fields_from_donor(self, authenticated_client):
        """Empty master fields are filled from the best donor."""
        master = _spec('DENZA', 'N9', horsepower='400 HP', engine='', drivetrain='')
        donor = _spec('DENZA', 'N9', horsepower='', engine='PHEV/40kWh', drivetrain='AWD')

        res = authenticated_client.post('/api/v1/car-specifications/merge/', {
            'master_id': master.id,
            'delete_ids': [donor.id],
        }, format='json')

        assert res.status_code == 200
        master.refresh_from_db()
        # master already had HP, should keep it
        assert master.horsepower == '400 HP'
        # master had no engine/drivetrain → filled from donor
        assert master.engine == 'PHEV/40kWh'
        assert master.drivetrain == 'AWD'

    def test_merge_invalid_master_id(self, authenticated_client):
        res = authenticated_client.post('/api/v1/car-specifications/merge/', {
            'master_id': 999999,
            'delete_ids': [1],
        }, format='json')
        assert res.status_code == 404

    def test_merge_missing_delete_ids(self, authenticated_client):
        master = _spec('Test', 'Car')
        res = authenticated_client.post('/api/v1/car-specifications/merge/', {
            'master_id': master.id,
            'delete_ids': [],
        }, format='json')
        assert res.status_code == 400

    def test_merge_requires_authentication(self, api_client):
        res = api_client.post('/api/v1/car-specifications/merge/', {
            'master_id': 1, 'delete_ids': [2],
        }, format='json')
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# API: POST /car-specifications/ai-pick/
# ═══════════════════════════════════════════════════════════════════════════════

MOCK_GEMINI_RESPONSE = json.dumps({
    'suggested_master_id': None,  # will be set per test
    'best_fields': {
        'trim':          {'value': 'PHEV', 'from_id': None, 'reason': 'More descriptive than None'},
        'engine':        {'value': 'PHEV / 40.0 kWh / AWD', 'from_id': None, 'reason': 'Consistent detail'},
        'horsepower':    {'value': '400 HP', 'from_id': None, 'reason': '530 HP may be error'},
        'torque':        {'value': '600 Nm', 'from_id': None, 'reason': 'Consistent with 400 HP'},
        'zero_to_sixty': {'value': '5.0s', 'from_id': None, 'reason': 'Plausible for PHEV'},
        'top_speed':     {'value': '200 km/h', 'from_id': None, 'reason': 'Typical for PHEV'},
        'drivetrain':    {'value': 'AWD', 'from_id': None, 'reason': 'Both records agree'},
        'price':         {'value': '350,000 CNY', 'from_id': None, 'reason': 'Consistent'},
        'release_date':  {'value': '', 'from_id': None, 'reason': 'Empty in both records'},
    },
})


class TestAiPickEndpoint:

    def _make_gemini_mock(self, spec_id):
        """Return a mock Gemini provider that injects the given spec_id as master."""
        response = json.loads(MOCK_GEMINI_RESPONSE)
        response['suggested_master_id'] = spec_id
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps(response)
        return mock_provider

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_pick_returns_best_fields(self, mock_ai, authenticated_client):
        """Happy path: returns best_fields with reason per field."""
        spec1 = _spec('DENZA', 'N9', horsepower='400 HP', engine='PHEV/40kWh')
        spec2 = _spec('DENZA', 'N9', horsepower='530 HP', engine='EV')
        mock_ai.return_value = self._make_gemini_mock(spec1.id)

        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [spec1.id, spec2.id],
        }, format='json')

        assert res.status_code == 200
        data = res.json()
        assert data['success'] is True
        assert 'best_fields' in data
        assert 'horsepower' in data['best_fields']
        assert data['best_fields']['horsepower']['value'] == '400 HP'
        assert 'reason' in data['best_fields']['horsepower']

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_pick_sets_suggested_master(self, mock_ai, authenticated_client):
        """suggested_master_id in response comes from Gemini."""
        spec1 = _spec('BYD', 'Seal', horsepower='530 HP', engine='Dual Motor', drivetrain='AWD')
        spec2 = _spec('BYD', 'Seal', horsepower='', engine='')
        mock_ai.return_value = self._make_gemini_mock(spec1.id)

        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [spec1.id, spec2.id],
        }, format='json')

        assert res.status_code == 200
        assert res.json()['suggested_master_id'] == spec1.id

    def test_ai_pick_requires_minimum_two_ids(self, authenticated_client):
        """Single ID → 400 Bad Request."""
        spec = _spec('Test', 'Car')
        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [spec.id],
        }, format='json')
        assert res.status_code == 400

    def test_ai_pick_empty_ids(self, authenticated_client):
        """Empty list → 400 Bad Request."""
        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [],
        }, format='json')
        assert res.status_code == 400

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_pick_invalid_json_from_gemini(self, mock_ai, authenticated_client):
        """If Gemini returns unparseable response → 422."""
        spec1 = _spec('Test', 'Car A')
        spec2 = _spec('Test', 'Car A')
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = 'I cannot help with this.'
        mock_ai.return_value = mock_provider

        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [spec1.id, spec2.id],
        }, format='json')

        assert res.status_code == 422

    def test_ai_pick_requires_authentication(self, api_client):
        res = api_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [1, 2],
        }, format='json')
        assert res.status_code == 401

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_pick_does_not_mutate_database(self, mock_ai, authenticated_client):
        """ai-pick is read-only — must NOT change any spec records."""
        spec1 = _spec('Zeekr', '7X', horsepower='475 HP')
        spec2 = _spec('Zeekr', '7X', horsepower='55 HP')
        original_hp1 = spec1.horsepower
        original_hp2 = spec2.horsepower
        mock_ai.return_value = self._make_gemini_mock(spec1.id)

        authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [spec1.id, spec2.id],
        }, format='json')

        spec1.refresh_from_db()
        spec2.refresh_from_db()
        # Nothing should have changed
        assert spec1.horsepower == original_hp1
        assert spec2.horsepower == original_hp2
        assert CarSpecification.objects.filter(id=spec2.id).exists()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_pick_records_reviewed_count(self, mock_ai, authenticated_client):
        """records_reviewed reflects how many specs were sent to Gemini."""
        specs = [_spec('AITO', 'M8') for _ in range(3)]
        mock_ai.return_value = self._make_gemini_mock(specs[0].id)

        res = authenticated_client.post('/api/v1/car-specifications/ai-pick/', {
            'spec_ids': [s.id for s in specs],
        }, format='json')

        assert res.status_code == 200
        assert res.json()['records_reviewed'] == 3
