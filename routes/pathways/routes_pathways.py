"""
Pathways Routes Module
=====================

This module provides functionality for managing educational pathways
in the Volunteer Management System (VMS). It handles Salesforce integration
for importing pathway data, events, and participant relationships.

Key Features:
- Salesforce pathway data import
- Pathway-event relationship management
- Pathway-participant relationship management
- Error handling and reporting
- Database synchronization

Main Endpoints:
- /pathways/import-from-salesforce: Import pathway data and relationships (POST)
- /pathways/import-participants-from-salesforce: Import pathway participants (POST)

Salesforce Integration:
- Pathway__c object synchronization
- Pathway_Session__c relationship management
- Pathway_Participant__c participant tracking
- Authentication and error handling
- Batch processing with rollback support

Data Synchronization:
- Creates new pathways from Salesforce
- Updates existing pathway information
- Manages pathway-event relationships
- Tracks pathway-participant associations
- Provides detailed import statistics

Error Handling:
- Salesforce authentication failures
- Missing relationship data
- Database transaction rollback
- Detailed error reporting
- Success/error count tracking

Dependencies:
- Flask Blueprint for routing
- Salesforce API integration
- Pathway, Event, and Contact models
- Database session management
- Configuration settings

Models Used:
- Pathway: Educational pathway data
- Event: Event data for pathway relationships
- Contact: Participant contact information
- Database session for persistence

Security Features:
- Login required for all operations
- Salesforce authentication validation
- Database transaction safety
- Error logging and reporting
"""

from flask import Blueprint, jsonify
from flask_login import login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

from config import Config
from models import db
from models.contact import Contact
from models.event import Event
from models.pathways import Pathway

pathways_bp = Blueprint("pathways", __name__, url_prefix="/pathways")


@pathways_bp.route("/import-from-salesforce", methods=["POST"])
@login_required
def import_pathways_from_salesforce():
    """
    Import pathway data and relationships from Salesforce.

    Fetches pathway information and pathway-session relationships from
    Salesforce and synchronizes them with the local database. Handles
    both creation of new pathways and updates to existing ones.

    Salesforce Objects:
        - Pathway__c: Main pathway data
        - Pathway_Session__c: Pathway-event relationships

    Process Flow:
        1. Authenticate with Salesforce
        2. Query Pathway__c objects
        3. Create/update pathway records
        4. Query Pathway_Session__c relationships
        5. Link pathways to events
        6. Commit all changes

    Error Handling:
        - Salesforce authentication failures
        - Missing pathway or event data
        - Database transaction rollback
        - Detailed error reporting

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        500: Database or server error
    """
    try:
        print("Fetching pathway data from Salesforce...")
        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce
        sf = Salesforce(username=Config.SF_USERNAME, password=Config.SF_PASSWORD, security_token=Config.SF_SECURITY_TOKEN, domain="login")

        # Query pathways from Salesforce
        pathways_query = """
        SELECT Id, Name
        FROM Pathway__c
        """

        # Execute pathway query
        pathways_result = sf.query_all(pathways_query)
        pathway_rows = pathways_result.get("records", [])

        # Process pathways
        for row in pathway_rows:
            try:
                # Check if pathway already exists
                pathway = Pathway.query.filter_by(salesforce_id=row["Id"]).first()

                if pathway:
                    # Update existing pathway
                    pathway.name = row["Name"]
                else:
                    # Create new pathway
                    pathway = Pathway(salesforce_id=row["Id"], name=row["Name"])
                    db.session.add(pathway)

                success_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"Error processing pathway {row.get('Name', 'Unknown')}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)

        # Commit pathways
        db.session.commit()

        # Now query the Pathway_Session__c relationships
        pathway_sessions_query = """
        SELECT Session__c, Pathway__c
        FROM Pathway_Session__c
        """

        pathway_sessions_result = sf.query_all(pathway_sessions_query)
        pathway_session_rows = pathway_sessions_result.get("records", [])

        # Process pathway-session relationships
        for row in pathway_session_rows:
            try:
                pathway = Pathway.query.filter_by(salesforce_id=row["Pathway__c"]).first()
                event = Event.query.filter_by(salesforce_id=row["Session__c"]).first()

                if pathway and event:
                    # Add event to pathway's events if not already present
                    if event not in pathway.events:
                        pathway.events.append(event)
                else:
                    error_msg = (
                        f"Could not find {'pathway' if not pathway else 'event'} for relationship: Pathway={row['Pathway__c']}, Session={row['Session__c']}"
                    )
                    errors.append(error_msg)
                    print(error_msg)
                    error_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"Error processing pathway-session relationship: {str(e)}"
                errors.append(error_msg)
                print(error_msg)

        # Commit relationships
        db.session.commit()

        # Print summary
        print(f"\nSuccessfully processed {success_count} pathways with {error_count} errors")
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")

        return jsonify({"success": True, "message": f"Successfully processed {success_count} pathways with {error_count} errors", "errors": errors})

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@pathways_bp.route("/import-participants-from-salesforce", methods=["POST"])
@login_required
def import_pathway_participants_from_salesforce():
    """
    Import pathway participant relationships from Salesforce.

    Fetches pathway-participant relationships from Salesforce and
    synchronizes them with the local database. Links contacts to
    pathways for participant tracking.

    Salesforce Objects:
        - Pathway_Participant__c: Pathway-participant relationships

    Process Flow:
        1. Authenticate with Salesforce
        2. Query Pathway_Participant__c objects
        3. Link contacts to pathways
        4. Commit all changes
        5. Report import statistics

    Error Handling:
        - Salesforce authentication failures
        - Missing pathway or contact data
        - Database transaction rollback
        - Detailed error reporting

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        500: Database or server error
    """
    try:
        print("Fetching pathway participant data from Salesforce...")
        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce
        sf = Salesforce(username=Config.SF_USERNAME, password=Config.SF_PASSWORD, security_token=Config.SF_SECURITY_TOKEN, domain="login")

        # Query pathway participants from Salesforce
        pathway_participants_query = """
        SELECT Contact__c, Pathway__c
        FROM Pathway_Participant__c
        """

        participants_result = sf.query_all(pathway_participants_query)
        participant_rows = participants_result.get("records", [])

        # Process pathway-participant relationships
        for row in participant_rows:
            try:
                pathway = Pathway.query.filter_by(salesforce_id=row["Pathway__c"]).first()
                contact = Contact.query.filter_by(salesforce_individual_id=row["Contact__c"]).first()

                if pathway and contact:
                    # Add contact to pathway's contacts if not already present
                    if contact not in pathway.contacts:
                        pathway.contacts.append(contact)
                        success_count += 1
                else:
                    error_msg = (
                        f"Could not find {'pathway' if not pathway else 'contact'} for relationship: Pathway={row['Pathway__c']}, Contact={row['Contact__c']}"
                    )
                    errors.append(error_msg)
                    print(error_msg)
                    error_count += 1

            except Exception as e:
                error_count += 1
                error_msg = f"Error processing pathway-participant relationship: {str(e)}"
                errors.append(error_msg)
                print(error_msg)

        # Commit all changes
        db.session.commit()

        # Print summary
        print(f"\nSuccessfully processed {success_count} pathway participants with {error_count} errors")
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")

        return jsonify({"success": True, "message": f"Successfully processed {success_count} pathway participants with {error_count} errors", "errors": errors})

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
