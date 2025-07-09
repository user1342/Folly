#!/usr/bin/env python3
"""
Test runner script for Folly testing suite.

This script provides a convenient way to run different types of tests
with proper configuration and reporting.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", coverage=False, verbose=False, markers=None):
    """Run tests with specified configuration."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directories based on type
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "system":
        cmd.append("tests/system/")
    elif test_type == "integration":
        cmd.append("tests/system/test_integration.py")
    elif test_type == "all":
        cmd.append("tests/")
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=Folly", "--cov-report=html", "--cov-report=term"])
    
    if markers:
        cmd.extend(["-m", markers])
    
    # Add common options
    cmd.extend(["--tb=short", "--strict-markers"])
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run Folly tests")
    
    parser.add_argument(
        "--type", "-t",
        choices=["unit", "system", "integration", "all"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--markers", "-m",
        help="Run tests with specific markers (e.g., 'not slow')"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests (excludes slow system tests)"
    )
    
    args = parser.parse_args()
    
    # Handle quick flag
    if args.quick:
        args.markers = "not slow"
        args.type = "unit"  # Only run unit tests for quick mode
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        markers=args.markers
    )
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())