#!/usr/bin/env python3

import subprocess
import sys
import os

def run_tests():
    """Run the test suite with appropriate configuration"""

    # Ensure we're in the right directory
    if not os.path.exists('tests'):
        print("Error: tests directory not found. Run this script from the project root.")
        return 1

    # Basic test run
    print("🧪 Running RARSMS test suite...")
    print("=" * 50)

    try:
        # Run pytest with coverage if available
        cmd = [sys.executable, '-m', 'pytest']

        # Add coverage options if pytest-cov is available
        try:
            import pytest_cov
            cmd.extend(['--cov=protocols', '--cov=.', '--cov-report=term-missing'])
            print("📊 Running with coverage reporting")
        except ImportError:
            print("ℹ️  Running without coverage (install pytest-cov for coverage reports)")

        # Add test discovery options
        cmd.extend([
            'tests/',
            '-v',
            '--tb=short'
        ])

        print(f"Command: {' '.join(cmd)}")
        print("-" * 50)

        result = subprocess.run(cmd, cwd=os.getcwd())

        print("-" * 50)
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")

        return result.returncode

    except FileNotFoundError:
        print("❌ pytest not found. Install requirements:")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test(test_pattern):
    """Run specific tests matching a pattern"""
    cmd = [sys.executable, '-m', 'pytest', '-v', '-k', test_pattern, 'tests/']

    print(f"🔍 Running tests matching: {test_pattern}")
    print("=" * 50)

    result = subprocess.run(cmd)
    return result.returncode

def show_help():
    """Show help information"""
    print("RARSMS Test Runner")
    print("=" * 30)
    print("Usage:")
    print("  python run_tests.py              # Run all tests")
    print("  python run_tests.py config       # Run configuration tests only")
    print("  python run_tests.py discord      # Run Discord tests only")
    print("  python run_tests.py aprs         # Run APRS tests only")
    print("  python run_tests.py manager      # Run protocol manager tests only")
    print("  python run_tests.py --help       # Show this help")
    print()
    print("Test Categories:")
    print("  config    - Configuration loading and validation")
    print("  discord   - Discord bot protocol functionality")
    print("  aprs      - APRS protocol parsing and routing")
    print("  manager   - Protocol manager and message routing")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ['--help', '-h', 'help']:
            show_help()
            sys.exit(0)
        elif arg in ['config', 'configuration']:
            sys.exit(run_specific_test('config'))
        elif arg in ['discord', 'discord_bot']:
            sys.exit(run_specific_test('discord'))
        elif arg in ['aprs']:
            sys.exit(run_specific_test('aprs'))
        elif arg in ['manager', 'protocol_manager']:
            sys.exit(run_specific_test('manager'))
        else:
            print(f"Unknown test category: {arg}")
            print("Run 'python run_tests.py --help' for available options")
            sys.exit(1)
    else:
        sys.exit(run_tests())