"""
Tenant Database Manager

Manages per-tenant SQLite database connections and provisioning.

Requirements:
- FR-TENANT-103: Route authenticated users to their tenant's database
- FR-TENANT-104: Duplicate reference data during provisioning
- FR-TENANT-106: Separate SQLite files (polaris_{slug}.db)
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from flask import current_app, g


class TenantDatabaseManager:
    """
    Manages multi-tenant SQLite database operations.

    Each tenant gets their own isolated SQLite database file:
    - instance/polaris.db           (PrepKC main)
    - instance/polaris_kckps.db     (KCKPS tenant)
    - instance/polaris_hmsd.db      (HMSD tenant)
    """

    # Reference tables to copy during provisioning (FR-TENANT-104)
    REFERENCE_TABLES = [
        "district",
        "school",
        "skill",
        "career_type",
    ]

    # Core tables to create in tenant databases (empty structure)
    TENANT_TABLES = [
        "users",
        "volunteer",
        "organization",
        "event",
        "event_participation",
        "teacher",
        "teacher_progress",
        "student",
        "student_participation",
        "virtual_session",
        "virtual_session_presenter",
        "contact_attempt",
        "email_log",
    ]

    def __init__(self, instance_path: Optional[str] = None):
        """
        Initialize the database manager.

        Args:
            instance_path: Path to instance folder. Defaults to Flask app instance path.
        """
        self.instance_path = instance_path or self._get_instance_path()

    def _get_instance_path(self) -> str:
        """Get the instance path from Flask app or use default."""
        try:
            return current_app.instance_path
        except RuntimeError:
            # Outside of application context
            return os.path.join(os.getcwd(), "instance")

    def get_main_db_path(self) -> str:
        """Get path to the main PrepKC database."""
        return os.path.join(self.instance_path, "your_database.db")

    def get_tenant_db_path(self, slug: str) -> str:
        """
        Get path to a tenant's database file.

        Args:
            slug: Tenant slug (e.g., 'kckps')

        Returns:
            Path like 'instance/polaris_kckps.db'
        """
        return os.path.join(self.instance_path, f"polaris_{slug}.db")

    def get_tenant_db_uri(self, slug: str) -> str:
        """
        Get SQLAlchemy URI for a tenant's database.

        Args:
            slug: Tenant slug

        Returns:
            SQLite URI like 'sqlite:///instance/polaris_kckps.db'
        """
        db_path = self.get_tenant_db_path(slug)
        return f"sqlite:///{db_path}"

    def tenant_database_exists(self, slug: str) -> bool:
        """Check if a tenant's database file exists."""
        return os.path.exists(self.get_tenant_db_path(slug))

    def ensure_tenant_database(self, slug: str) -> bool:
        """
        Create a tenant database if it doesn't exist.

        Creates the database file with proper schema by copying structure
        from the main database.

        Args:
            slug: Tenant slug

        Returns:
            True if database was created, False if already existed
        """
        tenant_db_path = self.get_tenant_db_path(slug)

        if os.path.exists(tenant_db_path):
            return False

        # Ensure instance directory exists
        os.makedirs(self.instance_path, exist_ok=True)

        # Get schema from main database
        main_db_path = self.get_main_db_path()

        if not os.path.exists(main_db_path):
            raise FileNotFoundError(f"Main database not found: {main_db_path}")

        # Create new database and copy schema
        self._create_tenant_database_schema(main_db_path, tenant_db_path)

        return True

    def _create_tenant_database_schema(self, source_db: str, target_db: str) -> None:
        """
        Create tenant database with schema from source database.

        Args:
            source_db: Path to source database (main DB)
            target_db: Path to target database (new tenant DB)
        """
        source_conn = sqlite3.connect(source_db)
        target_conn = sqlite3.connect(target_db)

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Get all table creation statements from source
            source_cursor.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type='table' AND sql IS NOT NULL
                ORDER BY name
            """
            )

            for (create_sql,) in source_cursor.fetchall():
                if create_sql:
                    # Skip internal SQLite tables
                    if "sqlite_" in create_sql.lower():
                        continue
                    try:
                        target_cursor.execute(create_sql)
                    except sqlite3.OperationalError:
                        # Table might already exist, skip
                        pass

            # Copy indexes
            source_cursor.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type='index' AND sql IS NOT NULL
            """
            )

            for (index_sql,) in source_cursor.fetchall():
                if index_sql:
                    try:
                        target_cursor.execute(index_sql)
                    except sqlite3.OperationalError:
                        # Index might already exist, skip
                        pass

            target_conn.commit()

        finally:
            source_conn.close()
            target_conn.close()

    def provision_reference_data(self, slug: str) -> dict:
        """
        Copy reference data tables to a tenant database.

        Copies data from: district, school, skill, career_type

        Args:
            slug: Tenant slug

        Returns:
            Dict with counts of records copied per table
        """
        tenant_db_path = self.get_tenant_db_path(slug)
        main_db_path = self.get_main_db_path()

        if not os.path.exists(tenant_db_path):
            raise FileNotFoundError(f"Tenant database not found: {tenant_db_path}")

        main_conn = sqlite3.connect(main_db_path)
        tenant_conn = sqlite3.connect(tenant_db_path)

        results = {}

        try:
            main_cursor = main_conn.cursor()
            tenant_cursor = tenant_conn.cursor()

            for table in self.REFERENCE_TABLES:
                # Check if table exists in main db
                main_cursor.execute(
                    f"""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                """,
                    (table,),
                )

                if not main_cursor.fetchone():
                    results[table] = 0
                    continue

                # Get all data from main db
                main_cursor.execute(f"SELECT * FROM {table}")
                rows = main_cursor.fetchall()

                if not rows:
                    results[table] = 0
                    continue

                # Get column names
                main_cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in main_cursor.fetchall()]

                # Clear existing data in tenant db
                tenant_cursor.execute(f"DELETE FROM {table}")

                # Insert data
                placeholders = ",".join(["?" for _ in columns])
                insert_sql = (
                    f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                )

                tenant_cursor.executemany(insert_sql, rows)
                results[table] = len(rows)

            tenant_conn.commit()

        finally:
            main_conn.close()
            tenant_conn.close()

        return results

    def get_tenant_stats(self, slug: str) -> Optional[dict]:
        """
        Get statistics about a tenant's database.

        Args:
            slug: Tenant slug

        Returns:
            Dict with table row counts, or None if DB doesn't exist
        """
        tenant_db_path = self.get_tenant_db_path(slug)

        if not os.path.exists(tenant_db_path):
            return None

        conn = sqlite3.connect(tenant_db_path)
        cursor = conn.cursor()

        stats = {
            "exists": True,
            "path": tenant_db_path,
            "size_bytes": os.path.getsize(tenant_db_path),
            "tables": {},
        }

        try:
            # Get all tables
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )

            for (table,) in cursor.fetchall():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats["tables"][table] = cursor.fetchone()[0]

        finally:
            conn.close()

        return stats

    def delete_tenant_database(self, slug: str) -> bool:
        """
        Delete a tenant's database file.

        WARNING: This permanently deletes all tenant data!

        Args:
            slug: Tenant slug

        Returns:
            True if deleted, False if didn't exist
        """
        tenant_db_path = self.get_tenant_db_path(slug)

        if os.path.exists(tenant_db_path):
            os.remove(tenant_db_path)
            return True

        return False


# Convenience functions for use in Flask context


def get_db_manager() -> TenantDatabaseManager:
    """Get or create TenantDatabaseManager for current request."""
    if "db_manager" not in g:
        g.db_manager = TenantDatabaseManager()
    return g.db_manager


def get_current_tenant_slug() -> Optional[str]:
    """Get the current tenant slug from request context."""
    return getattr(g, "tenant_slug", None)


def set_current_tenant(slug: str) -> None:
    """Set the current tenant for this request."""
    g.tenant_slug = slug
