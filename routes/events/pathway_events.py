from flask import Blueprint, jsonify
from flask_login import login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy.orm import joinedload, selectinload
from datetime import datetime # Add datetime

from config import Config
from models import db
from models.event import Event, EventType, EventFormat, EventStatus, CancellationReason # Add Enums
from models.student import Student
from models.school_model import School # Assuming School model is here
from models.district_model import District # Assuming District model is here
from models.volunteer import Skill, EventParticipation, Volunteer # Need Skill for parsing and volunteer participation
# Import helpers from routes.utils
from routes.utils import map_session_type, map_event_format, parse_date, map_cancellation_reason, parse_event_skills, DISTRICT_MAPPINGS
# Import the process_participation_row function from the events routes
from routes.events.routes import process_participation_row
# Adjust imports based on your actual model locations if needed

pathway_events_bp = Blueprint('pathway_events', __name__, url_prefix='/pathway-events')

def _create_event_from_salesforce(sf_event_data, event_districts):
    """
    Creates and returns a new Event object from Salesforce data,
    assigning the provided districts. Does not commit.
    """
    event_sf_id = sf_event_data.get('Id')
    if not event_sf_id:
        raise ValueError("Salesforce event data missing 'Id'")

    new_event = Event(
        salesforce_id=event_sf_id,
        title=sf_event_data.get('Name', '').strip() or f"Untitled Event {event_sf_id}" # Ensure title is not empty
    )

    # Map fields (similar to process_event_row)
    new_event.type = map_session_type(sf_event_data.get('Session_Type__c', ''))
    new_event.format = map_event_format(sf_event_data.get('Format__c', ''))
    new_event.start_date = parse_date(sf_event_data.get('Start_Date_and_Time__c')) or datetime(2000, 1, 1)
    new_event.end_date = parse_date(sf_event_data.get('End_Date_and_Time__c')) or datetime(2000, 1, 1)
    # Ensure status uses the enum value if applicable, otherwise the string
    raw_status = sf_event_data.get('Session_Status__c')
    try:
        new_event.status = EventStatus(raw_status) if raw_status else EventStatus.DRAFT
    except ValueError:
        # If raw_status doesn't match an enum value, store the raw string or default
        # This might depend on how Event.status column handles non-enum values
        # Let's default to DRAFT if mapping fails for safety
        print(f"Warning: Unknown status '{raw_status}' for event {event_sf_id}. Defaulting to DRAFT.")
        new_event.status = EventStatus.DRAFT

    new_event.location = sf_event_data.get('Location_Information__c', '')
    new_event.description = sf_event_data.get('Description__c', '')
    new_event.cancellation_reason = map_cancellation_reason(sf_event_data.get('Cancellation_Reason__c'))
    new_event.participant_count = int(float(sf_event_data.get('Non_Scheduled_Students_Count__c', 0)) if sf_event_data.get('Non_Scheduled_Students_Count__c') is not None else 0)
    new_event.additional_information = sf_event_data.get('Additional_Information__c', '')

    def safe_convert_to_int(value, default=0):
         if value is None: return default
         try: return int(float(value))
         except (ValueError, TypeError): return default

    new_event.total_requested_volunteer_jobs = safe_convert_to_int(sf_event_data.get('Total_Requested_Volunteer_Jobs__c'))
    new_event.available_slots = safe_convert_to_int(sf_event_data.get('Available_Slots__c'))

    # Assign the districts determined from students
    # The input event_districts should already be a set of District objects
    new_event.districts = list(event_districts)

    # Handle Skills (Uncommented and using logic from process_event_row)
    skills_covered = parse_event_skills(sf_event_data.get('Legacy_Skill_Covered_for_the_Session__c', ''))
    skills_needed = parse_event_skills(sf_event_data.get('Legacy_Skills_Needed__c', ''))
    requested_skills = parse_event_skills(sf_event_data.get('Requested_Skills__c', ''))
    all_skill_names = set(skills_covered + skills_needed + requested_skills)

    for skill_name in all_skill_names:
        # Use get_or_create pattern for skills to avoid race conditions if run concurrently (though unlikely here)
        # This requires querying within the loop, which is acceptable for a smaller number of skills per event.
        skill = db.session.query(Skill).filter(Skill.name == skill_name).first()
        if not skill:
            skill = Skill(name=skill_name)
            db.session.add(skill)
            # We might need to flush here if Skill has relationships needed immediately,
            # but let's try without it first.
            # db.session.flush()
        # Ensure the skill object is added to the event's skill list
        # Note: event.skills is likely an InstrumentedList, append handles the association
        if skill not in new_event.skills:
             new_event.skills.append(skill)

    # Important: This helper *does not* add the event to the session or flush/commit.
    # The calling function is responsible for that.
    return new_event

