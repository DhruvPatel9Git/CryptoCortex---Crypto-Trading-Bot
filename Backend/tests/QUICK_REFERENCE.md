# Quick Reference Guide - Testing Commands

## Installation

```bash
# Navigate to Backend directory
cd Backend

# Install test dependencies
pip install -r tests/requirements-test.txt
```

## Basic Commands

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/routes/test_auth_routes.py
pytest tests/routes/test_trading.py
```

### Run Tests by Name Pattern

```bash
# Run all login tests
pytest tests/ -k "login"

# Run all buy/sell tests
pytest tests/ -k "buy or sell"
```

### Verbose Output

```bash
pytest tests/ -v
```

### Show Print Statements

```bash
pytest tests/ -s
```

## Coverage Commands

### Basic Coverage

```bash
pytest tests/ --cov=routes
```

### Coverage with Missing Lines

```bash
pytest tests/ --cov=routes --cov-report=term-missing
```

### HTML Coverage Report

```bash
pytest tests/ --cov=routes --cov-report=html
# Open htmlcov/index.html in browser
```

### XML Coverage (for CI/CD)

```bash
pytest tests/ --cov=routes --cov-report=xml
```

## Using Test Runner Script

### Run All Tests

```bash
python tests/run_tests.py all
```

### Run Specific Module

```bash
python tests/run_tests.py auth
python tests/run_tests.py cart
python tests/run_tests.py credits
python tests/run_tests.py crypto
python tests/run_tests.py balance
python tests/run_tests.py ohlc
python tests/run_tests.py portfolio
python tests/run_tests.py qa
python tests/run_tests.py trading
python tests/run_tests.py websocket
```

### Coverage Reports

```bash
python tests/run_tests.py coverage
python tests/run_tests.py coverage-html
```

## Advanced Options

### Stop on First Failure

```bash
pytest tests/ -x
```

### Run Last Failed Tests

```bash
pytest tests/ --lf
```

### Run Failed Tests First

```bash
pytest tests/ --ff
```

### Parallel Execution (with pytest-xdist)

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

### Show Test Durations

```bash
pytest tests/ --durations=10
```

### Quiet Mode

```bash
pytest tests/ -q
```

## Markers

### Run Only Async Tests

```bash
pytest tests/ -m asyncio
```

### Run Only Unit Tests

```bash
pytest tests/ -m unit
```

### Skip Slow Tests

```bash
pytest tests/ -m "not slow"
```

## Debugging

### Drop into PDB on Failure

```bash
pytest tests/ --pdb
```

### Show Local Variables on Failure

```bash
pytest tests/ --showlocals
```

### Capture No Output (see all prints)

```bash
pytest tests/ --capture=no
```

## Output Formats

### JUnit XML (for Jenkins, GitLab CI)

```bash
pytest tests/ --junit-xml=test-results.xml
```

### JSON Report

```bash
pip install pytest-json-report
pytest tests/ --json-report --json-report-file=report.json
```

## Filtering

### By Test Class

```bash
pytest tests/routes/test_auth_routes.py::TestLoginEndpoint
```

### By Specific Test

```bash
pytest tests/routes/test_auth_routes.py::TestLoginEndpoint::test_login_success_with_json
```

### Multiple Patterns

```bash
pytest tests/ -k "test_success or test_error"
```

## Common Issues & Solutions

### Import Errors

```bash
# Add Backend to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"
# or on Windows PowerShell
$env:PYTHONPATH = "${env:PYTHONPATH};${PWD}"
```

### Async Test Errors

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

### Coverage Not Working

```bash
# Install coverage
pip install pytest-cov
```

## Quick Test Development

### Create New Test

```python
# In tests/routes/test_my_new_route.py
import pytest
from unittest.mock import AsyncMock, patch

class TestMyNewEndpoint:
    @pytest.mark.asyncio
    async def test_my_function(self):
        """Test description."""
        # Arrange
        mock_data = {"key": "value"}

        # Act
        with patch("routes.my_route.dependency", new_callable=AsyncMock):
            result = await my_function()

        # Assert
        assert result["status"] == "success"
```

### Run Your New Test

```bash
pytest tests/routes/test_my_new_route.py -v
```

## CI/CD Integration

### GitHub Actions

See: `tests/github_actions_example.yml`

### GitLab CI

```yaml
test:
  script:
    - pip install -r Backend/tests/requirements-test.txt
    - cd Backend
    - pytest tests/ --cov=routes --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### Jenkins

```groovy
stage('Test') {
    steps {
        sh 'pip install -r Backend/tests/requirements-test.txt'
        sh 'cd Backend && pytest tests/ --junit-xml=test-results.xml'
    }
}
```

## Performance Tips

1. **Use pytest-xdist** for parallel execution
2. **Cache fixtures** that are expensive to create
3. **Mock external calls** (already done in these tests)
4. **Use markers** to skip slow tests during development
5. **Run specific modules** instead of full suite during development

## Getting Help

```bash
# Show all pytest options
pytest --help

# Show available fixtures
pytest --fixtures

# Show markers
pytest --markers
```

## Recommended Workflow

### During Development

```bash
# Run only the tests you're working on
pytest tests/routes/test_auth_routes.py::TestLoginEndpoint -v
```

### Before Commit

```bash
# Run all tests with coverage
python tests/run_tests.py coverage
```

### In CI/CD

```bash
# Full suite with coverage and reports
pytest tests/ --cov=routes --cov-report=xml --cov-report=html --junit-xml=test-results.xml
```
