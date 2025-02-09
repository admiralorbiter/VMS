from datetime import datetime
from enum import Enum
from flask import current_app
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
    db.Column('district_id', db.String(18), db.ForeignKey('district.id'), primary_key=True)
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
    total_attendance = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Change the relationship definition to prevent circular updates
    event = db.relationship('Event', 
                          backref=db.backref('attendance', 
                                           uselist=False,
                                           cascade='all, delete-orphan'),
                          single_parent=True)

class EventFormat(str, Enum):
    IN_PERSON = 'in_person'
    VIRTUAL = 'virtual'

class EventStatus(str, Enum):
    DRAFT = 'Draft'
    PUBLISHED = 'Published'
    CANCELLED = 'Cancelled'
    COMPLETED = 'Completed'
    EMERGENCY_CANCELLATION = 'Emergency Cancellation'
    REQUESTED = 'Requested'
    CONFIRMED = 'Confirmed'

class Event(db.Model):
    __tablename__ = 'event'

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
    volunteers_needed = db.Column(db.Integer)
    format = db.Column(SQLAlchemyEnum(EventFormat), nullable=False, default=EventFormat.IN_PERSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    participant_count = db.Column(db.Integer, default=0)
    additional_information = db.Column(db.Text)
    session_id = db.Column(db.String(255))
    series = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    registered_count = db.Column(db.Integer, default=0)
    attended_count = db.Column(db.Integer, default=0)
    educators = db.Column(db.Text)
    educator_ids = db.Column(db.Text)
    school = db.Column(db.Text)
    district_partner = db.Column(db.Text)
    professionals = db.Column(db.Text)
    professional_ids = db.Column(db.Text)
    available_slots = db.Column(db.Integer, default=0)  # Available_Slots__c
    registration_link = db.Column(db.String(1300))  # Registration_Link__c
    scheduled_participants_count = db.Column(db.Integer, default=0)  # Scheduled_Participants_Count__c
    total_requested_volunteer_jobs = db.Column(db.Integer, default=0)  # Total_Requested_Volunteer_Jobs__c
    
    # Emergency cancellation fields
    emergency_status = db.Column(db.Boolean, default=False)
    emergency_declared_at = db.Column(db.DateTime, nullable=True)
    emergency_declared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    emergency_declared_by = db.relationship('User', foreign_keys=[emergency_declared_by_id])
    
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

    def merge_duplicate(self, data):
        """Merge data from a duplicate event's CSV row"""
        # Combine counts
        new_registered = int(data.get('Registered Student Count', '0').replace('n/a', '0'))
        new_attended = int(data.get('Attended Student Count', '0').replace('n/a', '0'))
        self.registered_count += new_registered
        self.attended_count += new_attended

        # Handle role-specific data
        role = data.get('SignUp Role', '').strip().lower()
        name = data.get('Name', '').strip()
        user_id = data.get('User Auth Id', '').strip()
        company = data.get('District or Company', '').strip()

        if name and role:
            if role == 'educator':
                current_educators = set(filter(None, (self.educators or '').split('; ')))
                current_educator_ids = set(filter(None, (self.educator_ids or '').split('; ')))
                
                if name:
                    current_educators.add(name)
                    self.educators = '; '.join(sorted(current_educators))
                if user_id:
                    current_educator_ids.add(user_id)
                    self.educator_ids = '; '.join(sorted(current_educator_ids))
                    
            elif role == 'professional':
                # Split name into first and last
                name_parts = name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                # Try to find existing volunteer
                from models.volunteer import Volunteer, db
                volunteer = Volunteer.query.filter(
                    Volunteer.first_name == first_name,
                    Volunteer.last_name == last_name
                ).first()

                if not volunteer:
                    # Create new volunteer with empty middle name
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=''  # Explicitly set empty string
                    )
                    db.session.add(volunteer)
                    
                    # Create or get organization if company provided
                    if company:
                        from models.organization import Organization, VolunteerOrganization
                        org = Organization.query.filter_by(name=company).first()
                        if not org:
                            org = Organization(name=company)
                            db.session.add(org)
                            db.session.flush()
                        
                        # Link volunteer to organization
                        vol_org = VolunteerOrganization(
                            volunteer=volunteer,
                            organization=org,
                            role='Professional',
                            is_primary=True
                        )
                        db.session.add(vol_org)

                # Link volunteer to event if not already linked
                if volunteer not in self.volunteers:
                    self.volunteers.append(volunteer)

    def update_from_csv(self, data):
        """Update event from CSV data"""
        # Validate required fields
        if not data.get('Date'):
            raise ValueError("Date is required")
        if not data.get('Title'):
            raise ValueError("Title is required")
        
        date_str = data.get('Date')
        if not date_str:
            raise ValueError("Date is required")

        self.session_id = data.get('Session ID')
        self.title = data.get('Title')
        self.series = data.get('Series or Event Title')
        self.start_date = datetime.strptime(date_str, '%m/%d/%Y')
        self.status = data.get('Status')
        self.duration = int(data.get('Duration', 0))
        self.school = data.get('School')
        self.district_partner = data.get('District or Company')
        self.registered_count = int(data.get('Registered Student Count', '0').replace('n/a', '0'))
        self.attended_count = int(data.get('Attended Student Count', '0').replace('n/a', '0'))
        
        # Add handling for volunteers_needed
        if data.get('Volunteers Needed'):
            self.volunteers_needed = int(data.get('Volunteers Needed', '0'))
        
        self.type = EventType.VIRTUAL_SESSION

        # Handle role-specific data
        role = data.get('SignUp Role', '').strip().lower()
        name = data.get('Name', '').strip()
        user_id = data.get('User Auth Id', '').strip()
        company = data.get('District or Company', '').strip()

        if name and role:
            if role == 'educator':
                self.educators = name
                self.educator_ids = user_id if user_id else ''
            elif role == 'professional':
                # Split name into first and last
                name_parts = name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                # Try to find existing volunteer
                from models.volunteer import Volunteer, db
                volunteer = Volunteer.query.filter(
                    Volunteer.first_name == first_name,
                    Volunteer.last_name == last_name
                ).first()

                if not volunteer:
                    # Create new volunteer with empty middle name
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=''  # Explicitly set empty string
                    )
                    db.session.add(volunteer)
                    
                    # Create or get organization if company provided
                    if company:
                        from models.organization import Organization, VolunteerOrganization
                        org = Organization.query.filter_by(name=company).first()
                        if not org:
                            org = Organization(name=company)
                            db.session.add(org)
                            db.session.flush()
                        
                        # Link volunteer to organization
                        vol_org = VolunteerOrganization(
                            volunteer=volunteer,
                            organization=org,
                            role='Professional',
                            is_primary=True
                        )
                        db.session.add(vol_org)

                # Link volunteer to event
                self.volunteers.append(volunteer)