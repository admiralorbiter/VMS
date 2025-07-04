"""
Pathway Model and Association Tables
==================================

This module defines the Pathway model and its relationships with Contact and Event models.
Pathways represent career or educational pathways that students can follow, and they can
be associated with multiple contacts (students) and events.

Key Features:
- Many-to-many relationships with Contact and Event models
- Salesforce integration with salesforce_id field
- Automatic timestamp tracking for created_at and updated_at
- Indexed salesforce_id for efficient lookups

Database Tables:
- pathway: Main pathway table with basic information
- pathway_contacts: Association table linking pathways to contacts
- pathway_events: Association table linking pathways to events

Usage:
    # Create a new pathway
    pathway = Pathway(name="Computer Science", salesforce_id="a1b2c3d4e5f6g7h8i9")
    db.session.add(pathway)
    db.session.commit()
    
    # Associate with contacts and events
    pathway.contacts.append(student_contact)
    pathway.events.append(event)
    db.session.commit()
"""

from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models import db

class Pathway(db.Model):
    """
    Pathway Model
    
    Represents a career or educational pathway that can be associated with
    multiple contacts (students) and events. Pathways help organize and
    categorize educational experiences and career development activities.
    
    Attributes:
        id: Primary key identifier
        salesforce_id: Unique Salesforce identifier for integration
        name: Human-readable pathway name
        contacts: Many-to-many relationship with Contact model
        events: Many-to-many relationship with Event model
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    
    Relationships:
        - Many-to-many with Contact via pathway_contacts table
        - Many-to-many with Event via pathway_events table
    """
    __tablename__ = 'pathway'
    
    # Primary identifier and Salesforce integration fields
    id = db.Column(Integer, primary_key=True)

    # Index salesforce_id since it's used for lookups and is unique
    salesforce_id = db.Column(String(18), unique=True, nullable=True, index=True)

    # Human-readable pathway name
    name = db.Column(String(255), nullable=False)

    # Add relationships to Contact and Event
    contacts = relationship(
        'Contact',
        secondary='pathway_contacts',  # Association table name
        backref=db.backref('pathways', lazy='dynamic'),
        lazy='dynamic'
    )

    events = relationship(
        'Event',
        secondary='pathway_events',  # Association table name
        backref=db.backref('pathways', lazy='dynamic'),
        lazy='dynamic'
    )

    # Automatic timestamp fields for auditing and tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Association table for Pathway-Contact relationship
# This table enables many-to-many relationship between pathways and contacts (students)
pathway_contacts = db.Table('pathway_contacts',
    db.Column('pathway_id', Integer, ForeignKey('pathway.id'), primary_key=True),
    db.Column('contact_id', Integer, ForeignKey('contact.id'), primary_key=True)
)

# Association table for Pathway-Event relationship
# This table enables many-to-many relationship between pathways and events
pathway_events = db.Table('pathway_events',
    db.Column('pathway_id', Integer, ForeignKey('pathway.id'), primary_key=True),
    db.Column('event_id', Integer, ForeignKey('event.id'), primary_key=True)
)
