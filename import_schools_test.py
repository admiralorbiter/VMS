#!/usr/bin/env python3
"""
Test script to import schools from Salesforce
"""

from app import app
from models.district_model import District
from models.school_model import School
from routes.management.management import process_district_record, process_school_record, validate_district_record, validate_school_record
from utils.salesforce_importer import ImportConfig, SalesforceImporter


def test_import_schools():
    """Test importing schools from Salesforce"""
    with app.app_context():
        print("=== Before Import ===")
        print(f"Districts in database: {District.query.count()}")
        print(f"Schools in database: {School.query.count()}")

        print("\n=== Importing Schools ===")
        try:
            # Phase 1: Import Districts
            print("Starting district import process...")

            # Configure the district import with optimized settings
            district_config = ImportConfig(
                batch_size=300,  # Process 300 records at a time
                max_retries=3,
                retry_delay_seconds=5,
                validate_data=True,
                log_progress=True,
                commit_frequency=60,  # Commit every 60 records
            )

            # Initialize the Salesforce importer for districts
            district_importer = SalesforceImporter(district_config)

            # Define the district query
            district_query = """
            SELECT Id, Name, School_Code_External_ID__c
            FROM Account
            WHERE Type = 'School District'
            """

            # Execute the district import using the optimized framework
            district_result = district_importer.import_data(
                query=district_query, process_func=process_district_record, validation_func=validate_district_record
            )

            print(f"District import complete: {district_result.success_count} successes, {district_result.error_count} errors")

            # Phase 2: Import Schools
            print("Starting school import process...")

            # Configure the school import with optimized settings
            school_config = ImportConfig(
                batch_size=400,  # Process 400 records at a time
                max_retries=3,
                retry_delay_seconds=5,
                validate_data=True,
                log_progress=True,
                commit_frequency=80,  # Commit every 80 records
            )

            # Initialize the Salesforce importer for schools
            school_importer = SalesforceImporter(school_config)

            # Define the school query
            school_query = """
            SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c
            FROM Account
            WHERE Type = 'School'
            """

            # Execute the school import using the optimized framework
            school_result = school_importer.import_data(query=school_query, process_func=process_school_record, validation_func=validate_school_record)

            print(f"School import complete: {school_result.success_count} successes, {school_result.error_count} errors")

            print("\n=== After Import ===")
            print(f"Districts in database: {District.query.count()}")
            print(f"Schools in database: {School.query.count()}")

            # Show some sample schools
            schools = School.query.limit(5).all()
            print("\nSample schools:")
            for school in schools:
                print(f"  {school.id} - {school.name} (Level: {school.level})")

        except Exception as e:
            print(f"Error during import: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_import_schools()
