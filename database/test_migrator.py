#!/usr/bin/env python3
"""
Test script to validate the Docker migrator image
"""

import subprocess
import json
import time

def test_migrator_image():
    """Test the tender-migrator Docker image"""
    print("🔧 Testing Docker Migrator Image...")
    
    # Test 1: Check if image exists
    try:
        result = subprocess.run(['docker', 'images', 'tender-migrator'], 
                              capture_output=True, text=True, check=True)
        if 'tender-migrator' in result.stdout:
            print("✅ Docker image 'tender-migrator' exists")
        else:
            print("❌ Docker image 'tender-migrator' not found")
            return False
    except subprocess.CalledProcessError:
        print("❌ Failed to check Docker images")
        return False
    
    # Test 2: Check container can start and run
    try:
        result = subprocess.run([
            'docker', 'run', '--rm', 
            '-e', 'POSTGRES_HOST=test_host',
            '-e', 'MONGODB_HOST=test_host', 
            '-e', 'REDIS_HOST=test_host',
            'tender-migrator', 
            'timeout', '3', 'python', 'migrate_standalone.py'
        ], capture_output=True, text=True, timeout=10)
        
        if "Database Migration Orchestrator Starting" in result.stdout:
            print("✅ Migration script starts correctly")
        else:
            print("❌ Migration script failed to start")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✅ Migration script runs (timed out as expected)")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Migration script exited with code {e.returncode} (expected due to no database)")
        if "Database Migration Orchestrator Starting" in e.stdout:
            print("✅ But script started correctly")
        else:
            print("❌ Script failed to start properly")
            return False
    
    # Test 3: Check file structure
    try:
        result = subprocess.run(['docker', 'run', '--rm', 'tender-migrator', 'ls', '-la', '/app/'], 
                              capture_output=True, text=True, check=True)
        
        required_items = ['migrate_standalone.py', 'postgresql', 'mongodb', 'migrations']
        missing_items = []
        
        for item in required_items:
            if item not in result.stdout:
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing required items in container: {missing_items}")
            return False
        else:
            print("✅ All required files and directories present")
    except subprocess.CalledProcessError:
        print("❌ Failed to check container file structure")
        return False
    
    # Test 4: Check database tools
    tools_to_check = [
        ('psql', 'PostgreSQL client'),
        ('mongosh', 'MongoDB shell'),
    ]
    
    for tool, description in tools_to_check:
        try:
            result = subprocess.run(['docker', 'run', '--rm', 'tender-migrator', 'which', tool], 
                                  capture_output=True, text=True, check=True)
            if result.stdout.strip():
                print(f"✅ {description} available at {result.stdout.strip()}")
            else:
                print(f"❌ {description} not found")
                return False
        except subprocess.CalledProcessError:
            print(f"❌ {description} not available")
            return False
    
    # Test 5: Check Python packages
    try:
        result = subprocess.run([
            'docker', 'run', '--rm', 'tender-migrator', 
            'python', '-c', 'import psycopg2, pymongo, redis; print("OK")'
        ], capture_output=True, text=True, check=True)
        
        if result.stdout.strip() == "OK":
            print("✅ All required Python packages available")
        else:
            print("❌ Python packages test failed")
            return False
    except subprocess.CalledProcessError:
        print("❌ Failed to import required Python packages")
        return False
    
    return True

def main():
    print("=" * 60)
    print("Docker Migrator Image Validation Test")
    print("=" * 60)
    
    success = test_migrator_image()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Docker migrator image is ready.")
        print("\nUsage:")
        print("docker run --rm -e POSTGRES_HOST=<host> -e MONGODB_HOST=<host> -e REDIS_HOST=<host> tender-migrator")
    else:
        print("❌ Some tests failed. Please check the issues above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
