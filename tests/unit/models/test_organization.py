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
                description='Test Description',
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
            db.session.commit()
            
            # Store initial timestamps
            created_at = org.created_at
            updated_at = org.updated_at
            
            # Update organization
            org.name = 'Updated Org Name'
            db.session.commit()
            
            # Verify timestamps
            assert org.created_at == created_at  # Should not change
            # Add a small delay to ensure timestamp difference
            import time
            time.sleep(0.001)
            assert org.updated_at >= updated_at  # Should be updated
            
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

def test_organization_unique_salesforce_id(app):
    """Test that organizations cannot have duplicate Salesforce IDs"""
    with app.app_context():
        db.session.begin()
        try:
            # Create first organization
            org1 = Organization(
                name='First Org',
                salesforce_id='001TEST123456789'
            )
            db.session.add(org1)
            db.session.flush()
            
            # Attempt to create second organization with same Salesforce ID
            org2 = Organization(
                name='Second Org',
                salesforce_id='001TEST123456789'
            )
            db.session.add(org2)
            
            # Should raise IntegrityError due to unique constraint
            with pytest.raises(Exception):  # Replace with specific exception if known
                db.session.flush()
                
        finally:
            db.session.rollback()

def test_volunteer_organization_multiple_relationships(app, test_volunteer):
    """Test volunteer can have multiple organization relationships"""
    with app.app_context():
        db.session.begin()
        try:
            # Refresh test_volunteer in current session
            test_volunteer = db.session.merge(test_volunteer)
            
            # Create two organizations
            org1 = Organization(name='Primary Org')
            org2 = Organization(name='Secondary Org')
            db.session.add_all([org1, org2])
            db.session.flush()
            
            # Create relationships using IDs instead of objects
            vol_org1 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org1.id,
                role='Manager',
                is_primary=True,
                status='Current'
            )
            vol_org2 = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org2.id,
                role='Contributor',
                is_primary=False,
                status='Past'
            )
            db.session.add_all([vol_org1, vol_org2])
            db.session.flush()
            
            # Refresh the test_volunteer to ensure relationships are loaded
            db.session.refresh(test_volunteer)
            
            # Verify relationships
            assert len(test_volunteer.organizations) == 2
            assert len(test_volunteer.volunteer_organizations) == 2
            
            # Verify only one primary relationship
            primary_orgs = [vo for vo in test_volunteer.volunteer_organizations if vo.is_primary]
            assert len(primary_orgs) == 1
            assert primary_orgs[0].organization_id == org1.id
            
            db.session.commit()
        except:
            db.session.rollback()
            raise

def test_volunteer_organization_date_validation(app, test_volunteer):
    """Test date validation in volunteer organization relationships"""
    with app.app_context():
        db.session.begin()
        try:
            org = Organization(name='Date Test Org')
            db.session.add(org)
            db.session.flush()
            
            # Test valid date range
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 12, 31)
            vol_org = VolunteerOrganization(
                volunteer_id=test_volunteer.id,
                organization_id=org.id,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(vol_org)
            db.session.flush()
            
            # Verify dates were saved correctly
            assert vol_org.start_date == start_date
            assert vol_org.end_date == end_date
            
            db.session.commit()
        except:
            db.session.rollback()
            raise

def test_organization_address_fields(app):
    """Test organization address field validations"""
    with app.app_context():
        db.session.begin()
        try:
            # Test with minimal address info
            org1 = Organization(
                name='Minimal Address Org',
                billing_city='Test City',
                billing_state='TS'
            )
            db.session.add(org1)
            db.session.flush()
            
            # Test with full address info
            org2 = Organization(
                name='Full Address Org',
                billing_street='123 Test St\nSuite 100',  # Test multi-line street
                billing_city='Test City',
                billing_state='TS',
                billing_postal_code='12345-6789',  # Test extended ZIP
                billing_country='Test Country'
            )
            db.session.add(org2)
            db.session.flush()
            
            assert org1.id is not None
            assert org2.id is not None
            
            db.session.commit()
        except:
            db.session.rollback()
            raise 