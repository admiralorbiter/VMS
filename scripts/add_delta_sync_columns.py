"""Quick script to add delta sync columns to sync_logs table."""
from app import app
from models import db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)
    existing_columns = [c['name'] for c in inspector.get_columns('sync_logs')]
    
    if 'last_sync_watermark' not in existing_columns:
        db.session.execute(text('ALTER TABLE sync_logs ADD COLUMN last_sync_watermark DATETIME'))
        print('Added last_sync_watermark column')
    else:
        print('last_sync_watermark column already exists')
    
    if 'is_delta_sync' not in existing_columns:
        db.session.execute(text('ALTER TABLE sync_logs ADD COLUMN is_delta_sync BOOLEAN DEFAULT 0'))
        print('Added is_delta_sync column')
    else:
        print('is_delta_sync column already exists')
    
    db.session.commit()
    print('Done!')
