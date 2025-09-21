#!/bin/bash

# RARSMS Validation Script
# Quick validation that all files are in place

echo "🔍 RARSMS Validation"
echo "===================="

errors=0

# Check essential files
echo ""
echo "📁 Checking essential files..."

files=(
    "docker-compose.yml"
    ".env.example"
    "config/config.example.yaml"
    "services/aprs-connector/go.mod"
    "services/aprs-connector/go.sum"
    "services/aprs-connector/Dockerfile"
    "services/discord-bot/requirements.txt"
    "services/discord-bot/Dockerfile"
    "services/web-dashboard/Dockerfile"
)

for file in "${files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        ((errors++))
    fi
done

# Check directories
echo ""
echo "📂 Checking directories..."

dirs=(
    "services/aprs-connector/src"
    "services/discord-bot/src"
    "services/web-dashboard/pb_hooks"
    "services/web-dashboard/pb_migrations"
    "services/web-dashboard/pb_public"
    "config"
    "scripts"
)

for dir in "${dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ - MISSING"
        ((errors++))
    fi
done

# Check key source files
echo ""
echo "🔧 Checking key source files..."

source_files=(
    "services/aprs-connector/src/main.go"
    "services/discord-bot/src/main.py"
    "services/web-dashboard/pb_hooks/main.pb.js"
)

for file in "${source_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        ((errors++))
    fi
done

# Check documentation
echo ""
echo "📚 Checking documentation..."

docs=(
    "README.md"
    "QUICKSTART.md"
    "README-SYNOLOGY.md"
    "README-DOCKER-ONLY.md"
    "README-DOCKER-PERMISSIONS.md"
    "CLAUDE.md"
)

for doc in "${docs[@]}"; do
    if [[ -f "$doc" ]]; then
        echo "✅ $doc"
    else
        echo "❌ $doc - MISSING"
        ((errors++))
    fi
done

# Check Docker Compose syntax
echo ""
echo "🐳 Validating Docker Compose..."

if command -v docker &> /dev/null; then
    if docker compose config &> /dev/null; then
        echo "✅ docker-compose.yml syntax valid"
    else
        echo "❌ docker-compose.yml syntax error"
        ((errors++))
    fi
else
    echo "⚠️  Docker not available, skipping syntax check"
fi

# Check Go module
echo ""
echo "🔧 Checking Go module..."

cd services/aprs-connector 2>/dev/null
if [[ -f "go.mod" && -f "go.sum" ]]; then
    if command -v go &> /dev/null; then
        if go mod verify &> /dev/null; then
            echo "✅ Go module valid"
        else
            echo "❌ Go module verification failed"
            ((errors++))
        fi
    else
        echo "⚠️  Go not available, skipping module check"
    fi
else
    echo "❌ Go module files missing"
    ((errors++))
fi

cd - > /dev/null

# Summary
echo ""
echo "📊 Validation Summary"
echo "===================="

if [[ $errors -eq 0 ]]; then
    echo "🎉 All checks passed! RARSMS is ready for deployment."
    echo ""
    echo "Next steps:"
    echo "1. Run: docker compose --profile setup run --rm setup"
    echo "2. Edit .env with your configuration"
    echo "3. Run: docker compose up -d"
    exit 0
else
    echo "❌ $errors error(s) found. Please fix these issues before deployment."
    exit 1
fi