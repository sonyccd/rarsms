# RARSMS Frontend Testing Guide

## 🧪 Frontend Test Suite Overview

The RARSMS project includes comprehensive frontend unit tests for the PocketBase UI components. These tests ensure the reliability and maintainability of the web interface.

## 📁 Test Files

- **`test.html`** - Complete frontend test suite with visual results
- **Test Coverage Areas:**
  - Authentication logic and role-based access
  - Configuration management and validation
  - Callsign management CRUD operations
  - Frontend form validation
  - Message statistics calculations

## 🚀 Running Frontend Tests

### Browser Testing

1. **Start RARSMS services:**
   ```bash
   docker compose up --build
   ```

2. **Open test page:**
   ```
   http://localhost:8090/test.html
   ```

3. **Run tests:**
   - Click "Run All Tests" button
   - View real-time test results
   - Check overall success/failure status

### Test Categories

#### 🔐 Authentication Logic Tests
- Admin role identification
- Regular user role identification
- Missing role field handling
- Mock PocketBase authentication
- Invalid credential rejection

#### ⚙️ Configuration Management Tests
- APRS server configuration validation
- Discord integration settings
- Default configuration values
- Configuration object structure

#### 📞 Callsign Management Tests
- Callsign format validation (regex)
- Uppercase conversion
- Callsign object creation
- Valid/invalid callsign testing

#### 📝 Frontend Validation Tests
- Email format validation
- Password length requirements
- Numeric input validation
- Form field validation

#### 📊 Message Statistics Tests
- Message count calculations
- Protocol distribution analysis
- Date filtering for "today" stats
- Statistics object structure

## 🎯 Test Results

The test runner provides:
- ✅ **Pass/Fail Status** for each test
- 📊 **Success Rate Percentage**
- 🚨 **Error Details** for failed tests
- 📋 **Organized by Test Suite**

### Example Output
```
Tests: 25 | Passed: 24 | Failed: 1 | Success Rate: 96%
```

## 🛠️ Mock Testing Infrastructure

### Mock PocketBase
The tests use a mock PocketBase client that simulates:
- User authentication with different roles
- Database collection operations
- Error conditions and edge cases

### Test Users
- **admin@test.com** / **admin123** → Admin role
- **user@test.com** / **user123** → User role
- **invalid@test.com** / **wrong** → Authentication failure

## 📈 Quality Standards

- **Comprehensive Coverage**: All major UI components tested
- **Role-Based Testing**: Admin vs user access scenarios
- **Error Handling**: Invalid input and failure cases
- **Validation Testing**: Form inputs and data validation
- **Real-World Scenarios**: Actual use case simulation

## 🔧 Integration with Backend Tests

### Backend Testing
```bash
# Run Python backend tests
python3 run_tests.py

# Run specific test category
python3 run_tests.py aprs

# Run with coverage
python3 run_tests.py --coverage
```

### Full Test Suite
```bash
# Backend tests
make test

# Frontend tests
open http://localhost:8090/test.html

# PocketBase integration
./test_pocketbase.sh
```

## 🚨 Troubleshooting

### Common Issues

1. **PocketBase Not Running**
   ```bash
   docker compose up -d pocketbase
   ```

2. **Test Page Not Loading**
   - Check if port 8090 is accessible
   - Verify PocketBase container is running

3. **Authentication Tests Failing**
   - Ensure mock users are properly configured
   - Check role field implementation

### Debug Information

The test suite includes detailed error messages and can be inspected using browser developer tools for additional debugging.

## 🎉 Contributing Tests

When adding new frontend features:

1. **Add corresponding tests** to `test.html`
2. **Follow naming convention**: `it('should do something', ...)`
3. **Include both success and failure cases**
4. **Update this documentation** with new test categories
5. **Ensure >95% pass rate** before merging

### Test Template
```javascript
describe('New Feature Tests', () => {
    it('should handle valid input correctly', () => {
        const result = newFeature('valid-input');
        expect(result).toBe('expected-output');
    });

    it('should handle invalid input gracefully', () => {
        expect(() => newFeature(null)).toThrow();
    });
});
```

## 📝 Test Maintenance

- **Run tests after each UI change**
- **Update tests when adding features**
- **Keep mock data realistic**
- **Maintain comprehensive error testing**

The frontend test suite ensures the RARSMS web interface remains reliable and user-friendly across all supported features and use cases.