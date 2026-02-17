"""
Quick script to add missing columns to the database schema.
Run this if migrations aren't available.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    
    # Check and add tenant_role to users table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('users')]
        
        if 'tenant_role' not in existing_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN tenant_role VARCHAR(20)'))
            db.session.commit()
            print('[OK] Added tenant_role column to users table')
        else:
            print('[INFO] tenant_role column already exists in users table')
    except Exception as e:
        print(f'[WARNING] Error adding tenant_role: {e}')
        db.session.rollback()
    
    # Check and add is_active to users table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('users')]
        
        if 'is_active' not in existing_columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1'))
            db.session.commit()
            print('[OK] Added is_active column to users table')
        else:
            print('[INFO] is_active column already exists in users table')
    except Exception as e:
        print(f'[WARNING] Error adding is_active: {e}')
        db.session.rollback()
    
    # Check and add pathful_user_id to volunteer table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('volunteer')]
        
        if 'pathful_user_id' not in existing_columns:
            db.session.execute(text('ALTER TABLE volunteer ADD COLUMN pathful_user_id VARCHAR(100)'))
            db.session.commit()
            print('[OK] Added pathful_user_id column to volunteer table')
        else:
            print('[INFO] pathful_user_id column already exists in volunteer table')
    except Exception as e:
        print(f'[WARNING] Error adding pathful_user_id: {e}')
        db.session.rollback()
    
    # Check and add cancellation_notes to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'cancellation_notes' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN cancellation_notes TEXT'))
            db.session.commit()
            print('[OK] Added cancellation_notes column to event table')
        else:
            print('[INFO] cancellation_notes column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding cancellation_notes: {e}')
        db.session.rollback()
    
    # Check and add cancellation_set_by to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'cancellation_set_by' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN cancellation_set_by INTEGER'))
            db.session.commit()
            print('[OK] Added cancellation_set_by column to event table')
        else:
            print('[INFO] cancellation_set_by column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding cancellation_set_by: {e}')
        db.session.rollback()
    
    # Check and add cancellation_set_at to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'cancellation_set_at' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN cancellation_set_at DATETIME'))
            db.session.commit()
            print('[OK] Added cancellation_set_at column to event table')
        else:
            print('[INFO] cancellation_set_at column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding cancellation_set_at: {e}')
        db.session.rollback()
    
    # Check and add pathful_session_id to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'pathful_session_id' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN pathful_session_id VARCHAR(100)'))
            db.session.commit()
            print('[OK] Added pathful_session_id column to event table')
        else:
            print('[INFO] pathful_session_id column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding pathful_session_id: {e}')
        db.session.rollback()
    
    print('[OK] Database schema fix complete!')

