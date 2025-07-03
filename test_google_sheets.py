#!/usr/bin/env python3
"""
Test script for Google Sheets management functionality
"""

import os
import sys
from cryptography.fernet import Fernet

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.google_sheet import GoogleSheet
from utils.academic_year import get_current_academic_year, validate_academic_year

def test_encryption():
    """Test encryption/decryption functionality"""
    print("Testing encryption functionality...")
    
    # Test with a sample sheet ID
    test_sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    
    # Create a GoogleSheet instance
    sheet = GoogleSheet(
        academic_year="2023-2024",
        sheet_id=test_sheet_id,
        sheet_name="Test Sheet",
        description="Test description"
    )
    
    # Test decryption
    decrypted_id = sheet.decrypted_sheet_id
    if decrypted_id == test_sheet_id:
        print("✅ Encryption/decryption test passed")
        return True
    else:
        print(f"❌ Encryption/decryption test failed")
        print(f"Expected: {test_sheet_id}")
        print(f"Got: {decrypted_id}")
        return False

def test_academic_year_utils():
    """Test academic year utility functions"""
    print("\nTesting academic year utilities...")
    
    # Test current academic year
    current_year = get_current_academic_year()
    print(f"Current academic year: {current_year}")
    
    # Test validation
    valid_years = ["2023-2024", "2024-2025", "2020-2021"]
    invalid_years = ["2023", "2023-2023", "abc-def", ""]
    
    for year in valid_years:
        if validate_academic_year(year):
            print(f"✅ Valid year: {year}")
        else:
            print(f"❌ Invalid year (should be valid): {year}")
            return False
    
    for year in invalid_years:
        if not validate_academic_year(year):
            print(f"✅ Invalid year correctly rejected: {year}")
        else:
            print(f"❌ Invalid year incorrectly accepted: {year}")
            return False
    
    print("✅ Academic year utilities test passed")
    return True

def test_database_operations():
    """Test database operations"""
    print("\nTesting database operations...")
    
    with app.app_context():
        try:
            # Test creating a sheet
            test_sheet = GoogleSheet(
                academic_year="2023-2024",
                sheet_id="test_sheet_id_123",
                sheet_name="Test Virtual Events",
                description="Test sheet for virtual events"
            )
            
            db.session.add(test_sheet)
            db.session.commit()
            print("✅ Sheet creation test passed")
            
            # Test retrieving the sheet
            retrieved_sheet = GoogleSheet.query.filter_by(academic_year="2023-2024").first()
            if retrieved_sheet is None:
                print("❌ Sheet retrieval test failed - sheet not found")
                return False
            if retrieved_sheet.sheet_name == "Test Virtual Events":
                print("✅ Sheet retrieval test passed")
            else:
                print("❌ Sheet retrieval test failed - wrong sheet name")
                return False
            
            # Test updating the sheet
            retrieved_sheet.sheet_name = "Updated Test Virtual Events"
            db.session.commit()
            
            updated_sheet = GoogleSheet.query.filter_by(academic_year="2023-2024").first()
            if updated_sheet.sheet_name == "Updated Test Virtual Events":
                print("✅ Sheet update test passed")
            else:
                print("❌ Sheet update test failed")
                return False
            
            # Test deleting the sheet
            db.session.delete(retrieved_sheet)
            db.session.commit()
            
            deleted_sheet = GoogleSheet.query.filter_by(academic_year="2023-2024").first()
            if deleted_sheet is None:
                print("✅ Sheet deletion test passed")
            else:
                print("❌ Sheet deletion test failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Database operations test failed: {e}")
            db.session.rollback()
            return False

def main():
    """Run all tests"""
    print("Running Google Sheets functionality tests...\n")
    
    # Check if encryption key is set
    if not os.getenv('ENCRYPTION_KEY'):
        print("⚠️  WARNING: ENCRYPTION_KEY not set in environment")
        print("Generating temporary key for testing...")
        temp_key = Fernet.generate_key()
        os.environ['ENCRYPTION_KEY'] = temp_key.decode()
    
    tests = [
        ("Encryption", test_encryption),
        ("Academic Year Utils", test_academic_year_utils),
        ("Database Operations", test_database_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} Test")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print(f"{'='*50}")
    
    if passed == total:
        print("🎉 All tests passed! Google Sheets functionality is working correctly.")
        return 0
    else:
        print("💥 Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 