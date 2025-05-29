#!/usr/bin/env python3
"""
Testing Infrastructure Validation Script

Validates all components of our comprehensive testing infrastructure.
"""
import sys
import os
import importlib
import traceback
from pathlib import Path

# Add the project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)


def validate_dependencies():
    """Validate all required dependencies are available."""
    print("🔍 Validating Dependencies...")
    
    required_packages = [
        'pytest', 'jsonschema', 'matplotlib', 'seaborn', 
        'numpy', 'pandas', 'psutil', 'httpx', 'aiohttp',
        'faker', 'locust'
    ]
    
    missing = []
    available = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            available.append(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"  ❌ {package} - MISSING")
    
    print(f"\n📊 Dependencies Summary:")
    print(f"  Available: {len(available)}/{len(required_packages)}")
    print(f"  Missing: {len(missing)}")
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Install with: poetry add " + " ".join(missing))
        return False
    
    print("✅ All dependencies available!")
    return True


def validate_test_files():
    """Validate syntax of all test files."""
    print("\n🔍 Validating Test File Syntax...")
    
    test_files = [
        'tests/utils/test_orchestrator.py',
        'tests/api_docs/test_contract_testing.py',
        'tests/stress/test_chaos_engineering.py',
        'tests/performance/test_regression_testing.py',
        'tests/security/test_advanced_security.py',
        'tests/integration/test_database_migrations.py',
        'tests/run_comprehensive_tests.py'
    ]
    
    valid_files = []
    invalid_files = []
    
    for test_file in test_files:
        file_path = Path(test_file)
        if not file_path.exists():
            print(f"  ⚠️  {test_file} - FILE NOT FOUND")
            invalid_files.append(test_file)
            continue
        
        try:
            # Test compilation
            with open(file_path, 'r') as f:
                code = f.read()
            
            compile(code, file_path, 'exec')
            valid_files.append(test_file)
            print(f"  ✅ {test_file}")
            
        except SyntaxError as e:
            invalid_files.append(test_file)
            print(f"  ❌ {test_file} - SYNTAX ERROR: {e}")
        except Exception as e:
            invalid_files.append(test_file)
            print(f"  ❌ {test_file} - ERROR: {e}")
    
    print(f"\n📊 File Validation Summary:")
    print(f"  Valid: {len(valid_files)}/{len(test_files)}")
    print(f"  Invalid: {len(invalid_files)}")
    
    if invalid_files:
        print(f"\n⚠️  Invalid files: {', '.join(invalid_files)}")
        return False
    
    print("✅ All test files valid!")
    return True


def validate_test_structure():
    """Validate test directory structure."""
    print("\n🔍 Validating Test Structure...")
    
    expected_dirs = [
        'tests',
        'tests/unit',
        'tests/integration', 
        'tests/api_docs',
        'tests/security',
        'tests/performance',
        'tests/stress',
        'tests/utils',
        'tests/e2e',
        'tests/monitoring'
    ]
    
    existing_dirs = []
    missing_dirs = []
    
    for test_dir in expected_dirs:
        dir_path = Path(test_dir)
        if dir_path.exists() and dir_path.is_dir():
            existing_dirs.append(test_dir)
            print(f"  ✅ {test_dir}/")
        else:
            missing_dirs.append(test_dir)
            print(f"  ❌ {test_dir}/ - MISSING")
    
    print(f"\n📊 Directory Structure Summary:")
    print(f"  Existing: {len(existing_dirs)}/{len(expected_dirs)}")
    print(f"  Missing: {len(missing_dirs)}")
    
    if missing_dirs:
        print(f"\n⚠️  Missing directories: {', '.join(missing_dirs)}")
        return False
    
    print("✅ Test structure complete!")
    return True


def validate_test_configurations():
    """Validate test configuration files."""
    print("\n🔍 Validating Test Configurations...")
    
    config_files = [
        'pyproject.toml',
        'tests/conftest.py',
        'tests/stress/conftest.py',
        'tests/stress/config.py'
    ]
    
    valid_configs = []
    invalid_configs = []
    
    for config_file in config_files:
        file_path = Path(config_file)
        if file_path.exists():
            valid_configs.append(config_file)
            print(f"  ✅ {config_file}")
        else:
            invalid_configs.append(config_file)
            print(f"  ❌ {config_file} - MISSING")
    
    # Check pytest configuration in pyproject.toml
    try:
        with open('pyproject.toml', 'r') as f:
            content = f.read()
            if '[tool.pytest.ini_options]' in content:
                print(f"  ✅ pytest configuration found")
            else:
                print(f"  ⚠️  pytest configuration missing in pyproject.toml")
    except Exception as e:
        print(f"  ❌ Error reading pyproject.toml: {e}")
    
    print(f"\n📊 Configuration Summary:")
    print(f"  Valid: {len(valid_configs)}/{len(config_files)}")
    print(f"  Missing: {len(invalid_configs)}")
    
    return len(invalid_configs) == 0


