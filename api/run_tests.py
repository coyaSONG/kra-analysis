#!/usr/bin/env python3
"""
Test runner script for KRA API v2

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit              # Run only unit tests
    python run_tests.py integration       # Run only integration tests
    python run_tests.py coverage          # Run with coverage report
    python run_tests.py specific test_auth # Run specific test file
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd: list) -> int:
    """Run a command and return exit code"""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    # Ensure we're in the api directory where pytest.ini is located
    api_dir = Path(__file__).parent
    result = subprocess.run(cmd, cwd=api_dir)
    print("-" * 60)
    return result.returncode


def main():
    """Main test runner"""
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Base pytest command
    pytest_cmd = ["python3", "-m", "pytest"]
    
    # Handle different test modes
    if not args:
        # Run all tests with coverage
        pytest_cmd.extend([
            "-v",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=xml"
        ])
    elif "unit" in args:
        # Run only unit tests
        pytest_cmd.extend(["-v", "-m", "unit"])
    elif "integration" in args:
        # Run only integration tests
        pytest_cmd.extend(["-v", "-m", "integration"])
    elif "e2e" in args:
        # Run only e2e tests
        pytest_cmd.extend(["-v", "-m", "e2e"])
    elif "coverage" in args:
        # Run with detailed coverage
        pytest_cmd.extend([
            "-v",
            "--cov=.",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html",
            "--cov-report=xml",
            "--cov-fail-under=80"
        ])
    elif "smoke" in args:
        # Run smoke tests
        pytest_cmd.extend(["-v", "-m", "smoke"])
    elif "specific" in args and len(args) > 1:
        # Run specific test file
        test_file = args[1]
        pytest_cmd.extend(["-v", f"tests/**/*{test_file}*"])
    else:
        # Pass through any other arguments
        pytest_cmd.extend(args)
    
    # Add color output if terminal supports it
    if sys.stdout.isatty():
        pytest_cmd.append("--color=yes")
    
    # Set environment variables for testing
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
    
    # Run the tests
    print("🧪 Running KRA API v2 Tests")
    print("=" * 60)
    
    exit_code = run_command(pytest_cmd)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
        
        # Show coverage report location if generated
        if "--cov" in " ".join(pytest_cmd):
            print("\n📊 Coverage Reports:")
            print("  - Terminal: See above")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())