#!/usr/bin/env python3
"""Quick test script to validate the testing infrastructure."""

import sys
import os
from pathlib import Path

print("🧪 QUICK INFRASTRUCTURE TEST")
print("=" * 50)

# Test imports
try:
    import pytest
    print("✅ pytest imported successfully")
except ImportError as e:
    print(f"❌ pytest import failed: {e}")

try:
    import jsonschema
    print("✅ jsonschema imported successfully")
except ImportError as e:
    print(f"❌ jsonschema import failed: {e}")

try:
    import matplotlib
    print("✅ matplotlib imported successfully")
except ImportError as e:
    print(f"❌ matplotlib import failed: {e}")

# Test directory structure
print("\n📁 Directory Structure:")
test_dirs = [
    'tests/unit', 'tests/integration', 'tests/api_docs',
    'tests/security', 'tests/performance', 'tests/stress',
    'tests/e2e', 'tests/monitoring', 'tests/tools',
    'tests/config', 'tests/fixtures', 'tests/helpers'
]

for test_dir in test_dirs:
    if Path(test_dir).exists():
        print(f"  ✅ {test_dir}")
    else:
        print(f"  ❌ {test_dir}")

# Test file validation
print("\n📄 Test Files:")
test_files = [
    'tests/test_manager.py',
    'tests/config/test_config.py',
    'tests/tools/validate_testing_infrastructure.py',
    'tests/tools/simple_validation.py'
]

for test_file in test_files:
    if Path(test_file).exists():
        print(f"  ✅ {test_file}")
    else:
        print(f"  ❌ {test_file}")

print("\n🎉 Quick test completed!")
