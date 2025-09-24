# Test Organization

This document describes the organization of the test suite for the Speculum Principum project.

## Test Structure

The tests are organized to mirror the source code structure for better maintainability:

```
tests/
├── unit/                   # Unit tests for individual modules
│   ├── clients/           # Tests for client modules
│   │   ├── test_github_issue_creator.py
│   │   └── test_search_client.py
│   ├── core/             # Tests for core business logic
│   │   ├── test_batch_processor.py
│   │   ├── test_deduplication.py
│   │   ├── test_issue_processor.py
│   │   └── test_site_monitor.py
│   ├── storage/          # Tests for storage components
│   │   └── test_git_manager.py
│   ├── utils/            # Tests for utility modules
│   │   ├── test_cli.py
│   │   ├── test_config_manager.py
│   │   └── test_error_handling.py
│   └── workflow/         # Tests for workflow components
│       ├── test_deliverable_generator.py
│       ├── test_template_engine.py
│       ├── test_workflow_matcher.py
│       └── test_workflow_schemas.py
├── integration/          # Integration tests
│   ├── test_github_integration.py
│   ├── test_main.py
│   └── test_smoke.py
└── e2e/                  # End-to-end tests
    └── test_github_integration.py
```

## Test Categories

### Unit Tests (`tests/unit/`)
- Test individual modules in isolation
- Use extensive mocking to isolate components
- Fast execution
- High coverage of edge cases

### Integration Tests (`tests/integration/`)
- Test interactions between components
- Limited mocking, focus on real interactions
- Test main application flows
- Smoke tests for basic functionality

### End-to-End Tests (`tests/e2e/`)
- Test complete user workflows
- Minimal mocking
- Test with real external dependencies where possible
- May require specific environment setup

## Running Tests

### All Tests
```bash
python -m pytest tests/
```

### Specific Categories
```bash
# Unit tests only
python -m pytest tests/unit/

# Integration tests only
python -m pytest tests/integration/

# E2E tests only
python -m pytest tests/e2e/

# Specific module
python -m pytest tests/unit/core/test_issue_processor.py
```

### Test Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

## Test Configuration

- `conftest.py`: Shared test fixtures and configuration
- `pyproject.toml`: Pytest configuration including coverage settings
- Test discovery follows pytest conventions

## Skipped Tests

Some tests may be skipped in certain environments:
- Tests requiring real GitHub credentials
- Tests requiring network access
- Environment-specific tests

These are marked with `@pytest.mark.skip()` or conditional skipping.