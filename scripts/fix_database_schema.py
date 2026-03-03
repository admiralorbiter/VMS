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
    
    # Check and add career_cluster to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'career_cluster' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN career_cluster VARCHAR(255)'))
            db.session.commit()
            print('[OK] Added career_cluster column to event table')
        else:
            print('[INFO] career_cluster column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding career_cluster: {e}')
        db.session.rollback()
    
    # Check and add import_source to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'import_source' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN import_source VARCHAR(50)'))
            db.session.commit()
            print('[OK] Added import_source column to event table')
        else:
            print('[INFO] import_source column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding import_source: {e}')
        db.session.rollback()
    
    # Check and add registered_student_count to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'registered_student_count' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN registered_student_count INTEGER DEFAULT 0'))
            db.session.commit()
            print('[OK] Added registered_student_count column to event table')
        else:
            print('[INFO] registered_student_count column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding registered_student_count: {e}')
        db.session.rollback()
    
    # Check and add attended_student_count to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'attended_student_count' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN attended_student_count INTEGER DEFAULT 0'))
            db.session.commit()
            print('[OK] Added attended_student_count column to event table')
        else:
            print('[INFO] attended_student_count column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding attended_student_count: {e}')
        db.session.rollback()
    
    # Check and add educators to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'educators' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN educators TEXT'))
            db.session.commit()
            print('[OK] Added educators column to event table')
        else:
            print('[INFO] educators column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding educators: {e}')
        db.session.rollback()
    
    # Check and add educator_ids to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'educator_ids' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN educator_ids TEXT'))
            db.session.commit()
            print('[OK] Added educator_ids column to event table')
        else:
            print('[INFO] educator_ids column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding educator_ids: {e}')
        db.session.rollback()
    
    # Check and add professionals to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'professionals' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN professionals TEXT'))
            db.session.commit()
            print('[OK] Added professionals column to event table')
        else:
            print('[INFO] professionals column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding professionals: {e}')
        db.session.rollback()
    
    # Check and add professional_ids to event table
    try:
        existing_columns = [c['name'] for c in inspector.get_columns('event')]
        
        if 'professional_ids' not in existing_columns:
            db.session.execute(text('ALTER TABLE event ADD COLUMN professional_ids TEXT'))
            db.session.commit()
            print('[OK] Added professional_ids column to event table')
        else:
            print('[INFO] professional_ids column already exists in event table')
    except Exception as e:
        print(f'[WARNING] Error adding professional_ids: {e}')
        db.session.rollback()
    
    print('[OK] Database schema fix complete!')

