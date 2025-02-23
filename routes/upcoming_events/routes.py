from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
import simple_salesforce
from sqlalchemy import or_

from config import Config
from models import db
from models.upcoming_events import UpcomingEvent

upcoming_events_bp = Blueprint('upcoming_events', __name__)

@upcoming_events_bp.route('/sync_upcoming_events', methods=['POST'])
def sync_upcoming_events():
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Add logging for deletion
        print("Starting sync process...")
        
        deleted_count = UpcomingEvent.query.filter(
            or_(
                UpcomingEvent.start_date < yesterday,
                UpcomingEvent.available_slots <= 0
            )
        ).delete()
        db.session.commit()
        print(f"Deleted {deleted_count} past/filled events")

        # Salesforce connection
        print("Connecting to Salesforce...")
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # Query execution
        print("Executing Salesforce query...")
        query = """
            SELECT Id, Name, Available_slots__c, Filled_Volunteer_Jobs__c, 
                Date_and_Time_for_Cal__c, Session_Type__c, Registration_Link__c, 
                Display_on_Website__c, Start_Date__c 
                FROM Session__c 
                WHERE Start_Date__c > TODAY 
                AND Available_slots__c > 0
                ORDER BY Start_Date__c ASC
        """
        result = sf.query(query)
        events = result.get('records', [])
        print(f"Retrieved {len(events)} events from Salesforce")
        
        # Print first event for debugging
        if events:
            print("Sample event data:", events[0])

        # Update database
        print("Updating database...")
        new_count, updated_count = UpcomingEvent.upsert_from_salesforce(events)
        
        return jsonify({
            'success': True,
            'new_count': new_count,
            'updated_count': updated_count,
            'deleted_count': deleted_count,
            'message': f'Successfully synced: {new_count} new, {updated_count} updated, {deleted_count} removed'
        })

    except SalesforceAuthenticationFailed as e:
        print(f"Salesforce Authentication Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401

    except Exception as e:
        import traceback
        print(f"Sync Error: {str(e)}")
        print("Full traceback:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@upcoming_events_bp.route('/volunteer_signup')
def volunteer_signup():
    # Get initial events from database where display_on_website is True, ordered by date
    events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]
    return render_template('events/signup.html', initial_events=events)

@upcoming_events_bp.route('/volunteer_signup_api')
def volunteer_signup_api():
    # Get initial events from database where display_on_website is True, ordered by date
    events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]

    # Return JSON response directly
    return jsonify(events)

@upcoming_events_bp.route('/toggle-event-visibility', methods=['POST'])
@login_required
def toggle_event_visibility():
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        visible = data.get('visible')
        
        print(f"Toggling event {event_id} to visibility: {visible}")  # Debug log
        
        event = UpcomingEvent.query.filter_by(salesforce_id=event_id).first()
        if not event:
            print(f"Event not found with ID: {event_id}")  # Debug log
            return jsonify({
                'success': False,
                'message': 'Event not found'
            }), 404
        
        # Print before state
        print(f"Before update - Event {event_id} visibility: {event.display_on_website}")
        
        event.display_on_website = visible
        db.session.commit()
        
        # Verify the update
        db.session.refresh(event)
        print(f"After update - Event {event_id} visibility: {event.display_on_website}")
        
        return jsonify({
            'success': True,
            'message': f'Event visibility {"enabled" if visible else "disabled"}',
            'current_state': event.display_on_website
        })
        
    except Exception as e:
        print(f"Error in toggle_event_visibility: {str(e)}")  # Debug log
        db.session.rollback()  # Roll back on error
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@upcoming_events_bp.route('/upcoming_event_management')
@login_required
def upcoming_event_management():
    # Get initial events from database and convert to dict
    events = [event.to_dict() for event in UpcomingEvent.query.all()]
    return render_template('events/upcoming_event_management.html', initial_events=events)

@upcoming_events_bp.route('/dia_events_api')
def dia_events_api():
    try:
        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # Query for DIA events
        query = """
            SELECT Id, Name, Available_slots__c, Filled_Volunteer_Jobs__c, 
                Date_and_Time_for_Cal__c, Session_Type__c, Registration_Link__c, 
                Display_on_Website__c, Start_Date__c 
            FROM Session__c 
            WHERE Start_Date__c > TODAY 
            AND Session_Type__c = 'DIA - Classroom Speaker'
            AND Available_slots__c > 0
            ORDER BY Start_Date__c ASC
        """
        result = sf.query(query)
        events = result.get('records', [])

        # Return JSON response directly
        return jsonify(events)

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500
