#!/usr/bin/env python3
"""
Set test environment variables for development
"""

import os

def set_test_environment():
    """Set test environment variables."""
    print("Setting test environment variables...")
    
    # Set test environment variables
    os.environ['SF_USERNAME'] = 'test@example.com'
    os.environ['SF_PASSWORD'] = 'test_password'
    os.environ['SF_SECURITY_TOKEN'] = 'test_token'
    os.environ['SECRET_KEY'] = 'test_secret_key'
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'
    
    print("✅ Test environment variables set:")
    print(f"  SF_USERNAME: {os.environ.get('SF_USERNAME')}")
    print(f"  SF_PASSWORD: {os.environ.get('SF_PASSWORD')}")
    print(f"  SF_SECURITY_TOKEN: {os.environ.get('SF_SECURITY_TOKEN')}")
    print(f"  SECRET_KEY: {os.environ.get('SECRET_KEY')}")
    print(f"  DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    
    print("\nNote: These are test values. For production, set real Salesforce credentials.")

if __name__ == '__main__':
    set_test_environment() 