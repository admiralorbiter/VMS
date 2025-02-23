from . import db
from datetime import datetime, timezone
from sqlalchemy.orm import validates
import re

class UpcomingEvent(db.Model):
    """
    Represents an upcoming event synchronized from Salesforce.
    Handles the display of events on the website and tracks volunteer registration status.
    """
    
    __tablename__ = 'upcoming_events'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False)  # Salesforce IDs are 18 chars
    name = db.Column(db.String(255), nullable=False)
    available_slots = db.Column(db.Integer)
    filled_volunteer_jobs = db.Column(db.Integer)
    date_and_time = db.Column(db.String(100))  # Storing as string since format is "MM/DD/YYYY HH:MM AM/PM to HH:MM AM/PM"
    event_type = db.Column(db.String(50), index=True)
    registration_link = db.Column(db.Text)
    display_on_website = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    start_date = db.Column(db.DateTime, index=True)
    status = db.Column(db.String(20), default='active')

    def to_dict(self):
        """Convert event to dictionary for JSON serialization"""
        return {
            'Id': self.salesforce_id,  # Match Salesforce API format
            'Name': self.name,
            'Available_Slots__c': self.available_slots,
            'Filled_Volunteer_Jobs__c': self.filled_volunteer_jobs,
            'Date_and_Time_for_Cal__c': self.date_and_time,
            'Session_Type__c': self.event_type,
            'Registration_Link__c': self.registration_link,
            'Display_on_Website__c': self.display_on_website,
            'Start_Date__c': self.start_date.isoformat() if self.start_date else None
        }

    @validates('available_slots', 'filled_volunteer_jobs')
    def validate_slots(self, key, value):
        """Ensure slot counts are non-negative integers"""
        if value is not None:
            try:
                # Handle string or float inputs from Salesforce
                value = int(float(str(value)))
                if value < 0:
                    raise ValueError(f"{key} cannot be negative")
            except (ValueError, TypeError):
                raise ValueError(f"{key} must be a valid number")
        return value

    @validates('registration_link')
    def validate_url(self, key, value):
        """
        Validate and extract URL from registration link.
        Handles both raw URLs and HTML anchor tags.
        """
        if not value:
            return value
        
        # If it's an HTML anchor tag, extract the href
        if value.startswith('<a') and 'href=' in value:
            href_match = re.search(r'href=[\'"]?([^\'" >]+)', value)
            if href_match:
                value = href_match.group(1)
        
        # Validate the URL
        if not value.startswith(('http://', 'https://')):
            raise ValueError("Registration link must be a valid URL")
        
        return value

    @classmethod
    def upsert_from_salesforce(cls, sf_data):
        """
        Update or insert event data from Salesforce.
        
        Args:
            sf_data (list): List of dictionaries containing Salesforce event data
            
        Returns:
            tuple: (new_records_count, updated_records_count)
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        new_count = 0
        updated_count = 0
        
        for record in sf_data:
            existing = cls.query.filter_by(salesforce_id=record['Id']).first()
            
            # Parse the start date string into a datetime object
            start_date = None
            if record['Start_Date__c']:
                try:
                    start_date = datetime.strptime(record['Start_Date__c'], '%Y-%m-%d')
                except ValueError:
                    # Handle any date parsing errors
                    print(f"Warning: Could not parse date {record['Start_Date__c']} for session {record['Id']}")
            
            event_data = {
                'salesforce_id': record['Id'],
                'name': record['Name'],
                'available_slots': int(record['Available_Slots__c'] or 0),
                'filled_volunteer_jobs': int(record['Filled_Volunteer_Jobs__c'] or 0),
                'date_and_time': record['Date_and_Time_for_Cal__c'],
                'event_type': record['Session_Type__c'],
                'registration_link': record['Registration_Link__c'],
                'start_date': start_date
            }
            
            if existing:
                # Don't include display_on_website in the update
                for key, value in event_data.items():
                    setattr(existing, key, value)
                # Explicitly preserve display_on_website
                # existing.display_on_website = existing.display_on_website  # This line isn't necessary but shows intent
                updated_count += 1
            else:
                # Only set display_on_website for new records
                if record['Display_on_Website__c'] == 'Yes':
                    event_data['display_on_website'] = True
                else:
                    event_data['display_on_website'] = False
                new_event = cls(**event_data)
                db.session.add(new_event)
                new_count += 1
        
        db.session.commit()
        return (new_count, updated_count)
