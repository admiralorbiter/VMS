from datetime import datetime, timezone
from models import db  # Import db from models instead of creating new instance

class DistrictYearEndReport(db.Model):
    __tablename__ = 'district_year_end_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey('district.id'), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # Added index
    host_filter = db.Column(db.String(20), default='all', nullable=False, index=True)
    report_data = db.Column(db.JSON, nullable=False)
    events_data = db.Column(db.JSON, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    district = db.relationship('District', backref='year_end_reports')
    
    __table_args__ = (
        db.UniqueConstraint('district_id', 'school_year', 'host_filter', name='uix_district_school_year_host_filter'),
        db.Index('idx_school_year_last_updated', 'school_year', 'last_updated')  # Added composite index
    )

class DistrictEngagementReport(db.Model):
    __tablename__ = 'district_engagement_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey('district.id'), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)
    
    # Cache for summary stats and detailed data
    summary_stats = db.Column(db.JSON, nullable=False)
    volunteers_data = db.Column(db.JSON, nullable=True)
    students_data = db.Column(db.JSON, nullable=True)
    events_data = db.Column(db.JSON, nullable=True)
    
    # Cache for full breakdown data (event-centric view)
    breakdown_data = db.Column(db.JSON, nullable=True)
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    district = db.relationship('District', backref='engagement_reports')
    
    __table_args__ = (
        db.UniqueConstraint('district_id', 'school_year', name='uix_district_engagement_school_year'),
        db.Index('idx_engagement_school_year_updated', 'school_year', 'last_updated')
    )


class OrganizationReport(db.Model):
    __tablename__ = 'organization_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(18), db.ForeignKey('organization.id'), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)
    
    # Cache for summary stats
    summary_stats = db.Column(db.JSON, nullable=False)
    
    # Cache for detailed event data
    in_person_events_data = db.Column(db.JSON, nullable=True)
    virtual_events_data = db.Column(db.JSON, nullable=True)
    cancelled_events_data = db.Column(db.JSON, nullable=True)
    volunteers_data = db.Column(db.JSON, nullable=True)
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    organization = db.relationship('Organization', backref='cached_reports')
    
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'school_year', name='uix_organization_school_year'),
        db.Index('idx_organization_school_year_updated', 'school_year', 'last_updated')
    )


class OrganizationSummaryCache(db.Model):
    __tablename__ = 'organization_summary_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # e.g., '2425'
    organizations_data = db.Column(db.JSON)  # Cached organization summary data
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<OrganizationSummaryCache {self.school_year}>'


class OrganizationDetailCache(db.Model):
    __tablename__ = 'organization_detail_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, index=True)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # e.g., '2425'
    organization_name = db.Column(db.String(255))  # For easier identification
    
    # Cached detailed data as JSON
    in_person_events = db.Column(db.JSON)  # List of in-person event data
    virtual_events = db.Column(db.JSON)    # List of virtual event data
    cancelled_events = db.Column(db.JSON)  # List of cancelled event data
    volunteers_data = db.Column(db.JSON)   # Volunteer summary data
    summary_stats = db.Column(db.JSON)     # Summary statistics
    
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('organization_id', 'school_year', name='uq_org_detail_cache'),
    )
    
    def __repr__(self):
        return f'<OrganizationDetailCache {self.organization_name} {self.school_year}>' 