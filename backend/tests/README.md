# Fresh Motors - Test Suite

## Running Tests

### Run all tests:
```bash
cd backend
pytest
```

### Run specific test file:
```bash
pytest tests/test_seo_helpers.py
pytest tests/test_search_api.py
pytest tests/test_analytics_api.py
```

### Run with verbose output:
```bash
pytest -v
```

### Run only unit tests (fast):
```bash
pytest -m unit
```

### Run only integration tests:
```bash
pytest -m integration
```

## Test Coverage

### SEO Tests (`test_seo_helpers.py`)
- ✅ Basic keyword generation
- ✅ EV/Hybrid/SUV specific keywords
- ✅ Unknown values handling
- ✅ String input safety (regression test for the bug we fixed)
- ✅ HTML tag removal
- ✅ Stop word filtering

### Search API Tests (`test_search_api.py`)
- ✅ Search by title, content, keywords
- ✅ Filter by category
- ✅ Filter by tags
- ✅ Sort by newest/popular
- ✅ Pagination
- ✅ Unpublished/deleted article filtering
- ✅ Empty results handling

### Analytics API Tests (`test_analytics_api.py`)
- ✅ Overview statistics
- ✅ Authentication required
- ✅ Top articles by views
- ✅ Views timeline (30 days)
- ✅ Categories distribution
- ✅ Growth percentage calculation

### Article Generation Tests (`test_article_generation.py`)
- ✅ Video info extraction
- ✅ Title extraction
- ✅ Content formatting
- ✅ Image distribution
- ✅ Article publishing
- ✅ Tags and specs handling

## Adding New Tests

1. Create new file: `tests/test_<feature>.py`
2. Import pytest: `import pytest`
3. Use `@pytest.mark.django_db` for DB tests
4. Write test functions starting with `test_`
5. Run: `pytest tests/test_<feature>.py`

## CI/CD Integration

Add to `.github/workflows/tests.yml`:
```yaml
- name: Run tests
  run: |
    cd backend
    pytest --tb=short
```

## Notes

- Tests use SQLite in-memory database (fast!)
- Fixtures defined in `conftest.py`
- Mock external API calls (Groq, YouTube)
- Keep tests independent and idempotent
