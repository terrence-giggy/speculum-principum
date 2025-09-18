#!/bin/bash

# Test runner script for Speculum Principum
# This script provides convenient test execution options

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Print header
print_header() {
    echo
    print_color $BLUE "=================================="
    print_color $BLUE "$1"
    print_color $BLUE "=================================="
    echo
}

# Check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_color $RED "Error: pytest is not installed"
        print_color $YELLOW "Run: pip install -r requirements.txt"
        exit 1
    fi
}

# Run unit tests
run_unit_tests() {
    print_header "Running Unit Tests"
    check_pytest
    pytest tests/ -v -m "not integration" --tb=short
}

# Run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    check_pytest
    
    # Check for required environment variables
    if [[ -z "$GITHUB_TOKEN" || -z "$GITHUB_REPOSITORY" ]]; then
        print_color $YELLOW "Warning: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables should be set for integration tests"
        print_color $YELLOW "Some integration tests may be skipped"
    fi
    
    pytest tests/ -v -m integration --tb=short
}

# Run all tests
run_all_tests() {
    print_header "Running All Tests"
    check_pytest
    pytest tests/ -v --tb=short
}

# Run tests with coverage
run_coverage() {
    print_header "Running Tests with Coverage"
    check_pytest
    pytest tests/ -v --cov=src --cov=main --cov-report=term-missing --cov-report=html --tb=short
    print_color $GREEN "Coverage report generated in htmlcov/"
}

# Run linting
run_lint() {
    print_header "Running Linting Checks"
    
    if command -v flake8 &> /dev/null; then
        print_color $BLUE "Running flake8..."
        flake8 src/ main.py tests/ || print_color $YELLOW "flake8 found issues"
    else
        print_color $YELLOW "flake8 not installed, skipping"
    fi
    
    if command -v black &> /dev/null; then
        print_color $BLUE "Checking code formatting with black..."
        black --check src/ main.py tests/ || print_color $YELLOW "black formatting issues found"
    else
        print_color $YELLOW "black not installed, skipping"
    fi
}

# Run security checks
run_security() {
    print_header "Running Security Checks"
    
    if command -v safety &> /dev/null; then
        print_color $BLUE "Running safety check..."
        safety check || print_color $YELLOW "safety found potential vulnerabilities"
    else
        print_color $YELLOW "safety not installed, skipping"
    fi
    
    if command -v bandit &> /dev/null; then
        print_color $BLUE "Running bandit security linter..."
        bandit -r src/ main.py || print_color $YELLOW "bandit found potential security issues"
    else
        print_color $YELLOW "bandit not installed, skipping"
    fi
}

# Clean up test artifacts
clean_test_artifacts() {
    print_header "Cleaning Test Artifacts"
    
    rm -rf __pycache__/
    rm -rf .pytest_cache/
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .mypy_cache/
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    
    print_color $GREEN "Test artifacts cleaned"
}

# Show help
show_help() {
    echo "Speculum Principum Test Runner"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  unit         Run unit tests only"
    echo "  integration  Run integration tests only"
    echo "  all          Run all tests"
    echo "  coverage     Run tests with coverage report"
    echo "  lint         Run linting checks"
    echo "  security     Run security checks"
    echo "  clean        Clean test artifacts"
    echo "  help         Show this help message"
    echo
    echo "Examples:"
    echo "  $0 unit"
    echo "  $0 coverage"
    echo "  $0 all"
}

# Main script logic
case "$1" in
    "unit")
        run_unit_tests
        ;;
    "integration")
        run_integration_tests
        ;;
    "all")
        run_all_tests
        ;;
    "coverage")
        run_coverage
        ;;
    "lint")
        run_lint
        ;;
    "security")
        run_security
        ;;
    "clean")
        clean_test_artifacts
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    "")
        print_color $YELLOW "No option specified. Running all tests..."
        run_all_tests
        ;;
    *)
        print_color $RED "Unknown option: $1"
        show_help
        exit 1
        ;;
esac

print_color $GREEN "Done!"