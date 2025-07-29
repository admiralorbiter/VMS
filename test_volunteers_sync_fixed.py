#!/usr/bin/env python3
"""
Test script to verify volunteers sync workflow after SQLAlchemy fixes.
"""

import os
import sys
from datetime import datetime

def test_volunteers_sync_import():
    """Test if volunteers sync workflow can be imported."""
    try:
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        print("✅ Volunteers sync flow imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing volunteers sync flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_base_workflow_import():
    """Test if base workflow can be imported."""
    try:
        from workflows.base_workflow import database_connection, salesforce_connection
        print("✅ Base workflow tasks imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing base workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection task."""
    try:
        from workflows.base_workflow import database_connection
        print("✅ Database connection task imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error with database connection task: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_volunteers_sync_execution():
    """Test if volunteers sync workflow can be executed."""
    try:
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        print("✅ Volunteers sync flow imported successfully")
        
        # Try to execute the workflow
        try:
            print("🔄 Attempting to execute volunteers sync workflow...")
            result = volunteers_sync_flow()
            print(f"✅ Workflow executed successfully!")
            print(f"Result: {result}")
            return True
        except Exception as e:
            print(f"❌ Error executing workflow: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error importing volunteers sync flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Testing volunteers sync workflow after SQLAlchemy fixes...")
    print("=" * 60)
    
    # Test imports
    print("\n1. Testing imports...")
    base_ok = test_base_workflow_import()
    volunteers_ok = test_volunteers_sync_import()
    db_ok = test_database_connection()
    
    if not all([base_ok, volunteers_ok, db_ok]):
        print("❌ Import tests failed. Stopping.")
        return False
    
    print("\n2. Testing workflow execution...")
    execution_ok = test_volunteers_sync_execution()
    
    if execution_ok:
        print("\n✅ All tests passed! Volunteers sync should work now.")
        return True
    else:
        print("\n❌ Execution test failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 