#!/usr/bin/env python3
"""
Test Status Checker for RARSMS
Provides a quick overview of test coverage and status
"""

import os
import sys
import glob
import subprocess
from pathlib import Path

def count_files(pattern):
    """Count files matching pattern"""
    return len(glob.glob(pattern))

def get_test_stats():
    """Get comprehensive test statistics"""
    stats = {}

    # Count source files
    stats['source_files'] = count_files('*.py') + count_files('protocols/*.py')

    # Count test files
    stats['test_files'] = count_files('tests/test_*.py')

    # Count individual test functions
    test_functions = 0
    test_classes = 0

    for test_file in glob.glob('tests/test_*.py'):
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                test_functions += content.count('def test_')
                test_classes += content.count('class Test')
        except Exception:
            continue

    stats['test_functions'] = test_functions
    stats['test_classes'] = test_classes

    return stats

def check_dependencies():
    """Check if required test dependencies are installed"""
    deps = {
        'pytest': False,
        'pytest-asyncio': False,
        'pytest-cov': False,
        'coverage': False
    }

    for dep in deps:
        try:
            __import__(dep.replace('-', '_'))
            deps[dep] = True
        except ImportError:
            try:
                # Try alternate import names
                if dep == 'pytest-asyncio':
                    __import__('pytest_asyncio')
                    deps[dep] = True
                elif dep == 'pytest-cov':
                    __import__('pytest_cov')
                    deps[dep] = True
            except ImportError:
                pass

    return deps

def check_test_files():
    """Check individual test files for basic structure"""
    test_files = {}

    for test_file in glob.glob('tests/test_*.py'):
        filename = os.path.basename(test_file)
        test_files[filename] = {
            'exists': True,
            'size': os.path.getsize(test_file),
            'functions': 0,
            'classes': 0,
            'imports_ok': True
        }

        try:
            with open(test_file, 'r') as f:
                content = f.read()
                test_files[filename]['functions'] = content.count('def test_')
                test_files[filename]['classes'] = content.count('class Test')

            # Test if file can be imported (basic syntax check)
            try:
                import ast
                ast.parse(content)
            except SyntaxError:
                test_files[filename]['imports_ok'] = False

        except Exception as e:
            test_files[filename]['error'] = str(e)

    return test_files

def run_quick_test():
    """Run a quick test to see if pytest works"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', '--collect-only', '-q', 'tests/'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def print_status():
    """Print comprehensive test status"""
    print("🧪 RARSMS Test Status")
    print("=" * 50)

    # Basic stats
    stats = get_test_stats()
    print(f"📊 Test Statistics:")
    print(f"   • Source files: {stats['source_files']}")
    print(f"   • Test files: {stats['test_files']}")
    print(f"   • Test classes: {stats['test_classes']}")
    print(f"   • Test functions: {stats['test_functions']}")
    print()

    # Dependencies
    deps = check_dependencies()
    print("📦 Dependencies:")
    for dep, installed in deps.items():
        status = "✅" if installed else "❌"
        print(f"   • {dep}: {status}")
    print()

    # Test file details
    test_files = check_test_files()
    print("📋 Test Files:")
    for filename, info in test_files.items():
        status = "✅" if info['imports_ok'] else "❌"
        functions = info['functions']
        classes = info['classes']
        size_kb = info['size'] // 1024
        print(f"   • {filename}: {status} ({functions} tests, {classes} classes, {size_kb}KB)")
    print()

    # Quick test run
    if deps['pytest']:
        print("⚡ Quick Test Check:")
        test_result = run_quick_test()
        if test_result['success']:
            print("   ✅ Test discovery successful")
            # Count discovered tests
            if 'collected' in test_result['output']:
                try:
                    collected_line = [line for line in test_result['output'].split('\n') if 'collected' in line][0]
                    print(f"   📊 {collected_line.strip()}")
                except:
                    pass
        else:
            print("   ❌ Test discovery failed")
            if test_result.get('error'):
                print(f"   Error: {test_result['error'][:200]}...")
    else:
        print("⚠️  pytest not available - cannot run quick test check")

    print()

    # Configuration files
    config_files = {
        'pytest.ini': os.path.exists('pytest.ini'),
        'requirements.txt': os.path.exists('requirements.txt'),
        'config.yaml': os.path.exists('config.yaml'),
        'config.example.yaml': os.path.exists('config.example.yaml'),
        'callsigns.txt': os.path.exists('callsigns.txt'),
    }

    print("⚙️  Configuration Files:")
    for filename, exists in config_files.items():
        status = "✅" if exists else "❌"
        print(f"   • {filename}: {status}")

    print()

    # Summary
    all_deps_ok = all(deps[dep] for dep in ['pytest', 'pytest-asyncio'])
    all_tests_ok = all(info['imports_ok'] for info in test_files.values())
    has_tests = stats['test_functions'] > 0

    if all_deps_ok and all_tests_ok and has_tests:
        print("🎉 Test suite is ready!")
        print("   Run: python -m pytest tests/ -v")
        print("   Run: python run_tests.py")
    else:
        print("⚠️  Issues found:")
        if not all_deps_ok:
            print("   - Missing test dependencies (run: pip install -r requirements.txt)")
        if not all_tests_ok:
            print("   - Some test files have syntax errors")
        if not has_tests:
            print("   - No test functions found")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("RARSMS Test Status Checker")
            print("Usage:")
            print("  python test_status.py           # Show full status")
            print("  python test_status.py --help    # Show this help")
            return

    print_status()

if __name__ == '__main__':
    main()