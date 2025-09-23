# RARSMS Project Makefile
.PHONY: help test test-verbose test-coverage test-specific clean setup check-status docker-build docker-test lint

# Default target
help:
	@echo "RARSMS Development Commands"
	@echo "=========================="
	@echo "Test Commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-verbose      - Run tests with verbose output"
	@echo "  make test-coverage     - Run tests with coverage reporting"
	@echo "  make test-specific     - Run specific test (usage: make test-specific TEST=aprs)"
	@echo "  make check-status      - Check test environment status"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup             - Install dependencies and setup test environment"
	@echo "  make clean             - Clean up generated files"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build      - Build Docker image"
	@echo "  make docker-test       - Test Docker image"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make lint              - Run linting (if available)"
	@echo ""
	@echo "Available test categories:"
	@echo "  aprs, discord, base, interchange, config, manager, integration"

# Run all tests
test:
	@python -m pytest tests/ -v --tb=short

# Run tests with verbose output and markers
test-verbose:
	@python -m pytest tests/ -v -s --tb=long

# Run tests with coverage
test-coverage:
	@python -m pytest tests/ --cov=protocols --cov=main --cov-report=term-missing --cov-report=html

# Run specific test category
test-specific:
	@if [ -z "$(TEST)" ]; then \
		echo "Usage: make test-specific TEST=<category>"; \
		echo "Available categories: aprs, discord, base, interchange, config, manager, integration"; \
	else \
		python run_tests.py $(TEST); \
	fi

# Check test environment status
check-status:
	@python test_status.py

# Setup development environment
setup:
	@echo "Setting up RARSMS development environment..."
	@pip install -r requirements.txt
	@if [ ! -f config.yaml ]; then cp config.example.yaml config.yaml; fi
	@if [ ! -f callsigns.txt ]; then echo -e "# Test callsigns\nTEST-1\nW4ABC\nKJ4XYZ" > callsigns.txt; fi
	@echo "✅ Setup complete! Run 'make test' to verify."

# Clean generated files
clean:
	@echo "Cleaning up generated files..."
	@rm -rf __pycache__ .pytest_cache htmlcov/ .coverage
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete."

# Build Docker image
docker-build:
	@echo "Building RARSMS Docker image..."
	@docker build -t rarsms-test .
	@echo "✅ Docker build complete."

# Test Docker image
docker-test: docker-build
	@echo "Testing Docker image..."
	@docker run --rm rarsms-test python -c "import protocols.base; import protocols.aprs; print('✅ Docker image working')"

# Run linting if available
lint:
	@echo "Running code quality checks..."
	@if command -v flake8 >/dev/null 2>&1; then \
		echo "Running flake8..."; \
		flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics; \
		flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics; \
	else \
		echo "flake8 not available, skipping linting"; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		echo "Checking code formatting with black..."; \
		black --check --diff . || echo "Run 'black .' to fix formatting"; \
	else \
		echo "black not available, install with: pip install black"; \
	fi

# Quick development test - runs fastest tests only
test-quick:
	@python -m pytest tests/test_base.py tests/test_config.py -v --tb=short

# Run tests in parallel (if pytest-xdist is available)
test-parallel:
	@if python -c "import pytest_xdist" 2>/dev/null; then \
		python -m pytest tests/ -n auto -v; \
	else \
		echo "pytest-xdist not available, running normally"; \
		make test; \
	fi

# Integration tests only
test-integration:
	@python -m pytest tests/test_integration.py -v --tb=short

# Install development dependencies
setup-dev: setup
	@echo "Installing development dependencies..."
	@pip install flake8 black isort coverage pytest-cov pytest-xdist || echo "Some dev dependencies failed to install"
	@echo "✅ Development setup complete!"

# Show test statistics
stats:
	@echo "RARSMS Test Statistics"
	@echo "====================="
	@echo "Test files: $$(find tests/ -name 'test_*.py' | wc -l)"
	@echo "Source files: $$(find . -name '*.py' -not -path './test_env/*' -not -path './.pytest_cache/*' | wc -l)"
	@echo "Lines of test code: $$(find tests/ -name '*.py' -exec cat {} \; | wc -l)"
	@echo "Test functions: $$(grep -r '^[[:space:]]*def test_' tests/ | wc -l)"