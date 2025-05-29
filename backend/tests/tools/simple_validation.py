#!/usr/bin/env python3
"""
Simple Testing Infrastructure Validation

Quick validation script to check the testing setup.
"""

import os
import sys
from pathlib import Path

# Add the project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

def check_files():
    """Check if all test files exist."""
    print("🔍 Checking test files...")
    
    test_files = [
        "tests/api_docs/test_contract_testing.py",
        "tests/stress/test_chaos_engineering.py", 
        "tests/performance/test_regression_testing.py",
        "tests/security/test_advanced_security.py",
        "tests/integration/test_database_migrations.py",
        "tests/utils/test_orchestrator.py",
        "tests/run_comprehensive_tests.py"
    ]
    
    all_exist = True
    for file_path in test_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            all_exist = False
    
    return all_exist

def check_dependencies():
    """Check if required packages are available."""
    print("\n🔍 Checking dependencies...")
    
    dependencies = [
        "pytest", "jsonschema", "matplotlib", "seaborn", 
        "numpy", "pandas", "psutil", "httpx", "aiohttp", 
        "faker", "locust"
    ]
    
    available = []
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
            available.append(dep)
        except ImportError:
            print(f"  ❌ {dep}")
            missing.append(dep)
    
    return len(missing) == 0, available, missing

def generate_sample_ci_config():
    """Generate a sample CI configuration."""
    print("\n🔧 Generating sample CI/CD configuration...")
    
    github_workflow = """name: Comprehensive Testing Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  comprehensive-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.12'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run API Contract Tests
      run: poetry run pytest tests/api_docs/ -v
    
    - name: Run Security Tests
      run: poetry run pytest tests/security/ -v
    
    - name: Run Performance Regression Tests
      run: poetry run pytest tests/performance/ -v
    
    - name: Run Integration Tests
      run: poetry run pytest tests/integration/ -v
    
    - name: Run Stress Tests (Light)
      run: poetry run pytest tests/stress/ -m "not heavy" -v
"""
    
    # Create .github/workflows directory
    workflows_dir = Path(".github/workflows")
    workflows_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the workflow file
    workflow_file = workflows_dir / "comprehensive-tests.yml"
    with open(workflow_file, "w") as f:
        f.write(github_workflow)
    
    print(f"  ✅ GitHub Actions workflow saved to {workflow_file}")
    return True

def main():
    """Main validation function."""
    print("🧪 SIMPLE TESTING INFRASTRUCTURE VALIDATION")
    print("=" * 60)
    
    # Check files
    files_ok = check_files()
    
    # Check dependencies
    deps_ok, available, missing = check_dependencies()
    
    # Generate CI config
    ci_ok = generate_sample_ci_config()
    
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 30)
    print(f"Test Files: {'✅ OK' if files_ok else '❌ MISSING'}")
    print(f"Dependencies: {'✅ OK' if deps_ok else '❌ MISSING'}")
    print(f"CI/CD Config: {'✅ OK' if ci_ok else '❌ FAILED'}")
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: poetry add " + " ".join(missing))
    
    print("\n🎯 TEST CATEGORIES AVAILABLE:")
    categories = [
        "API Contract Testing",
        "Chaos Engineering", 
        "Performance Regression",
        "Security Testing",
        "Database Migrations",
        "Stress Testing",
        "Test Orchestration"
    ]
    
    for category in categories:
        print(f"  ✅ {category}")
    
    if files_ok and deps_ok:
        print("\n🎉 VALIDATION SUCCESSFUL!")
        print("Your comprehensive testing infrastructure is ready!")
        print("\nNext steps:")
        print("  1. Run individual test categories")
        print("  2. Integrate with CI/CD pipeline")
        print("  3. Configure test thresholds")
        return 0
    else:
        print("\n⚠️  VALIDATION ISSUES DETECTED")
        print("Please address the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
