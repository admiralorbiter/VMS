from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models import db

class Organization(db.Model):
    """Organization model representing companies, schools, or other institutions.
    
    This model stores core information about organizations that volunteers are associated with.
    It supports bi-directional sync with Salesforce and includes address information.
    
    Relationships:
    - volunteers: Many-to-many with Volunteer model through volunteer_organization table
    - volunteer_organizations: One-to-many with VolunteerOrganization model (association table)
    """
    __tablename__ = 'organization'
    
    # Primary identifier and Salesforce integration fields
    id = db.Column(Integer, primary_key=True)
    # Salesforce Account ID (18 char) - indexed for sync operations
    salesforce_id = db.Column(String(18), unique=True, nullable=True, index=True)
    # Organization name - indexed for search operations
    name = db.Column(String(255), nullable=False, index=True)
    # Organization classification (e.g., "School", "Business", "Non-profit")
    type = db.Column(String(255), nullable=True)
    description = db.Column(String(255), nullable=True)
    
    # Reference to volunteer record in Salesforce
    volunteer_salesforce_id = db.Column(String(18), nullable=True, index=True)
    
    # Address fields
    # TODO: Consider refactoring these into a separate Address model
    # that can be reused across different entities
    billing_street = db.Column(String(255), nullable=True)
    billing_city = db.Column(String(255), nullable=True)
    billing_state = db.Column(String(255), nullable=True)
    billing_postal_code = db.Column(String(255), nullable=True)
    billing_country = db.Column(String(255), nullable=True)
    
    # Automatic timestamp fields
    # created_at: Set once when record is created
    # updated_at: Automatically updated whenever record is modified
    # last_activity_date: Manually set to track business-level activity
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_activity_date = db.Column(db.DateTime, nullable=True)

    # Relationship definitions
    # volunteers: Many-to-many relationship allowing direct access to associated Volunteer records
    # overlaps: Tells SQLAlchemy that this relationship shares some foreign keys with volunteer_organizations
    volunteers = relationship(
        'Volunteer',
        secondary='volunteer_organization',
        back_populates='organizations',      # Match the name in Volunteer model
        overlaps="volunteer_organizations"   # Match the relationship name
    )
    
    # Direct access to the association records
    # cascade='all, delete-orphan': Automatically deletes association records when Organization is deleted
    # passive_deletes=True: Lets the database handle cascade deletes for better performance
    volunteer_organizations = relationship(
        'VolunteerOrganization',
        back_populates='organization',
        cascade='all, delete-orphan',
        passive_deletes=True,
        overlaps="volunteers"
    )

    @property
    def salesforce_url(self):
        """Generate Salesforce URL if ID exists
        
        Returns:
            str: URL to Salesforce record, or None if no salesforce_id exists
        """
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_id}/view"
        return None

class VolunteerOrganization(db.Model):
    """Association model connecting volunteers to organizations.
    
    This is a junction table that manages the many-to-many relationship between
    Volunteer and Organization models. It includes additional metadata about
    the relationship such as role, dates, and status.
    
    Primary Keys:
    - volunteer_id and organization_id form a composite primary key
    
    Note: confirm_deleted_rows=False improves deletion performance for bulk operations
    """
    __tablename__ = 'volunteer_organization'
    
    __mapper_args__ = {
        'confirm_deleted_rows': False  # Performance optimization for deletions
    }
    
    # Composite primary key columns
    # ondelete='CASCADE': Automatically deletes records if parent is deleted
    # index=True: Speeds up joins and lookups
    volunteer_id = db.Column(Integer, 
                           ForeignKey('volunteer.id', ondelete='CASCADE'), 
                           primary_key=True,
                           index=True)
    organization_id = db.Column(Integer, 
                              ForeignKey('organization.id', ondelete='CASCADE'), 
                              primary_key=True,
                              index=True)
                              
    # Salesforce integration fields - indexed for sync operations
    salesforce_volunteer_id = db.Column(db.String(18), nullable=True, index=True)
    salesforce_org_id = db.Column(db.String(18), nullable=True, index=True)
    
    # Relationship metadata
    role = db.Column(String(255), nullable=True)  # Position/role at organization
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    is_primary = db.Column(Boolean, default=False)  # Indicates primary organization for volunteer
    status = db.Column(String(50), default='Current')  # e.g., 'Current', 'Past', 'Pending'
    
    # Automatic timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Fix the relationships - remove secondary and use direct relationships
    volunteer = relationship(
        'Volunteer',
        back_populates='volunteer_organizations',
        overlaps="organizations,volunteers"  # Add both relationship names
    )
    
    organization = relationship(
        'Organization',
        back_populates='volunteer_organizations',
        overlaps="organizations,volunteers"  # Add both relationship names
    )
