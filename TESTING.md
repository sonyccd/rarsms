# RARSMS Testing Guide

This document provides comprehensive information about the testing infrastructure for the RARSMS project.

## 🧪 Test Suite Overview

The RARSMS project includes a comprehensive test suite with **7 test modules** covering all major functionality:

| Test Module | Coverage | Test Count | Purpose |
|-------------|----------|------------|---------|
| `test_aprs.py` | APRS protocol, deduplication, SSID handling | 25+ tests | Core APRS functionality |
| `test_discord_bot.py` | Discord integration, formatting, QRZ links | 20+ tests | Discord bot protocol |
| `test_base.py` | Core message/protocol abstractions | 30+ tests | Foundation classes |
| `test_interchange.py` | Universal message system | 25+ tests | Message adaptation |
| `test_config.py` | Configuration management | Tests | Config loading/validation |
| `test_protocol_manager.py` | Protocol coordination | Tests | Message routing |
| `test_integration.py` | End-to-end functionality | Tests | Integration scenarios |

## 🚀 Running Tests

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
make test

# Or use pytest directly
python -m pytest tests/ -v
```

### Test Categories

Run specific test categories using the enhanced test runner:

```bash
python run_tests.py aprs         # APRS protocol tests
python run_tests.py discord      # Discord bot tests
python run_tests.py base         # Base protocol tests
python run_tests.py interchange  # Universal message tests
python run_tests.py config       # Configuration tests
python run_tests.py manager      # Protocol manager tests
python run_tests.py integration  # Integration tests
```

### Coverage Reporting

```bash
# Run tests with coverage
make test-coverage

# Or manually
python -m pytest tests/ --cov=protocols --cov=main --cov-report=html --cov-report=term-missing
```

## 🔧 Development Tools

### Makefile Commands

The project includes a comprehensive Makefile with useful commands:

```bash
make help          # Show all available commands
make test          # Run all tests
make test-verbose  # Run tests with detailed output
make test-coverage # Run tests with coverage reporting
make setup         # Setup development environment
make clean         # Clean generated files
make check-status  # Check test environment status
make docker-test   # Test Docker build
```

### Test Status Checker

Check your testing environment:

```bash
python test_status.py
```

This will show:
- Test file statistics
- Dependency status
- Configuration file status
- Quick test validation

## 🎯 GitHub Actions

The project includes three GitHub workflows:

### 1. **CI Workflow** (`.github/workflows/ci.yml`)
- Runs on every push/PR to main
- Tests against Python 3.9, 3.10, 3.11, 3.12
- Includes Docker build testing
- Basic test execution

### 2. **Comprehensive Tests** (`.github/workflows/tests.yml`)
- Full test suite with multiple Python versions
- Code coverage reporting with Codecov integration
- Security scanning with Bandit
- Code quality checks (Black, isort, mypy)
- Integration testing
- Artifact collection on failures

### 3. **Coverage Workflow** (`.github/workflows/coverage.yml`)
- Dedicated coverage reporting
- Coverage comments on PRs
- HTML coverage report artifacts
- Fail builds below 80% coverage

## 📊 Test Coverage

### Current Coverage Areas

✅ **APRS Protocol**
- Message parsing and routing
- Deduplication system
- SSID handling and callsign processing
- Geographic filtering
- Connection management

✅ **Discord Integration**
- Bot protocol functionality
- Message formatting (3-line layout)
- QRZ.com link integration
- Content cleanup and sanitization
- Reply system and message tracking

✅ **Core Architecture**
- Base protocol abstractions
- Message routing and validation
- Protocol capabilities system
- Universal message adaptation
- Content prioritization

✅ **Configuration System**
- YAML and environment variable loading
- Validation and error handling
- Default value management

## 🏗️ Test Architecture

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_aprs.py            # APRS protocol tests
├── test_discord_bot.py     # Discord bot tests
├── test_base.py            # Base protocol/message tests
├── test_interchange.py     # Universal message system tests
├── test_config.py          # Configuration tests
├── test_protocol_manager.py # Protocol manager tests
└── test_integration.py     # End-to-end integration tests
```

