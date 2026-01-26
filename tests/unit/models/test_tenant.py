"""
Unit tests for Tenant model (Test Pack 8)

Test Cases Covered:
- TC-806: Default feature flags on create
- TC-843: Key hashing (only hash stored)
"""

from datetime import datetime, timezone

import pytest

from models import db
from models.tenant import Tenant


class TestTenantModel:
    """Unit tests for the Tenant model"""

    def test_tenant_creation_basic(self, app):
        """TC-801: Tenant can be created with valid slug"""
        with app.app_context():
            tenant = Tenant(slug="test-tenant", name="Test Tenant")
            db.session.add(tenant)
            db.session.commit()

            assert tenant.id is not None
            assert tenant.slug == "test-tenant"
            assert tenant.name == "Test Tenant"
            assert tenant.is_active is True  # Default

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_default_feature_flags(self, app):
        """TC-806: Default feature flags on create"""
        with app.app_context():
            tenant = Tenant(slug="flags-test", name="Flags Test Tenant")
            db.session.add(tenant)
            db.session.commit()

            # Check default settings structure
            assert tenant.settings is not None
            features = tenant.settings.get("features", {})

            # Default features should be True for events and volunteers
            assert features.get("events_enabled") is True
            assert features.get("volunteers_enabled") is True

            # Advanced features should be False by default
            assert features.get("recruitment_enabled") is False
            assert features.get("prepkc_visibility_enabled") is False

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_api_key_generation(self, app):
        """TC-843: Key hashing - only hash stored, not plaintext"""
        with app.app_context():
            tenant = Tenant(slug="api-test", name="API Test Tenant")
            db.session.add(tenant)
            db.session.commit()

            # Generate API key
            plaintext_key = tenant.generate_api_key()

            # Verify key was returned
            assert plaintext_key is not None
            assert len(plaintext_key) > 20  # Should be substantial

            # Verify hash is stored, not plaintext
            assert tenant.api_key_hash is not None
            assert tenant.api_key_hash != plaintext_key  # Hash != plaintext
            assert tenant.api_key_created_at is not None

            # Verify the key can be validated
            assert tenant.validate_api_key(plaintext_key) is True
            assert tenant.validate_api_key("wrong-key") is False

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_api_key_rotation(self, app):
        """TC-841: Rotate API key - new key generated, old invalidated"""
        with app.app_context():
            tenant = Tenant(slug="rotate-test", name="Rotate Test Tenant")
            db.session.add(tenant)
            db.session.commit()

            # Generate first key
            first_key = tenant.generate_api_key()
            first_hash = tenant.api_key_hash

            # Generate second key (rotation)
            second_key = tenant.generate_api_key()

            # Keys should be different
            assert first_key != second_key
            assert first_hash != tenant.api_key_hash

            # Old key should no longer work
            assert tenant.validate_api_key(first_key) is False

            # New key should work
            assert tenant.validate_api_key(second_key) is True

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_unique_slug(self, app):
        """TC-802: Create tenant with duplicate slug fails"""
        with app.app_context():
            tenant1 = Tenant(slug="unique-test", name="First Tenant")
            db.session.add(tenant1)
            db.session.commit()

            tenant2 = Tenant(slug="unique-test", name="Second Tenant")
            db.session.add(tenant2)

            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

            db.session.rollback()

            # Cleanup
            db.session.delete(tenant1)
            db.session.commit()

    def test_tenant_get_portal_config(self, app):
        """Test portal config generation for backward compatibility"""
        with app.app_context():
            tenant = Tenant(
                slug="portal-test",
                name="Portal Test Tenant",
                settings={
                    "features": {"events_enabled": True},
                    "portal": {
                        "welcome_message": "Welcome!",
                        "teacher_login_label": "Teacher Login",
                    },
                },
            )
            db.session.add(tenant)
            db.session.commit()

            config = tenant.get_portal_config()

            assert config["slug"] == "portal-test"
            assert config["display_name"] == "Portal Test Tenant"
            assert config["welcome_message"] == "Welcome!"
            assert "teacher_login_url" in config
            assert "staff_login_url" in config

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_is_feature_enabled(self, app):
        """TC-822: Toggle feature flag persisted"""
        with app.app_context():
            tenant = Tenant(
                slug="feature-test",
                name="Feature Test Tenant",
                settings={
                    "features": {
                        "events_enabled": True,
                        "recruitment_enabled": False,
                    }
                },
            )
            db.session.add(tenant)
            db.session.commit()

            # Note: is_feature_enabled adds '_enabled' suffix automatically
            assert tenant.is_feature_enabled("events") is True
            assert tenant.is_feature_enabled("recruitment") is False
            assert tenant.is_feature_enabled("nonexistent") is False

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_with_district(self, app, test_district):
        """TC-804: Create tenant linked to district"""
        with app.app_context():
            # Merge the district into current session
            district = db.session.merge(test_district)

            tenant = Tenant(
                slug="district-link-test",
                name="District Linked Tenant",
                district_id=district.id,
            )
            db.session.add(tenant)
            db.session.commit()

            assert tenant.district_id == district.id
            assert tenant.district is not None
            assert tenant.district.name == district.name

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_deactivation(self, app):
        """TC-830: Deactivate active tenant"""
        with app.app_context():
            tenant = Tenant(
                slug="deactivate-test", name="Deactivate Test Tenant", is_active=True
            )
            db.session.add(tenant)
            db.session.commit()

            assert tenant.is_active is True

            # Deactivate
            tenant.is_active = False
            db.session.commit()

            # Verify
            assert tenant.is_active is False

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()

    def test_tenant_repr(self, app):
        """Test string representation"""
        with app.app_context():
            tenant = Tenant(slug="repr-test", name="Repr Test")
            db.session.add(tenant)
            db.session.commit()

            repr_str = repr(tenant)
            assert "repr-test" in repr_str
            assert "Repr Test" in repr_str

            # Cleanup
            db.session.delete(tenant)
            db.session.commit()
