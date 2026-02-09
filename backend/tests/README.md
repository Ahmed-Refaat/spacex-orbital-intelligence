# Tests - SpaceX Orbital Intelligence

## Test Coverage Status

**Current Coverage:** ~60% (estimated with new tests)  
**Target:** 80%+ for NASA-grade

## Test Structure

```
tests/
├── conftest.py                         # Shared fixtures
├── test_async_orbital_engine.py        # AsyncOrbitalEngine tests (✅ Complete)
├── test_satellites_omm_security.py     # OMM security tests (✅ Complete)
├── test_performance_api.py             # Performance API tests (✅ Complete)
├── test_spice_client.py                # SPICE client tests (✅ Existing)
└── integration/                        # Integration tests (TODO)
    ├── test_omm_e2e.py                 # OMM upload → query flow
    └── test_spice_fallback.py          # SPICE down → SGP4 fallback
```

## Running Tests

### All Tests

```bash
cd backend
pytest
```

### With Coverage

```bash
pytest --cov=app --cov-report=html
```

Opens `htmlcov/index.html` to view detailed coverage.

### Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests (requires services)
pytest -m integration

# Security tests
pytest -m security

# Performance benchmarks
pytest -m performance
```

### Specific Test Files

```bash
# Async engine tests
pytest tests/test_async_orbital_engine.py -v

# Security tests
pytest tests/test_satellites_omm_security.py -v

# Performance API tests
pytest tests/test_performance_api.py -v
```

## Test Markers

Tests are categorized with markers:

- `@pytest.mark.unit` - Fast unit tests (no external dependencies)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.slow` - Tests taking >1s
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.performance` - Performance benchmarks

## CI/CD Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Via GitHub Actions (see `.github/workflows/ci.yml`)

## Coverage Requirements

**NASA-Grade Requirements:**
- **Minimum:** 80% line coverage
- **Recommended:** 90% line coverage
- **Branch coverage:** 60%+

**Current Status:**

| Module | Coverage | Status |
|--------|----------|--------|
| `async_orbital_engine.py` | ~85% | ✅ Good |
| `spice_client.py` | ~70% | 🟡 Needs improvement |
| `api/satellites.py` | ~60% | 🟡 Needs improvement |
| `api/performance.py` | ~75% | ✅ Good |
| **Overall** | **~60%** | 🟡 **In Progress** |

## Writing New Tests

### Test Naming Convention

```python
# Format: test_<function>_<scenario>
def test_propagate_single_success():
    """Test successful single satellite propagation."""
    pass

def test_propagate_single_failure():
    """Test propagation failure handling."""
    pass
```

### Using Fixtures

```python
def test_with_fixtures(mock_async_engine, sample_omm_xml):
    """Use fixtures defined in conftest.py."""
    result = await mock_async_engine.propagate_single("25544")
    assert result is not None
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    """Async test example."""
    result = await some_async_function()
    assert result is not None
```

### Mocking External Services

```python
from unittest.mock import AsyncMock, patch

@patch('app.services.spice_client.httpx.AsyncClient')
def test_with_mock(mock_client):
    """Mock external HTTP calls."""
    mock_client.get = AsyncMock(return_value=Mock(status_code=200))
    # Test code here
```

## Test Data

Sample data is available via fixtures:

- `sample_omm_xml` - Valid OMM XML
- `sample_malicious_xml` - XXE attack payload
- `sample_xml_bomb` - Billion laughs attack
- `mock_orbital_engine` - Mocked SGP4 engine
- `mock_spice_client` - Mocked SPICE client
- `mock_async_engine` - Mocked AsyncOrbitalEngine

## Security Testing

Security tests validate:

- ✅ XXE (XML External Entity) prevention
- ✅ XML bomb (billion laughs) prevention
- ✅ DTD forbidden
- ✅ External entities forbidden
- ✅ File size limits (10MB)
- ✅ Rate limiting (10/min)
- ✅ Input validation

Run security tests:

```bash
pytest -m security -v
```

## Performance Testing

Performance tests benchmark:

- Single satellite propagation (<10ms target)
- Batch propagation scaling
- SGP4 vs SPICE comparison

Run performance tests:

```bash
pytest -m performance -v
```

## Integration Testing

Integration tests require services:

```bash
# Start services
docker-compose up -d

# Run integration tests
pytest -m integration

# Stop services
docker-compose down
```

## Troubleshooting

### Tests Failing with "RuntimeError: Not initialized"

**Cause:** AsyncOrbitalEngine not initialized in test

**Fix:** Use `mock_async_engine` fixture or initialize in test setup

### Tests Timing Out

**Cause:** Async tests not properly awaited

**Fix:** Add `@pytest.mark.asyncio` and use `await`

### Import Errors

**Cause:** Missing dependencies

**Fix:**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Redis Connection Errors

**Cause:** Redis not running

**Fix:**
```bash
# Start Redis
docker-compose up -d redis

# Or use mock
@patch('app.services.cache.redis_client')
```

## TODO - Remaining Tests (to reach 80%)

**Priority 1 (Critical):**
- [ ] `test_satellites_api.py` - Full satellites API coverage
- [ ] `test_orbital_engine.py` - SGP4 engine tests
- [ ] `test_tle_service.py` - TLE loading/caching
- [ ] Integration tests (E2E OMM flow)

**Priority 2 (Important):**
- [ ] `test_monitoring.py` - Monitoring endpoints
- [ ] `test_cache.py` - Redis cache layer
- [ ] `test_websocket.py` - WebSocket connections
- [ ] Load tests with k6/Locust

**Priority 3 (Nice-to-have):**
- [ ] Frontend tests (Vitest/Jest)
- [ ] E2E tests (Playwright)
- [ ] Visual regression tests

## Contributing

When adding new code:

1. **Write tests first** (TDD)
2. **Run tests locally** (`pytest -v`)
3. **Check coverage** (`pytest --cov`)
4. **Ensure 80%+ coverage** for new code
5. **Pre-commit hooks** (`pre-commit run --all-files`)

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Last Updated:** 2026-02-09  
**Maintainer:** James (AI Assistant)
