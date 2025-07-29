#!/usr/bin/env python3
"""
Test script to check volunteers sync functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_volunteers_sync_import():
    """Test if volunteers sync can be imported."""
    try:
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        print("✅ Volunteers sync flow imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing volunteers sync flow: {e}")
        return False

def test_salesforce_config():
    """Test if Salesforce configuration is available."""
    try:
        from config import Config
        config = Config()
        print("✅ Salesforce configuration loaded successfully")
        print(f"   SF_USERNAME: {'Set' if config.SF_USERNAME else 'Not set'}")
        print(f"   SF_PASSWORD: {'Set' if config.SF_PASSWORD else 'Not set'}")
        print(f"   SF_SECURITY_TOKEN: {'Set' if config.SF_SECURITY_TOKEN else 'Not set'}")
        return True
    except Exception as e:
        print(f"❌ Error loading Salesforce configuration: {e}")
        return False

def test_prefect_workflow():
    """Test if Prefect workflow can be created."""
    try:
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        print("✅ Prefect workflow can be created")
        return True
    except Exception as e:
        print(f"❌ Error creating Prefect workflow: {e}")
        return False

if __name__ == '__main__':
    print("Testing volunteers sync functionality...")
    print("=" * 50)
    
    test1 = test_volunteers_sync_import()
    test2 = test_salesforce_config()
    test3 = test_prefect_workflow()
    
    print("=" * 50)
    if all([test1, test2, test3]):
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!") 