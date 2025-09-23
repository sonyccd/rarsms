#!/bin/bash

# Clean Repository for GitHub Pages
# This script removes problematic directories and files that cause Jekyll build issues

echo "🧹 Cleaning repository for GitHub Pages deployment..."

# Remove Python virtual environments
echo "Removing Python virtual environments..."
rm -rf test_env/ venv/ env/ .venv/ .test_env/ 2>/dev/null || true

# Remove Python cache and bytecode
echo "Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*.pyd" -delete 2>/dev/null || true

# Remove broken symlinks
echo "Removing broken symlinks..."
find . -xtype l -delete 2>/dev/null || true

# Remove build artifacts
echo "Removing build artifacts..."
rm -rf build/ dist/ .eggs/ *.egg-info/ 2>/dev/null || true

# Remove test artifacts
echo "Removing test artifacts..."
rm -rf .pytest_cache/ htmlcov/ .coverage coverage.xml 2>/dev/null || true

# Remove IDE files
echo "Removing IDE files..."
rm -rf .vscode/ .idea/ 2>/dev/null || true

# Remove log files
echo "Removing log files..."
find . -name "*.log" -delete 2>/dev/null || true

# Remove temporary files
echo "Removing temporary files..."
find . -name "*~" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true

# List what's left in the repository
echo ""
echo "📁 Repository contents after cleanup:"
ls -la

echo ""
echo "📄 Files that will be processed by Jekyll:"
find . -maxdepth 1 -name "*.md" -o -name "*.html" -o -name "_config.yml" | sort

echo ""
echo "✅ Repository cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Commit these changes: git add -A && git commit -m 'Clean repository for Pages'"
echo "2. Push to GitHub: git push"
echo "3. Check GitHub Pages deployment in the Actions tab"