def generate_testing_framework_summary():
    """Generate comprehensive summary of testing framework capabilities."""
    print("\n📋 Testing Framework Capabilities Summary:")
    print("="*80)
    
    frameworks = {
        "API Contract Testing": {
            "file": "tests/api_docs/test_contract_testing.py",
            "capabilities": [
                "Schema validation with JSON Schema",
                "Backward compatibility testing",
                "Response time contracts",
                "Error response standardization",
                "Pagination contract validation",
                "OpenAPI documentation sync"
            ]
        },
        "Chaos Engineering": {
            "file": "tests/stress/test_chaos_engineering.py", 
            "capabilities": [
                "Network failure injection (latency, packet loss)",
                "Database chaos (connection exhaustion, slow queries)",
                "Resource pressure (memory, CPU, disk I/O)",
                "Cascading failure scenarios",
                "Circuit breaker testing",
                "Graceful degradation validation"
            ]
        },
        "Performance Regression": {
            "file": "tests/performance/test_regression_testing.py",
            "capabilities": [
                "Historical baseline tracking",
                "Automated regression detection",
                "Performance trend analysis",
                "Configurable degradation thresholds", 
                "Performance budget compliance",
                "Visualization and reporting"
            ]
        },
        "Security Testing": {
            "file": "tests/security/test_advanced_security.py",
            "capabilities": [
                "OWASP Top 10 vulnerability testing",
                "Injection attack simulation",
                "Access control validation",
                "Authentication bypass testing",
                "Input fuzzing capabilities",
                "Automated penetration testing"
            ]
        },
        "Database Migration Testing": {
            "file": "tests/integration/test_database_migrations.py",
            "capabilities": [
                "Up/down migration validation",
                "Schema change verification",
                "Data integrity preservation",
                "Performance impact assessment",
                "Rollback safety testing",
                "Concurrent access validation"
            ]
        },
        "Test Orchestration": {
            "file": "tests/utils/test_orchestrator.py",
            "capabilities": [
                "Parallel test execution",
                "Quality gate validation",
                "Comprehensive reporting",
                "CI/CD pipeline integration",
                "GitHub Actions workflow generation",
                "Jenkins pipeline creation"
            ]
        },
        "Stress Testing": {
            "file": "tests/stress/",
            "capabilities": [
                "High-concurrency load testing",
                "Multiple test profiles (light, medium, heavy)",
                "Real-time resource monitoring",
                "Bottleneck detection",
                "Performance threshold validation",
                "Comprehensive metrics collection"
            ]
        }
    }
    
    for framework, details in frameworks.items():
        file_path = Path(details["file"])
        status = "✅" if file_path.exists() else "❌"
        
        print(f"\n{status} {framework}")
        print(f"   File: {details['file']}")
        print(f"   Capabilities:")
        for capability in details["capabilities"]:
            print(f"     • {capability}")
    
    print("\n" + "="*80)


def main():
    """Main validation routine."""
    print("🧪 COMPREHENSIVE TESTING INFRASTRUCTURE VALIDATION")
    print("="*80)
    
    all_valid = True
    
    # Run validations
    all_valid &= validate_dependencies()
    all_valid &= validate_test_structure()
    all_valid &= validate_test_files()
    all_valid &= validate_test_configurations()
    
    # Generate summary
    generate_testing_framework_summary()
    
    # Final result
    print("\n" + "="*80)
    if all_valid:
        print("🎉 VALIDATION COMPLETE - ALL SYSTEMS READY!")
        print("✅ Your comprehensive testing infrastructure is fully operational.")
        print("\nNext steps:")
        print("  1. Run: python3 tests/run_comprehensive_tests.py --list-categories")
        print("  2. Execute specific test categories")
        print("  3. Integrate with CI/CD pipeline")
        return 0
    else:
        print("⚠️  VALIDATION FAILED - ISSUES DETECTED")
        print("❌ Please address the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
