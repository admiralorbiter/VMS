#!/usr/bin/env python3
"""
Database migration script to create the google_sheets table
Run this script to create the new table for storing Google Sheet IDs
"""

import os
import sys
from sqlalchemy import create_engine, text
from cryptography.fernet import Fernet

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.google_sheet import GoogleSheet

def create_google_sheets_table():
    """Create the google_sheets table"""
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            print("✅ Google Sheets table created successfully!")
            
            # Check if table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'google_sheets'
                );
            """))
            
            if result.scalar():
                print("✅ Table 'google_sheets' exists in database")
                
                # Check if we need to generate an encryption key
                encryption_key = os.getenv('ENCRYPTION_KEY')
                if not encryption_key:
                    new_key = Fernet.generate_key()
                    print(f"\n⚠️  WARNING: No ENCRYPTION_KEY found in environment variables!")
                    print(f"Generated new encryption key: {new_key.decode()}")
                    print("Please add this to your .env file:")
                    print(f"ENCRYPTION_KEY={new_key.decode()}")
                    print("\nThis key is required for encrypting/decrypting Google Sheet IDs.")
                else:
                    print("✅ ENCRYPTION_KEY found in environment variables")
                
                return True
            else:
                print("❌ Table 'google_sheets' was not created")
                return False
                
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            return False

if __name__ == "__main__":
    print("Creating Google Sheets table...")
    success = create_google_sheets_table()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use the Google Sheets management feature.")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1) 