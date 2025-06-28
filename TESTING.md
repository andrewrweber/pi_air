# Testing Guide for Pi Air Monitor

This document describes the comprehensive testing framework for the Pi Air Monitor project.

## Overview

The project includes multiple types of tests to ensure reliability and maintainability:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **API Tests**: Test Flask endpoints and responses
- **Frontend Tests**: Test JavaScript modules
- **Hardware Tests**: Test hardware-specific functionality (requires Pi)

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_database.py         # Database module tests
├── test_api_routes.py       # Flask API endpoint tests  
├── test_hardware_monitoring.py # Hardware monitoring tests
└── frontend/
    ├── test_runner.html     # Frontend test runner
    ├── test_utils.js        # Utils module tests
    ├── test_config.js       # Config module tests
    ├── test_charts.js       # Charts module tests
    └── test_air_quality.js  # Air quality module tests
```

## Quick Start

### Backend Tests (Python)

1. **Install test dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run all tests:**
   ```bash
   pytest
   ```

3. **Run specific test categories:**
   ```bash
   # Unit tests only
   pytest -m unit
   
   # API tests only
   pytest -m api
   
   # Database tests only
   pytest -m database
   
   # Skip hardware tests (useful for development)
   pytest -m "not hardware"
   ```

4. **Run with coverage:**
   ```bash
   pytest --cov=src --cov-report=html
   ```

### Frontend Tests (JavaScript)

1. **Open the test runner in a browser:**
   ```bash
   # Start a local server (optional but recommended)
   python -m http.server 8000
   
   # Open in browser
   open http://localhost:8000/tests/frontend/test_runner.html
   ```

2. **View test results in the browser console and page**

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Test individual functions and classes in isolation:

```python
@pytest.mark.unit
def test_aqi_calculation():
    assert calculate_aqi(12) == 50
```

### Integration Tests (`@pytest.mark.integration`)

Test component interactions:

```python
@pytest.mark.integration
def test_complete_air_quality_workflow(client):
    # Test full data flow from insertion to API response
```

### API Tests (`@pytest.mark.api`)

Test Flask endpoints:

```python
@pytest.mark.api
def test_system_api_route(client, mock_psutil):
    response = client.get('/api/system')
    assert response.status_code == 200
```

### Database Tests (`@pytest.mark.database`)

Test database operations:

```python
@pytest.mark.database
def test_insert_air_quality_reading(test_db):
    database.insert_air_quality_reading(pm2_5=12.5, aqi=50)
```

### Hardware Tests (`@pytest.mark.hardware`)

Test hardware-specific functionality (requires Raspberry Pi):

```python
@pytest.mark.hardware
@pytest.mark.skipif(not Path('/dev/ttyS0').exists(), reason="No serial port")
def test_real_serial_port_access():
    # Test actual hardware
```

### Slow Tests (`@pytest.mark.slow`)

Tests that take longer to execute:

```python
@pytest.mark.slow
def test_long_running_monitor():
    # Test that runs for extended time
```

## Fixtures

Common test fixtures are available in `conftest.py`:

### `client`
Flask test client with in-memory database:
```python
def test_api_endpoint(client):
    response = client.get('/api/stats')
```

### `test_db`
Temporary test database:
```python
def test_database_operation(test_db):
    # Use test_db path for database operations
```

### `mock_psutil`
Mocked system monitoring functions:
```python
def test_system_monitoring(mock_psutil):
    # psutil functions return predictable test data
```

### `sample_air_quality_data`
Sample air quality data for testing:
```python
def test_air_quality_insertion(sample_air_quality_data):
    database.insert_air_quality_reading(**sample_air_quality_data)
```

## Running Tests in Different Environments

### Development Environment

```bash
# Run all tests except hardware-specific ones
pytest -m "not hardware"

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_database.py
```

### Raspberry Pi

```bash
# Run all tests including hardware tests
pytest

# Run only hardware tests
pytest -m hardware

# Test actual serial communication
pytest tests/test_hardware_monitoring.py::test_real_serial_port_access
```

### Continuous Integration

```bash
# Run with coverage and exclude slow/hardware tests
pytest -m "not slow and not hardware" --cov=src --cov-fail-under=80
```

## Test Configuration

### pytest.ini

The `pytest.ini` file configures:
- Test discovery patterns
- Coverage reporting
- Test markers
- Output formatting

### Coverage

Coverage reports are generated in:
- Terminal: `--cov-report=term-missing`
- HTML: `--cov-report=html:htmlcov` (view at `htmlcov/index.html`)

Target coverage: **80% minimum**

## Writing New Tests

### Backend Tests

1. **Create test file**: `tests/test_<module_name>.py`
2. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
3. **Use fixtures**: Leverage existing fixtures for common setup
4. **Mock external dependencies**: Use `unittest.mock` for external services

Example:
```python
@pytest.mark.unit
class TestNewFeature:
    def test_basic_functionality(self, client):
        # Test implementation
        assert True
        
    def test_error_handling(self):
        with pytest.raises(ValueError):
            # Test error conditions
            pass
```

### Frontend Tests

1. **Add test to appropriate file**: `tests/frontend/test_<module>.js`
2. **Use test framework methods**: `tester.test()`, `tester.assert()`, etc.
3. **Test public APIs**: Focus on module interfaces and expected behavior

Example:
```javascript
tester.test('New feature works', () => {
    const result = MyModule.newFeature();
    tester.assertNotNull(result);
    tester.assertEqual(result.status, 'success');
});
```

## Debugging Tests

### Failed Test Investigation

1. **Run with verbose output**: `pytest -v -s`
2. **Run single test**: `pytest tests/test_file.py::test_function`
3. **Use debugger**: Add `import pdb; pdb.set_trace()` in test
4. **Check logs**: Tests disable logging by default, remove `disable_logging` fixture if needed

### Common Issues

- **Database tests**: Ensure proper cleanup with `test_db` fixture
- **API tests**: Mock external dependencies (psutil, vcgencmd, serial)
- **Frontend tests**: Browser compatibility and DOM availability
- **Hardware tests**: Requires actual Raspberry Pi hardware

## Performance Considerations

- **Parallel execution**: Tests run in parallel by default
- **Database isolation**: Each test gets fresh database
- **Mock external calls**: Avoid real network/hardware calls in unit tests
- **Resource cleanup**: Fixtures handle automatic cleanup

## Best Practices

1. **Test naming**: Use descriptive names that explain what's being tested
2. **Test isolation**: Each test should be independent
3. **Mock appropriately**: Mock external dependencies, not internal logic
4. **Test edge cases**: Include error conditions and boundary values
5. **Keep tests simple**: One concept per test
6. **Use appropriate markers**: Help categorize and filter tests
7. **Document complex tests**: Add comments for non-obvious test logic

## Continuous Improvement

- **Monitor coverage**: Aim for high coverage of critical paths
- **Regular test runs**: Run tests before commits
- **Update tests**: Modify tests when changing functionality
- **Add integration tests**: Ensure components work together
- **Performance testing**: Consider adding performance benchmarks