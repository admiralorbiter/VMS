import os
import sqlite3
import sys
import time

# Add the parent directory to the path so we can import the app and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app import app
from models import db

OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")


def copy_students_fast():
    """
    Fast bulk copy of student data using optimized database operations.
    """
    with app.app_context():
        print("Starting fast student migration...")
        start_time = time.time()

        # Connect to both databases
        old_conn = sqlite3.connect(OLD_DB_PATH)
        old_conn.row_factory = sqlite3.Row
        new_conn = sqlite3.connect(NEW_DB_PATH)

        try:
            # Get existing student IDs to avoid duplicates
            print("Checking for existing students...")
            existing_students = set()
            existing_result = db.session.execute(text("SELECT id FROM student")).fetchall()
            existing_students = {row[0] for row in existing_result}
            print(f"Found {len(existing_students)} existing students in target database")

            # Get all student data with contact info in one query
            print("Fetching student data from old database...")
            query = """
            SELECT
                s.id, s.active, s.current_grade, s.legacy_grade, s.student_id,
                s.school_id, s.class_salesforce_id, s.teacher_id, s.racial_ethnic,
                s.school_code, s.ell_language, s.gifted, s.lunch_status,
                c.type, c.salesforce_individual_id, c.salesforce_account_id,
                c.salutation, c.first_name, c.middle_name, c.last_name, c.suffix,
                c.description, c.age_group, c.education_level, c.birthdate,
                c.gender, c.race_ethnicity, c.do_not_call, c.do_not_contact,
                c.email_opt_out, c.email_bounced_date, c.exclude_from_reports,
                c.last_email_date, c.notes
            FROM student s
            INNER JOIN contact c ON s.id = c.id
            WHERE c.first_name IS NOT NULL
            AND c.last_name IS NOT NULL
            AND c.first_name != ''
            AND c.last_name != ''
            ORDER BY s.id
            """

            old_cursor = old_conn.cursor()
            old_cursor.execute(query)

            # Process in chunks for better memory management
            chunk_size = 1000
            total_processed = 0
            total_copied = 0
            total_skipped = 0

            print("Processing student records in chunks...")

            while True:
                rows = old_cursor.fetchmany(chunk_size)
                if not rows:
                    break

                chunk_start_time = time.time()

                # Filter out existing students
                new_students = []
                for row in rows:
                    if row["id"] not in existing_students:
                        new_students.append(dict(row))
                    else:
                        total_skipped += 1

                if new_students:
                    # Bulk insert using raw SQL for speed
                    contact_values = []
                    student_values = []

                    for student_data in new_students:
                        # Prepare contact data
                        contact_values.append(
                            (
                                student_data["id"],
                                "student",  # type
                                student_data.get("salesforce_individual_id"),
                                student_data.get("salesforce_account_id"),
                                student_data.get("salutation"),
                                student_data["first_name"],
                                student_data.get("middle_name"),
                                student_data["last_name"],
                                student_data.get("suffix"),
                                student_data.get("description"),
                                student_data.get("age_group", "UNKNOWN"),
                                student_data.get("education_level", "UNKNOWN"),
                                student_data.get("birthdate"),
                                student_data.get("gender"),
                                student_data.get("race_ethnicity"),
                                bool(student_data.get("do_not_call", 0)),
                                bool(student_data.get("do_not_contact", 0)),
                                bool(student_data.get("email_opt_out", 0)),
                                student_data.get("email_bounced_date"),
                                bool(student_data.get("exclude_from_reports", 0)),
                                student_data.get("last_email_date"),
                                student_data.get("notes"),
                            )
                        )

                        # Prepare student data
                        student_values.append(
                            (
                                student_data["id"],
                                bool(student_data.get("active", 1)),
                                student_data.get("current_grade"),
                                student_data.get("legacy_grade"),
                                student_data.get("student_id"),
                                student_data.get("school_id"),
                                student_data.get("class_salesforce_id"),
                                student_data.get("teacher_id"),
                                student_data.get("racial_ethnic"),
                                student_data.get("school_code"),
                                student_data.get("ell_language"),
                                bool(student_data.get("gifted", 0)),
                                student_data.get("lunch_status"),
                            )
                        )

                    # Bulk insert contacts
                    contact_sql = """
                    INSERT INTO contact (
                        id, type, salesforce_individual_id, salesforce_account_id,
                        salutation, first_name, middle_name, last_name, suffix,
                        description, age_group, education_level, birthdate,
                        gender, race_ethnicity, do_not_call, do_not_contact,
                        email_opt_out, email_bounced_date, exclude_from_reports,
                        last_email_date, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    student_sql = """
                    INSERT INTO student (
                        id, active, current_grade, legacy_grade, student_id,
                        school_id, class_salesforce_id, teacher_id, racial_ethnic,
                        school_code, ell_language, gifted, lunch_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    new_cursor = new_conn.cursor()
                    new_cursor.executemany(contact_sql, contact_values)
                    new_cursor.executemany(student_sql, student_values)
                    new_conn.commit()

                    total_copied += len(new_students)

                    # Update existing students set to avoid duplicates in next chunks
                    for student_data in new_students:
                        existing_students.add(student_data["id"])

                total_processed += len(rows)
                chunk_time = time.time() - chunk_start_time

                # Progress update
                elapsed_time = time.time() - start_time
                rate = total_processed / elapsed_time if elapsed_time > 0 else 0

                print(
                    f"Processed: {total_processed:,} records | Copied: {total_copied:,} | Skipped: {total_skipped:,} | Rate: {rate:.1f} records/sec | Chunk time: {chunk_time:.2f}s"
                )

            total_time = time.time() - start_time
            print(f"\nFast Migration Complete!")
            print(f"Total records processed: {total_processed:,}")
            print(f"Students copied: {total_copied:,}")
            print(f"Students skipped (already exist): {total_skipped:,}")
            print(f"Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
            print(f"Average rate: {total_processed/total_time:.1f} records/second")

        except Exception as e:
            print(f"Error during migration: {e}")
            import traceback

            traceback.print_exc()
        finally:
            old_conn.close()
            new_conn.close()


if __name__ == "__main__":
    # Ensure the instance directory exists
    if not os.path.exists("instance"):
        os.makedirs("instance")
        print("Created 'instance' directory.")

    # Basic check if databases exist
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: Old database not found at {OLD_DB_PATH}")
    elif not os.path.exists(NEW_DB_PATH):
        print(f"Error: New database not found at {NEW_DB_PATH}")
        print("Please ensure the new database is initialized (e.g., using Flask-Migrate or db.create_all()).")
    else:
        copy_students_fast()
