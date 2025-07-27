#!/usr/bin/env python3
"""
Simple test runner script for WhatsApp Search tests
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests and display results"""
    print("🧪 Running WhatsApp Search Unit Tests...")
    print("=" * 50)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "test_whatsapp_search.py", 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    """Main function"""
    # Check if we're in the right directory
    if not os.path.exists("test_whatsapp_search.py"):
        print("❌ Error: test_whatsapp_search.py not found!")
        print("Make sure you're running this from the whatsapp-companion-data-analyzer directory")
        sys.exit(1)
    
    success = run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()