# Makefile for Folly testing and development

.PHONY: test test-unit test-system test-integration coverage clean install help

# Default target
help:
	@echo "Available targets:"
	@echo "  install       - Install the package in development mode with test dependencies"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-system   - Run system tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-quick    - Run quick tests (unit tests only)"
	@echo "  coverage      - Run tests with coverage report"
	@echo "  coverage-html - Generate HTML coverage report"
	@echo "  clean         - Clean up temporary files and caches"
	@echo "  lint          - Run code quality checks (if available)"

# Install the package and dependencies
install:
	pip install -e ".[test]"

# Run all tests
test:
	python run_tests.py

# Run unit tests only
test-unit:
	python run_tests.py --type unit

# Run system tests only  
test-system:
	python run_tests.py --type system

# Run integration tests only
test-integration:
	python run_tests.py --type integration

# Run quick tests (unit tests, exclude slow ones)
test-quick:
	python run_tests.py --quick

# Run tests with coverage
coverage:
	python run_tests.py --type unit --coverage

# Generate HTML coverage report
coverage-html:
	python run_tests.py --coverage
	@echo "Coverage report generated in htmlcov/"
	@echo "Open htmlcov/index.html in your browser"

# Clean up temporary files
clean:
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */*/__pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/
	rm -rf flask_session/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Code quality checks (if tools are available)
lint:
	@command -v flake8 >/dev/null 2>&1 && flake8 Folly/ || echo "flake8 not installed, skipping"
	@command -v pylint >/dev/null 2>&1 && pylint Folly/ || echo "pylint not installed, skipping"
	@command -v black >/dev/null 2>&1 && black --check Folly/ || echo "black not installed, skipping"

# Continuous integration target
ci: clean install test coverage