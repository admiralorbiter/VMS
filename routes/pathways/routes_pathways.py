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
from simple_salesforce import SalesforceAuthenticationFailed

from models import db
from models.contact import Contact
from models.event import Event
from models.pathways import Pathway
from utils.salesforce_importer import ImportConfig, SalesforceImporter

pathways_bp = Blueprint("pathways", __name__, url_prefix="/pathways")


@pathways_bp.route("/import-from-salesforce", methods=["POST"])
@login_required
def import_pathways_from_salesforce():
    """
    Import pathway data and relationships from Salesforce (Optimized).

    Uses the standardized SalesforceImporter with batching, retries,
    validation, and progress reporting.
    """
    try:
        print("Starting optimized pathways import from Salesforce...")

        # Configure importer
        config = ImportConfig(
            batch_size=500,
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=10,
        )
        importer = SalesforceImporter(config)

        # Queries
        pathways_query = """
            SELECT Id, Name
            FROM Pathway__c
        """
        pathway_sessions_query = """
            SELECT Session__c, Pathway__c
            FROM Pathway_Session__c
        """

        # Caches
        pathway_cache: dict[str, Pathway | None] = {}
        event_cache: dict[str, Event | None] = {}

        created_count = 0
        updated_count = 0
        linked_count = 0
        missing_pathway = 0
        missing_event = 0

        def get_pathway_cached(sf_id: str, session):
            if sf_id in pathway_cache:
                return pathway_cache[sf_id]
            with session.no_autoflush:
                p = session.query(Pathway).filter_by(salesforce_id=sf_id).first()
            pathway_cache[sf_id] = p
            return p

        def get_event_cached(sf_id: str, session):
            if sf_id in event_cache:
                return event_cache[sf_id]
            with session.no_autoflush:
                ev = session.query(Event).filter_by(salesforce_id=sf_id).first()
            event_cache[sf_id] = ev
            return ev

        def validate_pathway_record(record: dict) -> list:
            return [] if record.get("Id") else ["Missing Pathway Id"]

        def process_pathway_record_optimized(record: dict, session) -> bool:
            nonlocal created_count, updated_count
            try:
                sf_id = record.get("Id")
                name = (record.get("Name") or "").strip()
                with session.no_autoflush:
                    pathway = session.query(Pathway).filter_by(salesforce_id=sf_id).first()
                if not pathway:
                    pathway = Pathway(salesforce_id=sf_id, name=name)
                    session.add(pathway)
                    created_count += 1
                else:
                    if pathway.name != name:
                        pathway.name = name
                    updated_count += 1
                pathway_cache[sf_id] = pathway
                return True
            except Exception as e:
                print(f"Error processing pathway {record.get('Id', 'unknown')}: {str(e)}")
                return False

        def validate_pathway_session_record(record: dict) -> list:
            errors = []
            if not record.get("Pathway__c"):
                errors.append("Missing Pathway__c")
            if not record.get("Session__c"):
                errors.append("Missing Session__c")
            return errors

        def process_pathway_session_record_optimized(record: dict, session) -> bool:
            nonlocal linked_count, missing_pathway, missing_event
            try:
                p = get_pathway_cached(record.get("Pathway__c"), session)
                if not p:
                    missing_pathway += 1
                    return False
                ev = get_event_cached(record.get("Session__c"), session)
                if not ev:
                    missing_event += 1
                    return False
                # link if not linked
                if ev not in p.events:
                    p.events.append(ev)
                    linked_count += 1
                return True
            except Exception as e:
                print(f"Error linking pathway-session: {str(e)}")
                return False

        def progress_callback(processed, total, message):
            if processed % 1000 == 0 and processed > 0:
                pct = (processed / max(total, 1)) * 100
                print(f"Progress: {processed:,}/{total:,} ({pct:.1f}%) - {message}")

        # Import pathways
        path_res = importer.import_data(
            query=pathways_query,
            process_func=process_pathway_record_optimized,
            validation_func=validate_pathway_record,
            progress_callback=progress_callback,
        )

        # Import relationships
        link_res = importer.import_data(
            query=pathway_sessions_query,
            process_func=process_pathway_session_record_optimized,
            validation_func=validate_pathway_session_record,
            progress_callback=None,
        )

        success = path_res.success and link_res.success
        message = (
            f"Pathways created {created_count:,}, updated {updated_count:,}; "
            f"Links created {linked_count:,}, missing pathways {missing_pathway:,}, missing events {missing_event:,}."
        )

        return jsonify(
            {
                "success": success,
                "message": message,
                "statistics": {
                    "pathways": {
                        "total_records": path_res.total_records,
                        "processed_count": path_res.processed_count,
                        "success_count": path_res.success_count,
                        "error_count": path_res.error_count,
                        "skipped_count": path_res.skipped_count,
                        "duration_seconds": path_res.duration_seconds,
                    },
                    "links": {
                        "total_records": link_res.total_records,
                        "processed_count": link_res.processed_count,
                        "success_count": link_res.success_count,
                        "error_count": link_res.error_count,
                        "skipped_count": link_res.skipped_count,
                        "duration_seconds": link_res.duration_seconds,
                        "created_count": linked_count,
                        "missing_pathway": missing_pathway,
                        "missing_event": missing_event,
                    },
                    "created_count": created_count,
                    "updated_count": updated_count,
                },
                "errors": (path_res.errors + link_res.errors)[:10],
                "warnings": (path_res.warnings + link_res.warnings)[:10],
            }
        )

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
    Import pathway participant relationships from Salesforce (Optimized).
    """
    try:
        print("Starting optimized pathway participants import from Salesforce...")

        config = ImportConfig(
            batch_size=500,
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=10,
        )
        importer = SalesforceImporter(config)

        participants_query = """
            SELECT Contact__c, Pathway__c
            FROM Pathway_Participant__c
        """

        # Caches
        pathway_cache: dict[str, Pathway | None] = {}
        contact_cache: dict[str, Contact | None] = {}
        created_links = 0
        missing_pathway = 0
        missing_contact = 0

        def get_pathway_cached(sf_id: str, session):
            if sf_id in pathway_cache:
                return pathway_cache[sf_id]
            with session.no_autoflush:
                p = session.query(Pathway).filter_by(salesforce_id=sf_id).first()
            pathway_cache[sf_id] = p
            return p

        def get_contact_cached(sf_id: str, session):
            if sf_id in contact_cache:
                return contact_cache[sf_id]
            with session.no_autoflush:
                c = session.query(Contact).filter_by(salesforce_individual_id=sf_id).first()
            contact_cache[sf_id] = c
            return c

        def validate_participant_record(record: dict) -> list:
            errors = []
            if not record.get("Pathway__c"):
                errors.append("Missing Pathway__c")
            if not record.get("Contact__c"):
                errors.append("Missing Contact__c")
            return errors

        def process_participant_record_optimized(record: dict, session) -> bool:
            nonlocal created_links, missing_pathway, missing_contact
            try:
                p = get_pathway_cached(record.get("Pathway__c"), session)
                if not p:
                    missing_pathway += 1
                    return False
                c = get_contact_cached(record.get("Contact__c"), session)
                if not c:
                    missing_contact += 1
                    return False
                if c not in p.contacts:
                    p.contacts.append(c)
                    created_links += 1
                return True
            except Exception as e:
                print(f"Error linking pathway participant: {str(e)}")
                return False

        def progress_callback(processed, total, message):
            if processed % 1000 == 0 and processed > 0:
                pct = (processed / max(total, 1)) * 100
                print(f"Progress: {processed:,}/{total:,} ({pct:.1f}%) - {message}")

        res = importer.import_data(
            query=participants_query,
            process_func=process_participant_record_optimized,
            validation_func=validate_participant_record,
            progress_callback=progress_callback,
        )

        return jsonify(
            {
                "success": res.success,
                "message": (
                    f"Links created {created_links:,}, Missing pathways {missing_pathway:,}, Missing contacts {missing_contact:,}, Errors {res.error_count:,}"
                ),
                "statistics": {
                    "total_records": res.total_records,
                    "processed_count": res.processed_count,
                    "success_count": res.success_count,
                    "error_count": res.error_count,
                    "skipped_count": res.skipped_count,
                    "duration_seconds": res.duration_seconds,
                    "created_links": created_links,
                    "missing_pathway": missing_pathway,
                    "missing_contact": missing_contact,
                },
                "errors": res.errors[:10],
                "warnings": res.warnings[:10],
            }
        )

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
