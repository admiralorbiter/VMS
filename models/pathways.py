from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models import db

class Pathway(db.Model):
    __tablename__ = 'pathway'
    # Primary identifier and Salesforce integration fields
    id = db.Column(Integer, primary_key=True)

    # Index salesforce_id since it's used for lookups and is unique
    salesforce_id = db.Column(String(18), unique=True, nullable=True, index=True)

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

    # Automatic timestamp fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Association table for Pathway-Contact relationship
pathway_contacts = db.Table('pathway_contacts',
    db.Column('pathway_id', Integer, ForeignKey('pathway.id'), primary_key=True),
    db.Column('contact_id', Integer, ForeignKey('contact.id'), primary_key=True)
)

# Association table for Pathway-Event relationship
pathway_events = db.Table('pathway_events',
    db.Column('pathway_id', Integer, ForeignKey('pathway.id'), primary_key=True),
    db.Column('event_id', Integer, ForeignKey('event.id'), primary_key=True)
)
