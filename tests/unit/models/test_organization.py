import pytest
from datetime import datetime
from models.organization import Organization, VolunteerOrganization
from models import db

def test_new_organization(app):
    """Test creating a new organization"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(
                name='Test Organization',
                salesforce_id='001TEST123456789',
                type='Business',
                description='Test Description',
                volunteer_parent_id='003TEST123456789',
                billing_street='123 Test St',
                billing_city='Test City',
                billing_state='TS',
                billing_postal_code='12345',
                billing_country='Test Country'
            )
            
            db.session.add(org)
            db.session.flush()
            
            # Test basic fields
            assert org.id is not None
            assert org.name == 'Test Organization'
            assert org.salesforce_id == '001TEST123456789'
            assert org.type == 'Business'
            assert org.description == 'Test Description'
            assert org.volunteer_parent_id == '003TEST123456789'
            
            # Test address fields
            assert org.billing_street == '123 Test St'
            assert org.billing_city == 'Test City'
            assert org.billing_state == 'TS'
            assert org.billing_postal_code == '12345'
            assert org.billing_country == 'Test Country'
            
            # Test timestamps
            assert isinstance(org.created_at, datetime)
            assert isinstance(org.updated_at, datetime)
            
            # Test Salesforce URL
            expected_url = "https://prep-kc.lightning.force.com/lightning/r/Account/001TEST123456789/view"
            assert org.salesforce_url == expected_url
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_volunteer_organization_relationship(app, test_volunteer):
    """Test relationship between Organization and Volunteer"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(
                name='Test Corp',
                type='Business'
            )
            db.session.add(org)
            db.session.flush()
            
            # Create volunteer organization relationship
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                role='Software Engineer',
                is_primary=True,
                status='Current'
            )
            db.session.add(vol_org)
            db.session.flush()
            
            # Test relationships using IDs instead of object comparison
            assert len(org.volunteer_organizations) == 1
            assert len(org.volunteers) == 1
            assert org.volunteers[0].id == test_volunteer.id
            assert org.volunteer_organizations[0].volunteer_id == test_volunteer.id
            
            # Test relationship attributes
            vol_org = org.volunteer_organizations[0]
            assert vol_org.role == 'Software Engineer'
            assert vol_org.is_primary is True
            assert vol_org.status == 'Current'
            assert isinstance(vol_org.created_at, datetime)
            assert isinstance(vol_org.updated_at, datetime)
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_organization_timestamps(app):
    """Test organization timestamp behavior"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(name='Timestamp Test Org')
            db.session.add(org)
            db.session.flush()
            
            # Store initial timestamps
            created_at = org.created_at
            updated_at = org.updated_at
            
            # Update organization
            org.name = 'Updated Org Name'
            db.session.flush()
            
            # Verify timestamps
            assert org.created_at == created_at  # Should not change
            assert org.updated_at > updated_at  # Should be updated
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_organization_salesforce_url(app):
    """Test organization Salesforce URL generation"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with Salesforce ID
            org_with_sf = Organization(
                name='SF Test Org',
                salesforce_id='001TEST123456789'
            )
            assert org_with_sf.salesforce_url == "https://prep-kc.lightning.force.com/lightning/r/Account/001TEST123456789/view"
            
            # Test without Salesforce ID
            org_without_sf = Organization(
                name='Non-SF Test Org'
            )
            assert org_without_sf.salesforce_url is None
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_volunteer_organization_cascade(app, test_volunteer):
    """Test cascade behavior when deleting organizations"""
    with app.app_context():
        db.session.begin()
        try:
            # Create organization
            org = Organization(name='Cascade Test Org')
            db.session.add(org)
            db.session.commit()  # Commit to ensure IDs are assigned
            
            # Create volunteer organization relationship
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                role='Tester'
            )
            db.session.add(vol_org)
            db.session.commit()  # Commit to ensure relationship is saved
            
            # Store IDs for later verification
            org_id = org.id
            
            # Delete organization
            db.session.delete(org)
            db.session.commit()  # Commit the deletion
            
            # Verify cascade delete
            assert db.session.get(Organization, org_id) is None
            vol_org_exists = db.session.query(VolunteerOrganization).filter_by(
                volunteer_id=test_volunteer.id,
                organization_id=org_id
            ).first()
            assert vol_org_exists is None
            
        except:
            db.session.rollback()
            raise 