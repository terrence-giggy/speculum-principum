# Makefile for Speculum Principum

.PHONY: help install test test-unit test-integration lint format clean coverage security type-check

# Default target
help:
	@echo "Available targets:"
	@echo "  install          Install dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black"
	@echo "  coverage         Generate coverage report"
	@echo "  security         Run security checks"
	@echo "  type-check       Run type checking"
	@echo "  clean            Clean up generated files"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

# Development dependencies
install-dev: install
	pip install pytest pytest-cov pytest-mock responses
	pip install flake8 black isort mypy types-requests
	pip install safety bandit

# Run all tests
test:
	pytest tests/ -v

# Run unit tests only
test-unit:
	pytest tests/ -v -m "not integration"

# Run integration tests only
test-integration:
	pytest tests/ -v -m integration

# Run tests with coverage
coverage:
	pytest tests/ -v --cov=src --cov=main --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

# Linting
lint:
	flake8 src/ main.py tests/
	isort --check-only src/ main.py tests/
	black --check src/ main.py tests/

# Format code
format:
	isort src/ main.py tests/
	black src/ main.py tests/

# Security checks
security:
	safety check
	bandit -r src/ main.py

# Type checking
type-check:
	mypy src/ main.py --ignore-missing-imports

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Quick development test (unit tests only, no coverage)
test-quick:
	pytest tests/ -x -v -m "not integration"

# Test with verbose output and stop on first failure
test-debug:
	pytest tests/ -v -s --tb=long -x

# Run specific test file
test-file:
	@read -p "Enter test file name (e.g., test_main.py): " file; \
	pytest tests/$$file -v

# Create test issue (requires environment variables)
create-test-issue:
	python main.py create-issue --title "Test Issue $(shell date '+%Y-%m-%d %H:%M:%S')" --body "This is a test issue created at $(shell date)" --labels "test" "automated"