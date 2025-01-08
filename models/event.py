from datetime import datetime
from enum import Enum
from sqlalchemy import String, Enum as SQLAlchemyEnum

from models import db

# Define the association table first
event_volunteers = db.Table('event_volunteers',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteer.id'), primary_key=True)
)

# Add this association table for event-district relationship
event_districts = db.Table('event_districts',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('district_id', db.Integer, db.ForeignKey('district.id'), primary_key=True)
)

# Add this near the top with other association tables
event_skills = db.Table('event_skills',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

class EventType(str, Enum):
    IN_PERSON = 'in_person'
    VIRTUAL_SESSION = 'virtual_session'
    CONNECTOR_SESSION = 'connector_session'
    CAREER_JUMPING = 'career_jumping'
    CAREER_SPEAKER = 'career_speaker'
    EMPLOYABILITY_SKILLS = 'employability_skills'
    IGNITE = 'ignite'
    CAREER_FAIR = 'career_fair'
    CLIENT_CONNECTED_PROJECT = 'client_connected_project'
    PATHWAY_CAMPUS_VISITS = 'pathway_campus_visits'
    WORKPLACE_VISIT = 'workplace_visit'
    PATHWAY_WORKPLACE_VISITS = 'pathway_workplace_visits'
    COLLEGE_OPTIONS = 'college_options'
    DIA_CLASSROOM_SPEAKER = 'dia_classroom_speaker'
    DIA = 'dia'
    CAMPUS_VISIT = 'campus_visit'
    ADVISORY_SESSIONS = 'advisory_sessions'
    VOLUNTEER_ORIENTATION = 'volunteer_orientation'
    VOLUNTEER_ENGAGEMENT = 'volunteer_engagement'
    MENTORING = 'mentoring'
    FINANCIAL_LITERACY = 'financial_literacy'
    MATH_RELAYS = 'math_relays'
    CLASSROOM_SPEAKER = 'classroom_speaker'
    INTERNSHIP = 'internship'
    COLLEGE_APPLICATION_FAIR = 'college_application_fair'
    FAFSA = 'fafsa'
    CLASSROOM_ACTIVITY = 'classroom_activity'
    HISTORICAL = 'historical'
    DATA_VIZ = 'data_viz'

class CancellationReason(str, Enum):
    WEATHER = 'weather'
    LOW_ENROLLMENT = 'low_enrollment'
    INSTRUCTOR_UNAVAILABLE = 'instructor_unavailable'
    FACILITY_ISSUE = 'facility_issue'
    OTHER = 'other'

class EventComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AttendanceStatus(str, Enum):
    NOT_TAKEN = 'not_taken'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

class EventAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    
    # Attendance details
    status = db.Column(SQLAlchemyEnum(AttendanceStatus), default=AttendanceStatus.NOT_TAKEN, nullable=False)
    last_taken = db.Column(db.DateTime, nullable=True)
    total_attendance = db.Column(db.Integer, default=0)  # Simple counter for now
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship back to event
    event = db.relationship('Event', backref=db.backref('attendance', uselist=False))

class District(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<District {self.name}>'

class EventFormat(str, Enum):
    IN_PERSON = 'in_person'
    VIRTUAL = 'virtual'

class EventStatus(str, Enum):
    COMPLETED = 'Completed'
    CONFIRMED = 'Confirmed'
    CANCELLED = 'Cancelled'
    REQUESTED = 'Requested'
    DRAFT = 'Draft'
    PUBLISHED = 'Published'

class Event(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(String(18), unique=True, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(SQLAlchemyEnum(EventType), default=EventType.IN_PERSON)
    cancellation_reason = db.Column(SQLAlchemyEnum(CancellationReason), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    status = db.Column(SQLAlchemyEnum(EventStatus), nullable=False, default=EventStatus.DRAFT)
    volunteer_needed = db.Column(db.Integer)
    format = db.Column(SQLAlchemyEnum(EventFormat), nullable=False, default=EventFormat.IN_PERSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    participant_count = db.Column(db.Integer, default=0)
    
    # Virtual specific fields (new)
    session_id = db.Column(db.String(255))  # Session ID from CSV
    series = db.Column(db.String(255))      # Series or Career Cluster
    duration = db.Column(db.Integer)        # Duration in minutes
    registered_count = db.Column(db.Integer, default=0)
    attended_count = db.Column(db.Integer, default=0)
    educator_name = db.Column(db.String(255))    # User Auth Name
    educator_id = db.Column(db.String(255))      # User Auth ID
    school = db.Column(db.String(255))           # School/District info
    district_partner = db.Column(db.String(255)) # District or Partner
    
    # Relationships
    volunteers = db.relationship('Volunteer', 
                               secondary=event_volunteers,
                               backref=db.backref('events', lazy='dynamic'))
    comments = db.relationship('EventComment', 
                             backref='event',
                             lazy='dynamic',
                             cascade='all, delete-orphan')
    districts = db.relationship('District', 
                              secondary=event_districts,
                              backref=db.backref('events', lazy='dynamic'))
    skills = db.relationship('Skill', 
                           secondary=event_skills,
                           backref=db.backref('events', lazy='dynamic'))

    @property
    def volunteer_count(self):
        return len(self.volunteers)
    
    @property
    def attendance_status(self):
        """Helper property to easily check attendance status"""
        if not self.attendance:
            return AttendanceStatus.NOT_TAKEN
        return self.attendance.status
    
    @property
    def attendance_count(self):
        """Helper property to easily get attendance count"""
        if not self.attendance:
            return 0
        return self.attendance.total_attendance

    @property
    def display_status(self):
        """Returns a clean version of the status for display"""
        return self.status.value if hasattr(self.status, 'value') else str(self.status)

    @property
    def salesforce_url(self):
        """Generate Salesforce session URL if ID exists"""
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Session__c/{self.salesforce_id}/view"
        return None

    @property
    def is_virtual(self):
        return self.type == EventType.VIRTUAL_SESSION

    def update_from_csv(self, data):
        """Update event from CSV data"""
        self.session_id = data.get('Session ID')
        self.title = data.get('Title')
        self.series = data.get('Series or Event Title')
        
        # Handle date conversion
        date_str = data.get('Date')
        if date_str:
            self.start_date = datetime.strptime(date_str, '%m/%d/%Y')
        else:
            raise ValueError("Date is required")
        
        self.status = data.get('Status')
        self.duration = int(data.get('Duration', 0))
        self.educator_name = data.get('Name')
        self.educator_id = data.get('User Auth Id')
        self.school = data.get('School')
        self.district_partner = data.get('District or Company')
        self.registered_count = int(data.get('Registered Student Count', '0').replace('n/a', '0'))
        self.attended_count = int(data.get('Attended Student Count', '0').replace('n/a', '0'))
        self.type = EventType.VIRTUAL_SESSION