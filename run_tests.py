#!/usr/bin/env python3
"""
Test runner script for Production Embedding Service
Provides both pytest and direct async execution options
"""

import sys
import subprocess
import asyncio
import os

def run_with_pytest():
    """Run tests using pytest"""
    print("🧪 Running tests with pytest...")
    print("=" * 50)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests.py", 
            "-v", 
            "--tb=short",
            "--asyncio-mode=auto"
        ], check=False)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False

def run_direct_async():
    """Run tests directly using asyncio"""
    print("🚀 Running tests directly with asyncio...")
    print("=" * 50)
    
    try:
        # Import and run the async test function
        from tests import run_all_tests
        result = asyncio.run(run_all_tests())
        return result
    except Exception as e:
        print(f"❌ Error running async tests: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_server():
    """Check if the API server is running"""
    import httpx
    
    try:
        with httpx.Client() as client:
            response = client.get("http://localhost:8081/api/v1/health/", timeout=5)
            if response.status_code == 200:
                print("✅ API server is running")
                return True
            else:
                print(f"⚠️  API server responded with status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ API server is not accessible: {e}")
        print("💡 Make sure to start the server: python app.py")
        return False

def main():
    """Main test runner"""
    print("🔧 Production Embedding Service Test Runner")
    print("=" * 50)
    
    # Check if server is running
    if not check_server():
        print("\n❌ Cannot run tests without API server")
        print("📋 Start the server first: python app.py")
        return False
    
    # Determine test method
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        success = run_direct_async()
    else:
        success = run_with_pytest()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests completed successfully!")
    else:
        print("❌ Some tests failed")
    
    return success

if __name__ == "__main__":
    print("Usage:")
    print("  python run_tests.py          # Run with pytest")
    print("  python run_tests.py --direct # Run directly with asyncio")
    print()
    
    success = main()
    sys.exit(0 if success else 1)