@pathway_events_bp.route('/sync-unaffiliated-events', methods=['POST'])
@login_required
def sync_unaffiliated_events():
    """
    Fetches events from Salesforce that are missing School, District, and Parent Account.
    Attempts to associate these events with districts based on the districts of
    participating students found in the local database.
    Also syncs volunteer participation for these events.
    """
    processed_count = 0
    updated_count = 0
    errors = []
    district_map_details = {} # To store event_sf_id -> list of district names

    try:
        print("Connecting to Salesforce...")
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login' # Use 'test' for sandbox if needed
        )
        print("Connected to Salesforce.")

        # 1. Query for *all* student participants first
        # Consider adding a date filter if this table is extremely large
        # e.g., WHERE CreatedDate >= LAST_N_MONTHS:24
        all_participants_query = """
        SELECT Session__c, Contact__c
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Student' AND Contact__c != NULL
        """
        print("Querying ALL student participants from Salesforce...")
        all_participants_result = sf.query_all(all_participants_query)
        all_participant_rows = all_participants_result.get('records', [])
        print(f"Found {len(all_participant_rows)} total student participation records.")

        # Build a map of Event SF ID -> Set of Student Contact SF IDs
        event_to_student_sf_ids = {}
        for row in all_participant_rows:
            event_id = row['Session__c']
            student_contact_id = row['Contact__c']
            # We already filter Contact__c != NULL in the query, but double-check
            if event_id and student_contact_id:
                if event_id not in event_to_student_sf_ids:
                    event_to_student_sf_ids[event_id] = set()
                event_to_student_sf_ids[event_id].add(student_contact_id)
        print(f"Built participation map for {len(event_to_student_sf_ids)} events.")


        # 2. Query for unaffiliated events in Salesforce (FETCH FULL DETAILS)
        # Copy fields from routes/events/routes.py import query
        unaffiliated_events_query = """
        SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c,
               End_Date_and_Time__c, Session_Status__c, Location_Information__c,
               Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c,
               District__c, School__c, Legacy_Skill_Covered_for_the_Session__c,
               Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
               Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c
        FROM Session__c
        WHERE School__c = NULL AND District__c = NULL AND Parent_Account__c = NULL
        ORDER BY CreatedDate DESC
        """
        print("Querying unaffiliated events (full details) from Salesforce...")
        events_result = sf.query_all(unaffiliated_events_query)
        unaffiliated_events_data = events_result.get('records', []) # Rename variable
        print(f"Found {len(unaffiliated_events_data)} potentially unaffiliated events in Salesforce.")

        if not unaffiliated_events_data:
            return jsonify({
                'success': True,
                'message': 'No unaffiliated events found in Salesforce matching the criteria.',
                'processed_count': 0,
                'updated_count': 0,
                'errors': []
            })

        # 3. Process each unaffiliated event found in Salesforce
        created_count = 0 # Add counter for new events
        # Rename loop variable for clarity
        for sf_event_data in unaffiliated_events_data:
            event_sf_id = sf_event_data['Id']
            processed_count += 1
            event_processed_or_skipped = False # Flag to ensure we don't double-process

            try:
                # Check if event already exists locally
                local_event = db.session.query(Event).filter(Event.salesforce_id == event_sf_id).first()

                # --- Logic if Event ALREADY Exists Locally (Unlikely, but handled) ---
                if local_event:
                    event_processed_or_skipped = True
                    # Check if it already has districts assigned locally
                    if not local_event.districts:
                        # Look up student participants in the map we built
                        student_sf_ids = event_to_student_sf_ids.get(event_sf_id)
                        if student_sf_ids:
                            # Find local students and districts (reuse logic from previous version)
                            local_students = db.session.query(Student).options(
                                selectinload(Student.school).selectinload(School.district)
                            ).filter(
                                Student.salesforce_individual_id.in_(student_sf_ids)
                            ).all()

                            event_districts = set()
                            if local_students:
                                for student in local_students:
                                    if student.school and student.school.district:
                                        event_districts.add(student.school.district)

                            if event_districts:
                                # Update existing event's districts
                                local_event.districts = list(event_districts) # Assign the list directly
                                db.session.add(local_event)
                                updated_count += 1
                                district_map_details[event_sf_id] = [d.name for d in event_districts]
                                print(f"UPDATED existing Event {event_sf_id} ({local_event.title}) with districts: {[d.name for d in event_districts]}")
                            # else: errors.append(f"Existing event {event_sf_id} - found students but no districts.")
                        # else: errors.append(f"Existing event {event_sf_id} - no students found in map.")
                    # else: print(f"Existing event {event_sf_id} already has districts. Skipping update.")
                    continue # Move to next Salesforce event

                # --- Logic if Event DOES NOT Exist Locally (Expected case) ---
                if not local_event:
                    # Look up student participants in the map we built
                    student_sf_ids = event_to_student_sf_ids.get(event_sf_id)
                    if not student_sf_ids:
                        # errors.append(f"New event {event_sf_id} - no students found in map. Cannot create/affiliate.")
                        event_processed_or_skipped = True
                        continue # Skip event if no participants were mapped

                    # Find local students and determine districts
                    local_students = db.session.query(Student).options(
                        selectinload(Student.school).selectinload(School.district)
                    ).filter(
                        Student.salesforce_individual_id.in_(student_sf_ids)
                    ).all()

                    event_districts = set()
                    if local_students:
                        for student in local_students:
                            if student.school and student.school.district:
                                event_districts.add(student.school.district)

                    if not event_districts:
                        errors.append(f"New event {event_sf_id} - found students (SF IDs: {', '.join(student_sf_ids)}) but cannot determine districts. Event not created.")
                        event_processed_or_skipped = True
                        continue # Skip event if districts can't be determined

                    # *** Create New Event ***
                    # Use a helper or adapt logic from process_event_row
                    # For simplicity here, basic creation:
                    # Import necessary helpers/enums at the top of the file:
                    # from routes.utils import map_session_type, map_event_format, parse_date, map_cancellation_reason, parse_event_skills
                    # from models.event import EventType, EventFormat, EventStatus, CancellationReason # Add Enums
                    # from datetime import datetime # Add datetime

                    # (Make sure the necessary functions/enums are imported at the top)
                    from routes.utils import map_session_type, map_event_format, parse_date, map_cancellation_reason, parse_event_skills, DISTRICT_MAPPINGS
                    from models.event import EventType, EventFormat, EventStatus, CancellationReason
                    from models.volunteer import Skill # Need Skill for parsing
                    from datetime import datetime

                    try:
                        new_event = _create_event_from_salesforce(sf_event_data, event_districts)

                        db.session.add(new_event)
                        db.session.flush() # Flush to catch potential validation errors early

                        created_count += 1
                        district_map_details[event_sf_id] = [d.name for d in event_districts]
                        print(f"CREATED new Event {event_sf_id} ({new_event.title}) affiliated with districts: {[d.name for d in event_districts]}")
                        event_processed_or_skipped = True

                    except Exception as creation_error:
                        db.session.rollback()
                        error_msg = f"Error CREATING event {event_sf_id}: {str(creation_error)}"
                        print(error_msg)
                        errors.append(error_msg)
                        event_processed_or_skipped = True


            except Exception as e:
                # Catch errors during the processing of a single event
                db.session.rollback()
                error_msg = f"Outer error processing event {event_sf_id}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)

            # Safety check - if event wasn't processed or skipped, log it
            # if not event_processed_or_skipped:
            #    errors.append(f"Event {event_sf_id} finished loop without being processed or explicitly skipped.")


        # NEW: After processing events, sync volunteer participants for the created/updated events
        print("Syncing volunteer participants for processed events...")
        
        # Get the Salesforce IDs of events we just processed
        processed_event_sf_ids = list(district_map_details.keys())
        
        participant_success = 0
        participant_error = 0
        
        if processed_event_sf_ids:
            # Query for volunteer participants for these specific events
            participants_query = f"""
            SELECT 
                Id,
                Name,
                Contact__c,
                Session__c,
                Status__c,
                Delivery_Hours__c,
                Age_Group__c,
                Email__c,
                Title__c
            FROM Session_Participant__c
            WHERE Participant_Type__c = 'Volunteer' 
            AND Session__c IN ({','.join([f"'{sf_id}'" for sf_id in processed_event_sf_ids])})
            """

            # Execute participants query
            participants_result = sf.query_all(participants_query)
            participant_rows = participants_result.get('records', [])

            print(f"Found {len(participant_rows)} volunteer participation records for processed events.")

            # Process volunteer participants using the existing function
            for row in participant_rows:
                participant_success, participant_error = process_participation_row(
                    row, participant_success, participant_error, errors
                )

            print(f"Successfully processed {participant_success} volunteer participations with {participant_error} errors")

        # Commit all changes
        db.session.commit()
        print("Database changes committed.")

        return jsonify({
            'success': True,
            'message': f'Processed {processed_count} unaffiliated events. Created: {created_count}, Updated: {updated_count}. Volunteer participations: {participant_success}.',
            'processed_count': processed_count,
            'created_count': created_count,
            'updated_count': updated_count,
            'volunteer_participations': participant_success,
            'district_map_details': district_map_details,
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        db.session.rollback()
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce.',
            'error': 'Salesforce Authentication Failed'
        }), 401
    except Exception as e:
        db.session.rollback()
        error_msg = f"An unexpected error occurred: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An internal server error occurred during the sync process. Please check server logs.'
        }), 500
