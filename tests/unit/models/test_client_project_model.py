import pytest
from models.client_project_model import ClientProject, ProjectStatus
from models import db
from datetime import datetime

def test_create_client_project(app):
    with app.app_context():
        project = ClientProject(
            status=ProjectStatus.IN_PROGRESS.value,
            teacher='John Doe',
            district='Test District',
            organization='Test Org',
            primary_contacts=[{'name': 'Contact 1', 'hours': 10}],
            project_description='Test project description',
            project_title='Test Project',
            project_dates='2024-01-01 to 2024-12-31',
            number_of_students=25
        )
        db.session.add(project)
        db.session.commit()
        assert project.id is not None
        assert project.status == ProjectStatus.IN_PROGRESS.value
        assert project.teacher == 'John Doe'
        assert project.district == 'Test District'
        assert project.organization == 'Test Org'
        assert project.primary_contacts == [{'name': 'Contact 1', 'hours': 10}]
        assert project.project_description == 'Test project description'
        assert project.project_title == 'Test Project'
        assert project.project_dates == '2024-01-01 to 2024-12-31'
        assert project.number_of_students == 25
        assert project.created_at is not None
        assert project.updated_at is not None
        # Cleanup
        db.session.delete(project)
        db.session.commit()

def test_project_status_enum(app):
    with app.app_context():
        # Test all enum values
        for status in ProjectStatus:
            project = ClientProject(
                status=status.value,
                teacher='Test Teacher',
                district='Test District',
                organization='Test Org'
            )
            db.session.add(project)
            db.session.commit()
            assert project.status == status.value
            db.session.delete(project)
            db.session.commit()

def test_json_field_primary_contacts(app):
    with app.app_context():
        contacts = [
            {'name': 'Contact 1', 'hours': 10},
            {'name': 'Contact 2', 'hours': 15},
            {'name': 'Contact 3', 'hours': 5}
        ]
        project = ClientProject(
            status=ProjectStatus.PLANNING.value,
            teacher='Test Teacher',
            district='Test District',
            organization='Test Org',
            primary_contacts=contacts
        )
        db.session.add(project)
        db.session.commit()
        assert project.primary_contacts == contacts
        assert len(project.primary_contacts) == 3
        assert project.primary_contacts[0]['name'] == 'Contact 1'
        assert project.primary_contacts[0]['hours'] == 10
        db.session.delete(project)
        db.session.commit()

def test_to_dict_method(app):
    with app.app_context():
        project = ClientProject(
            status=ProjectStatus.COMPLETED.value,
            teacher='Test Teacher',
            district='Test District',
            organization='Test Org',
            primary_contacts=[{'name': 'Contact 1', 'hours': 10}],
            project_description='Test description',
            project_title='Test Title',
            project_dates='2024-01-01 to 2024-12-31',
            number_of_students=30
        )
        db.session.add(project)
        db.session.commit()
        
        project_dict = project.to_dict()
        assert project_dict['id'] == project.id
        assert project_dict['status'] == ProjectStatus.COMPLETED.value
        assert project_dict['teacher'] == 'Test Teacher'
        assert project_dict['district'] == 'Test District'
        assert project_dict['organization'] == 'Test Org'
        assert project_dict['primary_contacts'] == [{'name': 'Contact 1', 'hours': 10}]
        assert project_dict['project_description'] == 'Test description'
        assert project_dict['project_title'] == 'Test Title'
        assert project_dict['project_dates'] == '2024-01-01 to 2024-12-31'
        assert project_dict['number_of_students'] == 30
        
        db.session.delete(project)
        db.session.commit()

def test_required_field_validation(app):
    with app.app_context():
        # Test missing required fields
        with pytest.raises(Exception):
            project = ClientProject(
                # Missing status
                teacher='Test Teacher',
                district='Test District',
                organization='Test Org'
            )
            db.session.add(project)
            db.session.commit()
        db.session.rollback()
        
        with pytest.raises(Exception):
            project = ClientProject(
                status=ProjectStatus.IN_PROGRESS.value,
                # Missing teacher
                district='Test District',
                organization='Test Org'
            )
            db.session.add(project)
            db.session.commit()
        db.session.rollback()

def test_timestamp_behavior(app):
    with app.app_context():
        project = ClientProject(
            status=ProjectStatus.IN_PROGRESS.value,
            teacher='Test Teacher',
            district='Test District',
            organization='Test Org'
        )
        db.session.add(project)
        db.session.commit()
        
        initial_created = project.created_at
        initial_updated = project.updated_at
        
        # Update the project
        project.teacher = 'Updated Teacher'
        db.session.commit()
        
        # created_at should not change, updated_at should change
        assert project.created_at == initial_created
        # Add a small delay to ensure timestamp difference
        import time
        time.sleep(0.001)
        assert project.updated_at >= initial_updated
        
        db.session.delete(project)
        db.session.commit()

def test_project_status_workflow(app):
    with app.app_context():
        # Start with planning
        project = ClientProject(
            status=ProjectStatus.PLANNING.value,
            teacher='Test Teacher',
            district='Test District',
            organization='Test Org'
        )
        db.session.add(project)
        db.session.commit()
        assert project.status == ProjectStatus.PLANNING.value
        
        # Move to in progress
        project.status = ProjectStatus.IN_PROGRESS.value
        db.session.commit()
        assert project.status == ProjectStatus.IN_PROGRESS.value
        
        # Complete the project
        project.status = ProjectStatus.COMPLETED.value
        db.session.commit()
        assert project.status == ProjectStatus.COMPLETED.value
        
        db.session.delete(project)
        db.session.commit() 