"""
Unit tests for TenantDatabaseManager

Test Cases:
- TC-860: Tenant database created on provisioning
- TC-861: Reference data copied to new tenant DB
- TC-862: Database path generation
"""

import os
import sqlite3
import tempfile

import pytest

from utils.db_manager import TenantDatabaseManager


class TestTenantDatabaseManager:
    """Tests for TenantDatabaseManager class."""

    @pytest.fixture
    def temp_instance_dir(self):
        """Create a temporary instance directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_main_db(self, temp_instance_dir):
        """Create a mock main database with schema and reference data."""
        # Use your_database.db to match TenantDatabaseManager.get_main_db_path()
        main_db_path = os.path.join(temp_instance_dir, "your_database.db")

        conn = sqlite3.connect(main_db_path)
        cursor = conn.cursor()

        # Create reference tables
        cursor.execute(
            """
            CREATE TABLE district (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE school (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                district_id INTEGER,
                FOREIGN KEY (district_id) REFERENCES district(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE career_type (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT
            )
        """
        )

        # Create a few operational tables
        cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                tenant_id INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE volunteer (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            )
        """
        )

        # Insert reference data
        cursor.executemany(
            "INSERT INTO district (id, name, code) VALUES (?, ?, ?)",
            [
                (1, "Kansas City Kansas Public Schools", "KCKPS"),
                (2, "Hickman Mills School District", "HMSD"),
                (3, "Center School District", "CENTER"),
            ],
        )

        cursor.executemany(
            "INSERT INTO school (id, name, district_id) VALUES (?, ?, ?)",
            [
                (1, "Central High School", 1),
                (2, "Sumner Academy", 1),
                (3, "Hickman Mills High", 2),
            ],
        )

        cursor.executemany(
            "INSERT INTO skill (id, name) VALUES (?, ?)",
            [
                (1, "Public Speaking"),
                (2, "Career Coaching"),
                (3, "Resume Review"),
            ],
        )

        cursor.executemany(
            "INSERT INTO career_type (id, name, category) VALUES (?, ?, ?)",
            [
                (1, "Software Engineer", "Technology"),
                (2, "Nurse", "Healthcare"),
                (3, "Teacher", "Education"),
            ],
        )

        # Create an index
        cursor.execute("CREATE INDEX ix_district_code ON district(code)")

        conn.commit()
        conn.close()

        return main_db_path

    def test_get_tenant_db_path(self, temp_instance_dir):
        """Test tenant database path generation."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        path = manager.get_tenant_db_path("kckps")

        assert "polaris_kckps.db" in path
        assert temp_instance_dir in path

    def test_get_tenant_db_uri(self, temp_instance_dir):
        """Test tenant database URI generation."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        uri = manager.get_tenant_db_uri("hmsd")

        assert uri.startswith("sqlite:///")
        assert "polaris_hmsd.db" in uri

    def test_tenant_database_exists_false(self, temp_instance_dir):
        """Test checking for non-existent database."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        assert manager.tenant_database_exists("nonexistent") is False

    def test_tenant_database_exists_true(self, temp_instance_dir, mock_main_db):
        """Test checking for existing database."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # Main DB exists
        assert os.path.exists(mock_main_db)

        # Create a tenant db
        manager.ensure_tenant_database("test-tenant")

        assert manager.tenant_database_exists("test-tenant") is True

    def test_ensure_tenant_database_creates_file(self, temp_instance_dir, mock_main_db):
        """TC-860: Tenant database created on provisioning."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # Database shouldn't exist yet
        assert not os.path.exists(manager.get_tenant_db_path("new-tenant"))

        # Create the database
        created = manager.ensure_tenant_database("new-tenant")

        # Should return True (was created)
        assert created is True

        # File should now exist
        assert os.path.exists(manager.get_tenant_db_path("new-tenant"))

    def test_ensure_tenant_database_copies_schema(
        self, temp_instance_dir, mock_main_db
    ):
        """Test that schema is copied from main database."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        manager.ensure_tenant_database("schema-test")

        # Connect to tenant DB and verify tables exist
        tenant_db_path = manager.get_tenant_db_path("schema-test")
        conn = sqlite3.connect(tenant_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        )

        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Should have all tables from main DB
        assert "district" in tables
        assert "school" in tables
        assert "skill" in tables
        assert "career_type" in tables
        assert "users" in tables
        assert "volunteer" in tables

    def test_ensure_tenant_database_idempotent(self, temp_instance_dir, mock_main_db):
        """Test that calling ensure twice doesn't fail."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # First call creates
        created1 = manager.ensure_tenant_database("idempotent-test")
        assert created1 is True

        # Second call returns False (already exists)
        created2 = manager.ensure_tenant_database("idempotent-test")
        assert created2 is False

    def test_provision_reference_data(self, temp_instance_dir, mock_main_db):
        """TC-861: Reference data copied to new tenant DB."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # Create the tenant database first
        manager.ensure_tenant_database("ref-data-test")

        # Provision reference data
        results = manager.provision_reference_data("ref-data-test")

        # Should have copied all reference tables
        assert results["district"] == 3
        assert results["school"] == 3
        assert results["skill"] == 3
        assert results["career_type"] == 3

    def test_provision_reference_data_actually_copied(
        self, temp_instance_dir, mock_main_db
    ):
        """Verify reference data is actually in tenant DB."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        manager.ensure_tenant_database("verify-copy")
        manager.provision_reference_data("verify-copy")

        # Connect and verify data
        tenant_db_path = manager.get_tenant_db_path("verify-copy")
        conn = sqlite3.connect(tenant_db_path)
        cursor = conn.cursor()

        # Check districts
        cursor.execute("SELECT name FROM district WHERE code = 'KCKPS'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "Kansas City Kansas Public Schools"

        # Check skills
        cursor.execute("SELECT COUNT(*) FROM skill")
        assert cursor.fetchone()[0] == 3

        conn.close()

    def test_get_tenant_stats(self, temp_instance_dir, mock_main_db):
        """Test getting statistics from tenant database."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # Non-existent DB returns None
        assert manager.get_tenant_stats("nonexistent") is None

        # Create and provision
        manager.ensure_tenant_database("stats-test")
        manager.provision_reference_data("stats-test")

        stats = manager.get_tenant_stats("stats-test")

        assert stats is not None
        assert stats["exists"] is True
        assert "size_bytes" in stats
        assert stats["tables"]["district"] == 3
        assert stats["tables"]["school"] == 3

    def test_delete_tenant_database(self, temp_instance_dir, mock_main_db):
        """Test deleting a tenant database."""
        manager = TenantDatabaseManager(instance_path=temp_instance_dir)

        # Create DB
        manager.ensure_tenant_database("delete-test")
        assert manager.tenant_database_exists("delete-test") is True

        # Delete it
        deleted = manager.delete_tenant_database("delete-test")

        assert deleted is True
        assert manager.tenant_database_exists("delete-test") is False

        # Deleting non-existent returns False
        deleted2 = manager.delete_tenant_database("delete-test")
        assert deleted2 is False
