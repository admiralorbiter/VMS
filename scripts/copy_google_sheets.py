#!/usr/bin/env python

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

# Ensure we can import the Flask app and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app import app  # noqa: E402
from models import db  # noqa: E402

# Paths follow the same convention as other copy scripts
OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")


def _load_users_from_old_db(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email FROM users")
    return cursor.fetchall()


def _build_old_to_new_user_id_map(old_users: Iterable[sqlite3.Row]) -> Dict[int, int]:
    """
    Build a mapping from old user IDs to new user IDs using username/email as stable identifiers.

    This allows preserving the GoogleSheet.created_by relationship even if primary keys changed.
    """
    old_to_new: Dict[int, int] = {}

    # Preload all new users once to avoid N queries
    new_users = db.session.execute(
        text("SELECT id, username, email FROM users")
    ).fetchall()
    # Build lookup by username/email for fast match
    username_to_id = {row[1]: row[0] for row in new_users if row[1] is not None}
    email_to_id = {row[2]: row[0] for row in new_users if row[2] is not None}

    for row in old_users:
        old_id = row[0]
        username = row[1]
        email = row[2]
        new_id: Optional[int] = None

        if username and username in username_to_id:
            new_id = username_to_id[username]
        elif email and email in email_to_id:
            new_id = email_to_id[email]

        if new_id is not None:
            old_to_new[old_id] = new_id

    return old_to_new


def _load_existing_google_sheet_signatures() -> Tuple[set, set]:
    """
    Load existing google_sheets identifiers from the target DB to avoid duplicates and ID collisions.

    Returns two sets:
      - existing_ids: set of primary keys present in target
      - existing_keys: set of (academic_year, purpose, sheet_name) tuples for duplicate detection
    """
    existing_ids = set()
    existing_keys = set()
    rows = db.session.execute(
        text(
            """
            SELECT id, academic_year, purpose, sheet_name
            FROM google_sheets
            """
        )
    ).fetchall()
    for row in rows:
        existing_ids.add(row[0])
        existing_keys.add((row[1], row[2], row[3]))
    return existing_ids, existing_keys


def _decrypt_sheet_id_if_needed(
    encrypted_value: Optional[str],
    mode: str,
    old_key: Optional[bytes],
) -> Optional[bytes]:
    """
    Optionally decrypt a base64-encoded encrypted value using the OLD key.

    Returns raw decrypted bytes or None if not applicable.
    """
    if not encrypted_value:
        return None
    if mode != "recrypt":
        return None

    try:
        from base64 import b64decode

        from cryptography.fernet import Fernet

        if not old_key:
            raise ValueError("OLD_ENCRYPTION_KEY is required for --mode recrypt")
        if isinstance(old_key, str):
            old_key = old_key.encode()

        f = Fernet(old_key)  # type: ignore[arg-type]
        encrypted_data = b64decode(encrypted_value.encode())
        decrypted = f.decrypt(encrypted_data)
        return decrypted
    except Exception as exc:
        print(f"WARNING: Failed to decrypt with old key; copying as-is. Error: {exc}")
        return None


def _encrypt_sheet_id_if_needed(
    decrypted_value: Optional[bytes],
    mode: str,
    new_key: Optional[bytes],
) -> Optional[str]:
    """
    Optionally encrypt plaintext bytes with the NEW key and return base64-encoded cipher text.
    """
    if decrypted_value is None:
        return None
    if mode != "recrypt":
        return None

    try:
        from base64 import b64encode

        from cryptography.fernet import Fernet

        if not new_key:
            raise ValueError("ENCRYPTION_KEY (new) is required for --mode recrypt")
        if isinstance(new_key, str):
            new_key = new_key.encode()

        f = Fernet(new_key)  # type: ignore[arg-type]
        encrypted = f.encrypt(decrypted_value)
        return b64encode(encrypted).decode()
    except Exception as exc:
        print(
            f"WARNING: Failed to encrypt with new key; will fallback to old stored value. Error: {exc}"
        )
        return None


def copy_google_sheets(mode: str = "raw") -> None:
    """
    Copy all rows from google_sheets in old.db to your_database.db.

    Modes:
      - raw (default): copies the encrypted sheet_id as-is (requires same ENCRYPTION_KEY to be usable)
      - recrypt: decrypt with OLD_ENCRYPTION_KEY and re-encrypt with ENCRYPTION_KEY (recommended if keys changed)
    """
    with app.app_context():
        start_ts = datetime.now()
        print(
            f"Starting GoogleSheet migration in '{mode}' mode at {start_ts:%Y-%m-%d %H:%M:%S}"
        )

        if not os.path.exists(OLD_DB_PATH):
            print(f"Error: Old database not found at {OLD_DB_PATH}")
            return
        if not os.path.exists(NEW_DB_PATH):
            print(f"Error: New database not found at {NEW_DB_PATH}")
            print("Please initialize the new database (e.g., db.create_all()).")
            return

        old_conn = sqlite3.connect(OLD_DB_PATH)
        new_conn = sqlite3.connect(NEW_DB_PATH)
        old_conn.row_factory = sqlite3.Row

        try:
            # Build user ID mapping to preserve created_by relationships
            print("Building user ID mapping...")
            old_users = _load_users_from_old_db(old_conn)
            user_id_map = _build_old_to_new_user_id_map(old_users)
            print(f"Mapped {len(user_id_map)} old users to new user IDs")

            # Load existing target IDs and uniqueness keys
            existing_ids, existing_keys = _load_existing_google_sheet_signatures()
            print(
                f"Target has {len(existing_ids)} existing google_sheets rows; using duplicate protection on (academic_year, purpose, sheet_name)"
            )

            # Optional keys for re-encryption
            old_key = os.getenv("OLD_ENCRYPTION_KEY")
            new_key = os.getenv("ENCRYPTION_KEY")

            # Read all google_sheets rows from old DB
            print("Fetching google_sheets rows from old database...")
            cursor = old_conn.cursor()
            cursor.execute(
                """
                SELECT id, academic_year, purpose, sheet_id, sheet_name, created_at, updated_at, created_by
                FROM google_sheets
                ORDER BY id
                """
            )
            rows = cursor.fetchall()
            print(f"Found {len(rows)} google_sheets rows in old database")

            # Prepare batched inserts
            insert_with_id: List[Tuple] = []
            insert_without_id: List[Tuple] = []
            skipped_duplicates = 0

            for r in rows:
                old_id = r[0]
                academic_year = r[1]
                purpose = r[2]
                stored_encrypted_sheet_id = r[3]
                sheet_name = r[4]
                created_at = r[5]
                updated_at = r[6]
                old_created_by = r[7]

                # Check duplicate by logical key
                logical_key = (academic_year, purpose, sheet_name)
                if logical_key in existing_keys:
                    skipped_duplicates += 1
                    continue

                # Determine new created_by via mapping (may be None)
                new_created_by = user_id_map.get(old_created_by)

                # Handle re-encryption if requested
                new_encrypted_value: Optional[str] = None
                if mode == "recrypt":
                    decrypted = _decrypt_sheet_id_if_needed(
                        stored_encrypted_sheet_id, mode, old_key
                    )
                    new_encrypted_value = _encrypt_sheet_id_if_needed(
                        decrypted, mode, new_key
                    )

                # Choose which encrypted value to insert
                final_sheet_id_value = (
                    new_encrypted_value
                    if new_encrypted_value is not None
                    else stored_encrypted_sheet_id
                )

                if old_id not in existing_ids:
                    insert_with_id.append(
                        (
                            old_id,
                            academic_year,
                            purpose,
                            final_sheet_id_value,
                            sheet_name,
                            created_at,
                            updated_at,
                            new_created_by,
                        )
                    )
                else:
                    insert_without_id.append(
                        (
                            academic_year,
                            purpose,
                            final_sheet_id_value,
                            sheet_name,
                            created_at,
                            updated_at,
                            new_created_by,
                        )
                    )

            # Execute inserts in batches
            new_cursor = new_conn.cursor()

            if insert_with_id:
                new_cursor.executemany(
                    """
                    INSERT INTO google_sheets (
                        id, academic_year, purpose, sheet_id, sheet_name, created_at, updated_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    insert_with_id,
                )

            if insert_without_id:
                new_cursor.executemany(
                    """
                    INSERT INTO google_sheets (
                        academic_year, purpose, sheet_id, sheet_name, created_at, updated_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    insert_without_id,
                )

            new_conn.commit()

            total_inserted = len(insert_with_id) + len(insert_without_id)
            print("\nGoogleSheet migration complete.")
            print(f"Inserted: {total_inserted}")
            print(f"  - with preserved IDs: {len(insert_with_id)}")
            print(f"  - with new IDs: {len(insert_without_id)}")
            print(f"Skipped as duplicates: {skipped_duplicates}")
            print(
                "Note: created_by mapped via username/email; rows without a match use NULL."
            )
            if mode == "recrypt":
                print(
                    "Mode 'recrypt': used OLD_ENCRYPTION_KEY -> ENCRYPTION_KEY for sheet_id values where possible."
                )
            else:
                print(
                    "Mode 'raw': copied encrypted sheet_id as-is. Ensure the same ENCRYPTION_KEY is configured to decrypt."
                )

        except Exception as e:
            print(f"Error during GoogleSheet migration: {e}")
            import traceback

            traceback.print_exc()
        finally:
            old_conn.close()
            new_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy google_sheets from old.db to your_database.db with relationship preservation."
    )
    parser.add_argument(
        "--mode",
        choices=["raw", "recrypt"],
        default="raw",
        help=(
            "Copy mode: 'raw' copies encrypted sheet_id as-is (default). 'recrypt' decrypts with OLD_ENCRYPTION_KEY and re-encrypts with ENCRYPTION_KEY."
        ),
    )
    args = parser.parse_args()
    copy_google_sheets(mode=args.mode)


if __name__ == "__main__":
    main()