### Key Testing Patterns

- **Fixtures**: Reusable test components in `conftest.py`
- **Async Testing**: Full support for async protocols with `pytest-asyncio`
- **Mocking**: Extensive use of mocks for external dependencies
- **Parameterized Tests**: Multiple test cases with different inputs
- **Edge Case Coverage**: Comprehensive error condition testing

### Test Naming Convention

- Test files: `test_<module>.py`
- Test classes: `TestClassName`
- Test functions: `test_specific_functionality`
- Test markers: `@pytest.mark.asyncio` for async tests

## 🔍 What's Tested

### New Features (Recently Added)

✅ **Message Deduplication**
- Configurable timeout windows
- Content normalization
- Cache management
- Duplicate detection accuracy

✅ **Discord Formatting Improvements**
- 3-line message layout
- QRZ.com clickable links
- Link preview suppression
- Content cleanup (removing debug info)
- Timestamp formatting

✅ **SSID Processing**
- Callsign uppercase conversion
- SSID preservation (-1 through -15)
- Portable/mobile indicators (/M, /P)
- Case normalization

✅ **Universal Message System**
- Content block prioritization
- Protocol-specific adaptations
- Smart text truncation
- Fallback handling

## 🚨 Quality Standards

- **Minimum Coverage**: 80% (enforced in CI)
- **All Tests Must Pass**: No failing tests in main branch
- **Async Support**: Full async/await pattern testing
- **Error Handling**: Comprehensive error condition coverage
- **Documentation**: All test functions have descriptive docstrings

## 🎛️ Configuration for Testing

### Required Files
- `config.yaml` (copy from `config.example.yaml`)
- `callsigns.txt` (test callsigns)
- `pytest.ini` (pytest configuration)

### Test Environment Variables
Tests use safe defaults and don't require real credentials.

### Dependencies
All testing dependencies are included in `requirements.txt`:
- `pytest==7.4.4`
- `pytest-asyncio==0.23.2`

## 📈 Continuous Integration

### Branch Protection
- All tests must pass before merging
- Coverage must meet minimum thresholds
- Code quality checks must pass

### Automated Testing
- Every commit triggers test runs
- Multiple Python versions tested
- Docker builds validated
- Security scans performed

### Coverage Reporting
- Codecov integration for coverage tracking
- Coverage reports on pull requests
- HTML coverage reports archived as artifacts

## 🛠️ Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure dependencies are installed
pip install -r requirements.txt
```

**Config File Missing**
```bash
# Copy example config
cp config.example.yaml config.yaml
```

**Permission Errors**
```bash
# Fix file permissions
chmod +x run_tests.py test_status.py
```

### Getting Help

1. Check test status: `python test_status.py`
2. Run specific category: `python run_tests.py <category>`
3. Check setup: `make check-status`
4. Clean and retry: `make clean && make setup`

## 🎉 Contributing Tests

When adding new features:

1. **Write tests first** (TDD approach recommended)
2. **Achieve >80% coverage** for new code
3. **Include edge cases** and error conditions
4. **Use descriptive test names** that explain what's being tested
5. **Add docstrings** to test functions
6. **Test both success and failure paths**

### Test Template

```python
def test_new_feature_success(self, fixture_name):
    """Test new feature works correctly with valid input"""
    # Arrange
    input_data = "test_input"

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
    assert some_side_effect_occurred()

def test_new_feature_handles_error(self, fixture_name):
    """Test new feature handles invalid input gracefully"""
    # Arrange
    invalid_input = None

    # Act & Assert
    with pytest.raises(ValueError, match="Expected error message"):
        function_under_test(invalid_input)
```

The RARSMS test suite provides comprehensive coverage and confidence in the codebase's reliability and maintainability.