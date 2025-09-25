#!/bin/bash

# RARSMS Test Validation Script
# Validates that both frontend and backend test infrastructure is ready

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 RARSMS Test Infrastructure Validation${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check frontend tests
echo -e "${BLUE}📱 Frontend Tests${NC}"
if [ -f "pocketbase/pb_public/test.html" ]; then
    echo -e "${GREEN}✅ Frontend test suite found${NC}"

    # Count test cases in the frontend
    test_count=$(grep -c "it('.*'" pocketbase/pb_public/test.html || echo "0")
    echo -e "${GREEN}   📋 ${test_count} frontend test cases detected${NC}"
else
    echo -e "${RED}❌ Frontend test suite not found${NC}"
fi

# Check backend tests
echo -e "${BLUE}🐍 Backend Tests${NC}"
if [ -d "tests" ]; then
    echo -e "${GREEN}✅ Backend test directory found${NC}"

    # Count test files
    test_files=$(find tests/ -name "test_*.py" | wc -l)
    echo -e "${GREEN}   📋 ${test_files} backend test files found${NC}"

    # List test files
    echo -e "${BLUE}   Backend test modules:${NC}"
    find tests/ -name "test_*.py" -exec basename {} \; | sed 's/^/     - /'
else
    echo -e "${RED}❌ Backend test directory not found${NC}"
fi

# Check test runner
echo -e "${BLUE}🚀 Test Runners${NC}"
if [ -f "run_tests.py" ]; then
    echo -e "${GREEN}✅ Python test runner found${NC}"
else
    echo -e "${YELLOW}⚠️  Python test runner not found${NC}"
fi

# Check requirements
echo -e "${BLUE}📦 Dependencies${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✅ Requirements file found${NC}"

    # Check for test dependencies
    if grep -q pytest requirements.txt; then
        echo -e "${GREEN}   ✅ pytest dependency found${NC}"
    else
        echo -e "${RED}   ❌ pytest dependency missing${NC}"
    fi
else
    echo -e "${RED}❌ Requirements file not found${NC}"
fi

# Check configuration files
echo -e "${BLUE}⚙️  Configuration${NC}"
if [ -f "config.yaml" ] || [ -f "config.example.yaml" ]; then
    echo -e "${GREEN}✅ Configuration file(s) found${NC}"
else
    echo -e "${RED}❌ No configuration files found${NC}"
fi

# Check Docker setup
echo -e "${BLUE}🐳 Docker Integration${NC}"
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✅ Docker Compose configuration found${NC}"
else
    echo -e "${RED}❌ Docker Compose configuration not found${NC}"
fi

# Check PocketBase test infrastructure
echo -e "${BLUE}💾 PocketBase Tests${NC}"
if [ -f "test_pocketbase.sh" ]; then
    echo -e "${GREEN}✅ PocketBase test script found${NC}"
else
    echo -e "${YELLOW}⚠️  PocketBase test script not found${NC}"
fi

if [ -f "pocketbase_collections.json" ]; then
    echo -e "${GREEN}✅ PocketBase collections schema found${NC}"
else
    echo -e "${RED}❌ PocketBase collections schema not found${NC}"
fi

echo ""
echo -e "${BLUE}📊 Test Infrastructure Summary${NC}"
echo -e "${BLUE}==============================${NC}"

# Calculate score
score=0
total=8

[ -f "pocketbase/pb_public/test.html" ] && score=$((score + 1))
[ -d "tests" ] && score=$((score + 1))
[ -f "run_tests.py" ] && score=$((score + 1))
[ -f "requirements.txt" ] && score=$((score + 1))
[ -f "config.yaml" ] || [ -f "config.example.yaml" ] && score=$((score + 1))
[ -f "docker-compose.yml" ] && score=$((score + 1))
[ -f "test_pocketbase.sh" ] && score=$((score + 1))
[ -f "pocketbase_collections.json" ] && score=$((score + 1))

percentage=$((score * 100 / total))

if [ $percentage -ge 90 ]; then
    echo -e "${GREEN}🎉 Excellent! Test infrastructure is ${percentage}% complete (${score}/${total})${NC}"
elif [ $percentage -ge 70 ]; then
    echo -e "${YELLOW}👍 Good! Test infrastructure is ${percentage}% complete (${score}/${total})${NC}"
else
    echo -e "${RED}⚠️  Test infrastructure needs work: ${percentage}% complete (${score}/${total})${NC}"
fi

echo ""
echo -e "${BLUE}🚀 How to Run Tests${NC}"
echo -e "${BLUE}==================${NC}"
echo -e "${GREEN}Frontend Tests:${NC}"
echo -e "  1. Start services: ${YELLOW}docker compose up -d${NC}"
echo -e "  2. Open browser: ${YELLOW}http://localhost:8090/test.html${NC}"
echo -e "  3. Click 'Run All Tests'"
echo ""
echo -e "${GREEN}Backend Tests:${NC}"
echo -e "  1. Install dependencies: ${YELLOW}pip install -r requirements.txt${NC}"
echo -e "  2. Copy config: ${YELLOW}cp config.example.yaml config.yaml${NC}"
echo -e "  3. Run tests: ${YELLOW}python3 run_tests.py${NC}"
echo ""
echo -e "${GREEN}Integration Tests:${NC}"
echo -e "  1. Start PocketBase: ${YELLOW}docker compose up -d pocketbase${NC}"
echo -e "  2. Run PocketBase tests: ${YELLOW}./test_pocketbase.sh${NC}"

exit 0