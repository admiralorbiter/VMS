import pytest
from models.tech_job_board import EntryLevelJob, JobOpportunity, WorkLocationType
from models import db

def test_new_job_opportunity(app):
    """Test creating a new job opportunity"""
    with app.app_context():
        job_opp = JobOpportunity(
            company_name='Test Company',
            description='Test Description',
            industry='Technology',
            current_openings=5,
            opening_types='Software Engineer, Data Scientist',
            location='Kansas City, MO',
            entry_level_available=True,
            kc_based=True,
            remote_available=True,
            notes='Test notes',
            job_link='https://example.com/jobs',
            is_active=True
        )
        
        db.session.add(job_opp)
        db.session.commit()
        
        # Test basic fields
        assert job_opp.id is not None
        assert job_opp.company_name == 'Test Company'
        assert job_opp.description == 'Test Description'
        assert job_opp.industry == 'Technology'
        assert job_opp.current_openings == 5
        assert job_opp.opening_types == 'Software Engineer, Data Scientist'
        assert job_opp.location == 'Kansas City, MO'
        assert job_opp.entry_level_available is True
        assert job_opp.kc_based is True
        assert job_opp.remote_available is True
        assert job_opp.notes == 'Test notes'
        assert job_opp.job_link == 'https://example.com/jobs'
        assert job_opp.is_active is True
        
        # Test relationships
        assert len(job_opp.entry_level_positions) == 0
        
        # Test __repr__
        assert repr(job_opp) == '<JobOpportunity Test Company (Technology)>'
        
        # Cleanup
        db.session.delete(job_opp)
        db.session.commit()

def test_new_entry_level_job(app, test_job_opportunity):
    """Test creating a new entry level job"""
    with app.app_context():
        # Get a fresh instance of test_job_opportunity
        job_opp = db.session.get(JobOpportunity, test_job_opportunity.id)
        
        entry_job = EntryLevelJob(
            job_opportunity_id=job_opp.id,
            title='Junior Developer',
            description='Entry level developer position',
            address='123 Tech St, Kansas City, MO',
            job_link='https://example.com/jobs/junior-dev',
            skills_needed='Python, JavaScript, SQL',
            work_location=WorkLocationType.HYBRID,
            is_active=True
        )
        
        db.session.add(entry_job)
        db.session.commit()
        
        # Refresh the objects from the database
        db.session.refresh(entry_job)
        db.session.refresh(job_opp)
        
        # Test basic fields
        assert entry_job.id is not None
        assert entry_job.job_opportunity_id == job_opp.id
        assert entry_job.title == 'Junior Developer'
        assert entry_job.description == 'Entry level developer position'
        assert entry_job.address == '123 Tech St, Kansas City, MO'
        assert entry_job.job_link == 'https://example.com/jobs/junior-dev'
        assert entry_job.skills_needed == 'Python, JavaScript, SQL'
        assert entry_job.work_location == WorkLocationType.HYBRID
        assert entry_job.is_active is True
        
        # Test relationship
        assert entry_job.job_opportunity_id == job_opp.id
        assert entry_job in job_opp.entry_level_positions
        
        # Test skills_list property
        assert entry_job.skills_list == ['Python', 'JavaScript', 'SQL']
        
        # Test __repr__
        expected_repr = f'<EntryLevelJob Junior Developer at {job_opp.company_name}>'
        assert repr(entry_job) == expected_repr
        
        # Cleanup
        db.session.delete(entry_job)
        db.session.commit()

def test_job_opportunity_active_positions(app, test_job_opportunity):
    """Test active_entry_level_positions property"""
    with app.app_context():
        # Get a fresh instance of test_job_opportunity
        job_opp = db.session.get(JobOpportunity, test_job_opportunity.id)
        
        # Create active and inactive positions
        active_job = EntryLevelJob(
            job_opportunity_id=job_opp.id,
            title='Active Position',
            work_location=WorkLocationType.ONSITE,  # Add required field
            is_active=True
        )
        inactive_job = EntryLevelJob(
            job_opportunity_id=job_opp.id,
            title='Inactive Position',
            work_location=WorkLocationType.ONSITE,  # Add required field
            is_active=False
        )
        
        db.session.add_all([active_job, inactive_job])
        db.session.commit()
        
        # Refresh the objects
        db.session.refresh(job_opp)
        db.session.refresh(active_job)
        db.session.refresh(inactive_job)
        
        # Test active_entry_level_positions property
        active_positions = job_opp.active_entry_level_positions
        assert len(active_positions) == 1
        assert active_job.id == active_positions[0].id  # Compare IDs instead of objects
        assert inactive_job.id not in [pos.id for pos in active_positions]
        
        # Cleanup
        db.session.delete(active_job)
        db.session.delete(inactive_job)
        db.session.commit()

def test_entry_level_job_skills_list(app, test_job_opportunity):
    """Test skills_list property with various inputs"""
    with app.app_context():
        # Test with normal skills list
        job1 = EntryLevelJob(
            job_opportunity_id=test_job_opportunity.id,
            title='Test Job 1',
            skills_needed='Python, JavaScript, SQL'
        )
        assert job1.skills_list == ['Python', 'JavaScript', 'SQL']
        
        # Test with empty skills
        job2 = EntryLevelJob(
            job_opportunity_id=test_job_opportunity.id,
            title='Test Job 2',
            skills_needed=''
        )
        assert job2.skills_list == []
        
        # Test with None skills
        job3 = EntryLevelJob(
            job_opportunity_id=test_job_opportunity.id,
            title='Test Job 3',
            skills_needed=None
        )
        assert job3.skills_list == [] 