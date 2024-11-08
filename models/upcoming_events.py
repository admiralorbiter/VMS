from . import db
from datetime import datetime, timezone

class UpcomingEvent(db.Model):
    __tablename__ = 'upcoming_events'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False)  # Salesforce IDs are 18 chars
    name = db.Column(db.String(255), nullable=False)
    available_slots = db.Column(db.Integer)
    filled_volunteer_jobs = db.Column(db.Integer)
    date_and_time = db.Column(db.String(100))  # Storing as string since format is "MM/DD/YYYY HH:MM AM/PM to HH:MM AM/PM"
    event_type = db.Column(db.String(50))
    registration_link = db.Column(db.Text)
    display_on_website = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    start_date = db.Column(db.DateTime)

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

    @classmethod
    def upsert_from_salesforce(cls, sf_data):
        """
        Update or insert event data from Salesforce.
        Returns tuple of (new_records_count, updated_records_count)
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
                # Update existing record, preserving display_on_website
                for key, value in event_data.items():
                    setattr(existing, key, value)
                updated_count += 1
            else:
                # Create new record with display_on_website defaulting to False
                event_data['display_on_website'] = False
                new_event = cls(**event_data)
                db.session.add(new_event)
                new_count += 1
        
        db.session.commit()
        return (new_count, updated_count)
