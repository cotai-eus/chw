#!/usr/bin/env python3
"""
Test Orchestrator Demo

Demonstrates the capabilities of the comprehensive testing infrastructure.
"""

import os
import sys
from pathlib import Path

# Add the project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

def test_orchestrator():
    """Test the orchestrator functionality."""
    try:
        from tests.utils.test_orchestrator import TestOrchestrator
        print("✅ TestOrchestrator imported successfully")
        
        # Create orchestrator instance
        orchestrator = TestOrchestrator()
        print("✅ TestOrchestrator instantiated")
        
        # Generate CI/CD configs
        print("\n🔧 Generating CI/CD configurations...")
        
        github_config = orchestrator.generate_github_actions_config()
        print("✅ GitHub Actions config generated")
        
        jenkins_config = orchestrator.generate_jenkins_pipeline()
        print("✅ Jenkins pipeline config generated")
        
        # Save configurations
        github_dir = Path(".github/workflows")
        github_dir.mkdir(parents=True, exist_ok=True)
        
        with open(github_dir / "comprehensive-tests.yml", "w") as f:
            f.write(github_config)
        print(f"✅ GitHub Actions workflow saved to {github_dir / 'comprehensive-tests.yml'}")
        
        with open("Jenkinsfile", "w") as f:
            f.write(jenkins_config)
        print("✅ Jenkins pipeline saved to Jenkinsfile")
        
        print("\n📋 Testing Infrastructure Status:")
        print("  • Test Orchestrator: ✅ Ready")
        print("  • CI/CD Integration: ✅ Ready")
        print("  • Configuration Generation: ✅ Working")
        print("  • GitHub Actions: ✅ Generated")
        print("  • Jenkins Pipeline: ✅ Generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def list_test_categories():
    """List all available test categories."""
    print("\n📚 Available Test Categories:")
    print("=" * 50)
    
    categories = {
        'unit': 'Unit tests for individual components',
        'integration': 'Integration tests including database migrations',
        'api_contracts': 'API contract and compatibility testing',
        'security': 'Advanced security vulnerability testing',
        'performance_regression': 'Performance regression detection',
        'chaos_engineering': 'Chaos engineering resilience tests',
        'stress': 'High-concurrency stress testing'
    }
    
    for category, description in categories.items():
        print(f"  {category:20} - {description}")
    
    print("=" * 50)

def main():
    """Main demo function."""
    print("🧪 COMPREHENSIVE TESTING INFRASTRUCTURE DEMO")
    print("=" * 60)
    
    list_test_categories()
    
    print("\n🔧 Testing Orchestrator Functionality...")
    success = test_orchestrator()
    
    if success:
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("  1. Review generated CI/CD configurations")
        print("  2. Run specific test categories")
        print("  3. Integrate with your CI/CD pipeline")
    else:
        print("\n❌ Demo failed. Please check the error messages above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
