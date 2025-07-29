#!/usr/bin/env python3
"""
Test script to check if volunteers sync workflow can be submitted
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_volunteers_submit():
    """Test if volunteers sync workflow can be submitted."""
    try:
        from workflows.salesforce_sync.volunteers_sync import volunteers_sync_flow
        print("✅ Volunteers sync flow imported successfully")
        
        # Try to submit the workflow
        try:
            result = volunteers_sync_flow()
            print(f"✅ Workflow executed successfully!")
            print(f"Result: {result}")
            return True
        except Exception as e:
            print(f"❌ Error submitting workflow: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error importing volunteers sync flow: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prefect_client():
    """Test if Prefect client can be created."""
    try:
        from prefect.client.orchestration import get_client
        client = get_client()
        print("✅ Prefect client created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating Prefect client: {e}")
        return False

if __name__ == '__main__':
    print("Testing volunteers sync workflow submission...")
    print("=" * 60)
    
    test1 = test_prefect_client()
    test2 = test_volunteers_submit()
    
    print("=" * 60)
    if all([test1, test2]):
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!") 