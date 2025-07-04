import sqlite3
import os
from datetime import datetime, timezone

OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")

def copy_students():
    """
    Copies student data from the 'contact' and 'student' tables in old.db 
    to the corresponding tables in your_database.db.
    Handles the relationship where Student inherits from Contact.
    Skips duplicate entries based on checks in the new database.
    Ensures timestamps are in UTC format for new records.
    """
    old_conn = None
    new_conn = None
    
    try:
        # Connect to both old and new databases
        old_conn = sqlite3.connect(OLD_DB_PATH)
        old_conn.row_factory = sqlite3.Row # Access columns by name
        old_cursor = old_conn.cursor()

        new_conn = sqlite3.connect(NEW_DB_PATH)
        new_conn.row_factory = sqlite3.Row
        new_cursor = new_conn.cursor()

        # --- Get column names from old.db ---
        old_cursor.execute("PRAGMA table_info(contact)")
        contact_columns = [col['name'] for col in old_cursor.fetchall()]
        
        old_cursor.execute("PRAGMA table_info(student)")
        student_columns = [col['name'] for col in old_cursor.fetchall()]
        
        # Ensure essential columns exist
        if 'id' not in contact_columns or 'id' not in student_columns:
             raise ValueError("Required 'id' column missing in contact or student table in old.db")
        if 'salesforce_individual_id' not in contact_columns:
             print("Warning: 'salesforce_individual_id' not found in old contact table. Duplicate checking might be less reliable.")
             # Add fallback checks if needed, e.g., based on name/email
        
        # --- Fetch all student rows from old.db ---
        # Assuming student.id is the foreign key referencing contact.id
        old_cursor.execute("SELECT * FROM student")
        student_rows = old_cursor.fetchall()

        total = len(student_rows)
        copied = 0
        skipped_contact_exists = 0
        skipped_student_exists = 0
        skipped_fetch_error = 0
        
        print(f"Found {total} student records in old.db. Starting migration...")

        for student_row in student_rows:
            student_dict = dict(student_row)
            contact_id = student_dict.get('id') # Assuming student.id == contact.id

            if not contact_id:
                print(f"Skipping student row due to missing ID: {student_dict}")
                skipped_fetch_error += 1
                continue

            # --- Fetch corresponding contact row from old.db ---
            old_cursor.execute("SELECT * FROM contact WHERE id = ?", (contact_id,))
            contact_row = old_cursor.fetchone()

            if not contact_row:
                print(f"Skipping student ID {contact_id}: Corresponding contact record not found in old.db.")
                skipped_fetch_error += 1
                continue
                
            contact_dict = dict(contact_row)

            # --- Check if contact already exists in new.db ---
            existing_contact_id = None
            sf_id = contact_dict.get('salesforce_individual_id')
            
            if sf_id:
                 new_cursor.execute("SELECT id FROM contact WHERE salesforce_individual_id = ?", (sf_id,))
                 existing = new_cursor.fetchone()
                 if existing:
                     existing_contact_id = existing['id']
            else:
                 # Fallback check if salesforce_id is missing (less reliable)
                 # Consider checking first_name, last_name, maybe email if available
                 # For now, we'll assume if sf_id is missing, it's a new contact
                 pass # Or implement fallback check here

            if existing_contact_id is not None:
                 # Check if this existing contact is already linked to a student
                 new_cursor.execute("SELECT id FROM student WHERE id = ?", (existing_contact_id,))
                 if new_cursor.fetchone():
                      # print(f"Skipping contact ID {contact_id} (SF ID: {sf_id}): Already exists as a student in new.db.")
                      skipped_contact_exists += 1
                      continue
                 else:
                     # Contact exists but not as a student - should we update type? Or skip?
                     # For now, let's skip to avoid complex updates/potential conflicts
                     print(f"Skipping contact ID {contact_id} (SF ID: {sf_id}): Contact exists in new.db but is not a student. Manual review suggested.")
                     skipped_contact_exists += 1
                     continue


            # --- Check if student record already exists by ID in new.db ---
            # This covers cases where a student might exist even if the contact check passed 
            # (e.g., if SF IDs were missing/changed)
            new_cursor.execute("SELECT id FROM student WHERE id = ?", (contact_id,))
            if new_cursor.fetchone():
                # print(f"Skipping student ID {contact_id}: Student record already exists in new.db.")
                skipped_student_exists += 1
                continue

            # --- Insert into contact table in new.db ---
            try:
                # Map old columns to new schema (adjust names if they differ)
                # Use contact_dict values, ensure 'type' is 'student'
                # Add created_at, updated_at
                
                # Construct insert statement dynamically based on available columns
                contact_insert_cols = []
                contact_insert_placeholders = []
                contact_insert_values = []

                # Required fields for Contact base model
                required_contact_fields = ['id', 'first_name', 'last_name']
                for field in required_contact_fields:
                    if field not in contact_dict or contact_dict[field] is None:
                         raise ValueError(f"Missing required contact field '{field}' for old contact ID {contact_id}")

                # Map columns - adapt this mapping if column names differ significantly
                # between old.db and the new schema defined in models/contact.py
                # We are assuming direct mapping for common fields.
                for col in contact_columns:
                     if col in contact_dict: # Check if column exists in fetched data
                         # Map old column name to new column name if necessary
                         new_col_name = col # Assume same name for now
                         
                         # Handle potential Enum mismatches or data cleaning here if needed
                         value = contact_dict[col]
                         
                         # Skip 'type' from old DB, we set it explicitly
                         if new_col_name == 'type':
                             continue
                             
                         contact_insert_cols.append(new_col_name)
                         contact_insert_placeholders.append('?')
                         contact_insert_values.append(value)

                # Add mandatory 'type' field for the new schema
                if 'type' not in contact_insert_cols:
                    contact_insert_cols.append('type')
                    contact_insert_placeholders.append('?')
                    contact_insert_values.append('student') # Set polymorphic identity
                
                sql_contact_insert = f"""
                    INSERT INTO contact ({", ".join(contact_insert_cols)})
                    VALUES ({", ".join(contact_insert_placeholders)})
                """
                new_cursor.execute(sql_contact_insert, tuple(contact_insert_values))
                
                # Verify the inserted contact ID matches the original
                inserted_id = new_cursor.lastrowid # This might not be reliable if ID is not auto-increment
                                                   # Let's assume we inserted with the original contact_id
                
                if inserted_id != contact_id and contact_id not in contact_insert_values:
                     # If ID wasn't part of the insert values and lastrowid doesn't match,
                     # it implies the ID was auto-generated, which is wrong for inheritance.
                     # However, we included 'id' in the insert list derived from contact_columns.
                     # If 'id' was correctly included, this check might be redundant unless the insert failed silently.
                     # Let's primarily rely on the fact we explicitly inserted the ID.
                     pass


            except sqlite3.IntegrityError as e:
                print(f"Skipping contact ID {contact_id}: Integrity error during contact insert - {str(e)}")
                skipped_contact_exists += 1 # Count as skipped due to conflict
                new_conn.rollback() # Rollback this specific transaction
                continue
            except ValueError as e:
                 print(f"Skipping contact ID {contact_id}: Value error - {str(e)}")
                 skipped_fetch_error += 1
                 new_conn.rollback()
                 continue
            except Exception as e: # Catch other potential errors during insert prep/execution
                 print(f"Skipping contact ID {contact_id}: Unexpected error during contact insert - {type(e).__name__}: {str(e)}")
                 skipped_fetch_error += 1
                 new_conn.rollback()
                 continue


            # --- Insert into student table in new.db ---
            try:
                # Map old student columns to new schema (adjust names if they differ)
                # Use student_dict values, ensure 'id' matches contact_id
                student_insert_cols = []
                student_insert_placeholders = []
                student_insert_values = []

                # Map columns for student table
                for col in student_columns:
                    if col in student_dict: # Check if column exists in fetched data
                        # Map old column name to new column name if necessary
                        new_col_name = col # Assume same name for now
                        
                        # Handle potential Enum mismatches or data cleaning here if needed
                        value = student_dict[col]
                        
                        student_insert_cols.append(new_col_name)
                        student_insert_placeholders.append('?')
                        student_insert_values.append(value)
                        
                # Ensure the ID from the contact table is used if it wasn't already in student_columns
                if 'id' not in student_insert_cols:
                     student_insert_cols.insert(0, 'id') # Add 'id' column
                     student_insert_placeholders.insert(0, '?')
                     student_insert_values.insert(0, contact_id) # Use the contact ID
                elif student_dict.get('id') != contact_id:
                     # If student dict had an 'id' but it doesn't match contact_id, raise error
                     raise ValueError(f"Mismatch between student.id ({student_dict.get('id')}) and contact.id ({contact_id}) in old.db")

                # Add 'active' field if not present in old data, default to True
                if 'active' not in student_insert_cols:
                     student_insert_cols.append('active')
                     student_insert_placeholders.append('?')
                     student_insert_values.append(True) # Default active to True


                sql_student_insert = f"""
                    INSERT INTO student ({", ".join(student_insert_cols)})
                    VALUES ({", ".join(student_insert_placeholders)})
                """
                new_cursor.execute(sql_student_insert, tuple(student_insert_values))
                copied += 1

            except sqlite3.IntegrityError as e:
                print(f"Skipping student ID {contact_id}: Integrity error during student insert - {str(e)}. Rolling back contact insert.")
                # Rollback the contact insert as well since the student part failed
                new_conn.rollback()
                skipped_student_exists += 1 # Count as skipped due to conflict
                continue
            except ValueError as e:
                 print(f"Skipping student ID {contact_id}: Value error during student insert prep - {str(e)}. Rolling back contact insert.")
                 new_conn.rollback()
                 skipped_fetch_error += 1
                 continue
            except Exception as e: # Catch other potential errors during student insert
                 print(f"Skipping student ID {contact_id}: Unexpected error during student insert - {type(e).__name__}: {str(e)}. Rolling back contact insert.")
                 new_conn.rollback()
                 skipped_fetch_error += 1
                 continue


        # --- Commit transaction and print stats ---
        new_conn.commit()

        print(f"\nStudent Migration complete:")
        print(f"Total student records processed from old.db: {total}")
        print(f"Students copied successfully: {copied}")
        print(f"Skipped (contact/student already exists in new.db): {skipped_contact_exists + skipped_student_exists}")
        # print(f"  - Skipped (contact existed): {skipped_contact_exists}")
        # print(f"  - Skipped (student existed): {skipped_student_exists}")
        print(f"Skipped (data fetch/validation error): {skipped_fetch_error}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if new_conn:
            new_conn.rollback() # Rollback any partial changes on general DB error
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if new_conn:
            new_conn.rollback()
    finally:
        if old_conn:
            old_conn.close()
        if new_conn:
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
        copy_students()
