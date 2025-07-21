#!/usr/bin/env python3
"""
Test Email Import Script
=======================

This script tests the email import functionality from Salesforce to verify
that email messages are being properly imported and stored in the history table.

The email content is stored in the Task Description field in Salesforce with
a specific format including headers like "To:", "CC:", "Subject:", "Body:".

Usage:
    python scripts/test_email_import.py

Dependencies:
    - Flask app context
    - Salesforce connection
    - Database models
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from models.history import History
from models.volunteer import Volunteer
from routes.history.routes import import_history_from_salesforce
from flask import Flask

def test_email_import():
    """Test the email import functionality"""
    app = create_app()
    
    with app.app_context():
        print("Testing email import functionality...")
        
        # Check if we have any volunteers with Salesforce IDs
        volunteers_with_sf = Volunteer.query.filter(
            Volunteer.salesforce_individual_id.isnot(None)
        ).limit(5).all()
        
        print(f"Found {len(volunteers_with_sf)} volunteers with Salesforce IDs")
        
        # Check existing history records
        total_history = History.query.count()
        email_history = History.query.filter_by(activity_type='Email').count()
        
        print(f"Total history records: {total_history}")
        print(f"Email history records: {email_history}")
        
        # Show some sample email history records
        if email_history > 0:
            print("\nSample email history records:")
            email_records = History.query.filter_by(activity_type='Email').limit(3).all()
            for record in email_records:
                print(f"  - {record.summary} ({record.activity_date})")
                if record.description:
                    # Extract email body content for preview
                    lines = record.description.split('\n')
                    body_content = []
                    body_started = False
                    for line in lines[:10]:
                        if line.strip().startswith('Body:'):
                            body_started = True
                            body_content.append(line.strip()[6:])  # Remove "Body:" prefix
                        elif body_started and line.strip():
                            body_content.append(line.strip())
                    
                    preview = ' '.join(body_content)
                    preview = preview[:100] + "..." if len(preview) > 100 else preview
                    print(f"    Content: {preview}")
        
        # Test the import function (this would require Salesforce credentials)
        print("\nNote: To test the actual import, you would need to:")
        print("1. Have valid Salesforce credentials in config.py")
        print("2. Run the import function manually")
        print("3. Check that Task records with Type='Email' are being imported")
        print("4. Verify that email content from Description field is being extracted")

if __name__ == "__main__":
    test_email_import() 