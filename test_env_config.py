#!/usr/bin/env python3
"""
Test script to check environment configuration
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_environment():
    """Test environment configuration."""
    print("Environment Configuration Test")
    print("=" * 50)
    
    # Check environment variables
    env_vars = [
        'SF_USERNAME',
        'SF_PASSWORD', 
        'SF_SECURITY_TOKEN',
        'FLASK_ENV',
        'DATABASE_URL',
        'SECRET_KEY'
    ]
    
    print("Environment Variables:")
    for var in env_vars:
        value = os.getenv(var)
        status = "✅ Set" if value else "❌ Not set"
        print(f"  {var}: {status}")
        if value:
            print(f"    Value: {value[:10]}..." if len(value) > 10 else f"    Value: {value}")
    
    print("\nConfig Test:")
    try:
        from config import Config
        print(f"  SF_USERNAME: {'✅ Set' if Config.SF_USERNAME else '❌ Not set'}")
        print(f"  SF_PASSWORD: {'✅ Set' if Config.SF_PASSWORD else '❌ Not set'}")
        print(f"  SF_SECURITY_TOKEN: {'✅ Set' if Config.SF_SECURITY_TOKEN else '❌ Not set'}")
    except Exception as e:
        print(f"  ❌ Config error: {e}")
    
    print("\nDatabase Test:")
    try:
        from models import db
        db.session.execute("SELECT 1")
        print("  ✅ Database connection successful")
    except Exception as e:
        print(f"  ❌ Database error: {e}")

if __name__ == '__main__':
    test_environment() 