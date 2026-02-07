# Test Optimization Plan

## Problem Summary
- 3 test directories timeout after 600 seconds
- Main culprit: `test_spec_pipeline_orchestrator.py` - integration tests that run real code
- Autouse fixture adding overhead to every test

## Optimization Strategies

### 1. Use Pytest Markers (Immediate Impact)

Already defined in `pytest.ini`:
```ini
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
```

**Action:** Mark slow integration tests:

```python
@pytest.mark.slow
@pytest.mark.integration
async def test_run_with_auto_approve(self, tmp_path):
    ...
```

**Run fast tests only:**
```bash
pytest -m "not slow" -v
pytest -m "not integration" -v
```

**Run all tests when needed:**
```bash
pytest -v  # or explicitly: pytest -m "slow or integration" -v
```

### 2. Fix Autouse Fixture Overhead

The `ensure_modules_not_mocked()` fixture runs before EVERY test.

**Action:** Remove autouse or make it conditional:

```python
@pytest.fixture(autouse=True, scope="function")
def ensure_modules_not_mocked():
    """Only run for tests that need real claude_agent_sdk"""
    # Skip for tests that explicitly mock everything
    if os.environ.get("PYTEST_SKIP_MODULE_CLEANUP"):
        return
    # ... existing code ...
```

### 3. Separate Unit and Integration Tests

**Directory structure:**
```
tests/
├── unit/           # Fast tests (seconds)
│   ├── test_*.py
├── integration/    # Slow tests (minutes)
│   ├── test_*.py
└── e2e/           # Very slow tests (10+ minutes)
    ├── test_*.py
```

**pytest.ini:**
```ini
[pytest]
testpaths = tests/unit  # Default to fast tests
# Override with: pytest --testpaths=integration
```

### 4. Optimize Async Tests

Async tests have overhead. Use sync tests where possible:

```python
# SLOW (async overhead)
@pytest.mark.asyncio
async def test_something():
    result = await some_async_function()
    assert result

# FASTER (mock the async call)
def test_something():
    with patch('module.some_async_function', return_value=expected):
        result = some_function_that_calls_async()
        assert result
```

### 5. Reduce Test Data Creation

Many tests create large temporary directories. Use shared fixtures:

```python
@pytest.fixture(scope="session")
def shared_test_data():
    """Create test data once per session, not per test"""
    data = create_expensive_test_data()
    yield data
    # cleanup runs at session end
```

### 6. Disable Coverage by Default

Coverage collection adds overhead.

**pytest.ini:**
```ini
[pytest]
addopts = -q --tb=short  # No --cov
# Enable coverage explicitly: pytest --cov=apps/backend
```

### 7. Increase Timeout for Integration Tests

For tests that must be slow:

```python
@pytest.mark.timeout(300)  # 5 minutes for this specific test
async def test_slow_integration():
    ...
```

### 8. Use Test Profiles

Create pytest configs for different scenarios:

**pytest.unit.ini:**
```ini
[pytest]
testpaths = tests
addopts = -m "not slow and not integration" -q
```

**pytest.all.ini:**
```ini
[pytest]
testpaths = tests
addopts = -v
timeout = 1200  # 20 minutes
```

**Usage:**
```bash
pytest -c pytest.unit.ini      # Fast PR checks
pytest -c pytest.all.ini       # Full test suite
```

### 9. Mock Expensive Operations

Identify what's actually slow in the tests:

```python
# SLOW - Real file I/O
async def test_orchestrator():
    orchestrator = SpecOrchestrator(project_dir)
    await orchestrator.run()  # Does real file operations

# FASTER - Mock the expensive parts
async def test_orchestrator():
    with patch('spec.pipeline.orchestrator.discover_project'):
        with patch('spec.pipeline.orchestrator.write_files'):
            orchestrator = SpecOrchestrator(project_dir)
            await orchestrator.run()  # Just tests the logic
```

### 10. Run Tests in Parallel (Already Done)

Use the scripts we created:
```bash
./scripts/run-parallel-tests.sh       # Directory-level
./scripts/run-tests-per-file.sh       # File-level
```

## Implementation Priority

1. **HIGH** - Mark slow/integration tests (5 minutes)
   - Add `@pytest.mark.slow` to `test_spec_pipeline_orchestrator.py`
   - Add `@pytest.mark.integration` to integration tests

2. **HIGH** - Update CI to run fast tests by default (10 minutes)
   - CI: `pytest -m "not slow"` for PR checks
   - CI: `pytest` (full) for main branch

3. **MEDIUM** - Fix autouse fixture (30 minutes)
   - Remove autouse or make it conditional

4. **MEDIUM** - Create test profiles (1 hour)
   - Separate unit/integration configs

5. **LOW** - Refactor slow tests (ongoing)
   - Better mocking
   - Shared fixtures

## Quick Win Script

Add to Makefile or scripts:

```bash
# makefile or script
test-fast:
    pytest -m "not slow" -v

test-all:
    pytest -v

test-integration:
    pytest -m "integration" -v
```
