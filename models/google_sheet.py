from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from models import db
from cryptography.fernet import Fernet
import base64
import os
from datetime import datetime, timezone
from flask import current_app

class GoogleSheet(db.Model):
    __tablename__ = 'google_sheets'
    
    id = Column(Integer, primary_key=True)
    academic_year = Column(String(10), nullable=False, unique=True)  # e.g., "2023-2024"
    sheet_id = Column(Text, nullable=False)  # Encrypted Google Sheet ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, db.ForeignKey('users.id'))
    
    # Relationship to user who created it
    creator = db.relationship('User', backref='created_sheets')
    
    def __init__(self, academic_year, sheet_id, created_by=None):
        self.academic_year = academic_year
        self.sheet_id = self._encrypt_sheet_id(sheet_id)
        self.created_by = created_by
    
    def _get_encryption_key(self):
        """Get or create encryption key from environment variable"""
        # Try to get from Flask config first, then environment
        try:
            key = current_app.config.get('ENCRYPTION_KEY')
        except RuntimeError:
            # If we're outside application context, fall back to os.getenv
            key = os.getenv('ENCRYPTION_KEY')
            
        if not key:
            # Generate a new key if none exists
            key = Fernet.generate_key()
            print(f"WARNING: No ENCRYPTION_KEY found in environment. Generated new key: {key.decode()}")
            print("Please add this key to your environment variables for production use.")
        elif isinstance(key, str):
            key = key.encode()
        return key
    
    def _encrypt_sheet_id(self, sheet_id):
        """Encrypt the Google Sheet ID"""
        if not sheet_id:
            return None
        
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(sheet_id.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def _decrypt_sheet_id(self, encrypted_sheet_id):
        """Decrypt the Google Sheet ID"""
        if not encrypted_sheet_id:
            return None
        
        try:
            key = self._get_encryption_key()
            f = Fernet(key)
            encrypted_data = base64.b64decode(encrypted_sheet_id.encode())
            decrypted_data = f.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Error decrypting sheet ID: {e}")
            return None
    
    @property
    def decrypted_sheet_id(self):
        """Get the decrypted Google Sheet ID"""
        return self._decrypt_sheet_id(self.sheet_id)
    
    def update_sheet_id(self, new_sheet_id):
        """Update the encrypted sheet ID"""
        self.sheet_id = self._encrypt_sheet_id(new_sheet_id)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'academic_year': self.academic_year,
            'sheet_id': self.decrypted_sheet_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None
        }
    
    def __repr__(self):
        return f'<GoogleSheet {self.academic_year}>' 