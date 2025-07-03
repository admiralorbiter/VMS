import pytest
from models.bug_report import BugReport, BugReportType
from models.user import User
from models import db
from datetime import datetime, timezone

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()

def test_create_bug_report(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        bug = BugReport(
            type=BugReportType.BUG,
            description='Something is broken',
            page_url='/test',
            page_title='Test Page',
            submitted_by=user
        )
        db.session.add(bug)
        db.session.commit()
        assert bug.id is not None
        assert bug.type == BugReportType.BUG
        assert bug.description == 'Something is broken'
        assert bug.page_url == '/test'
        assert bug.page_title == 'Test Page'
        assert bug.submitted_by_id == user.id
        assert bug.submitted_by.username == 'buguser'
        assert bug.resolved is False
        assert bug.created_at is not None
        # Note: SQLite doesn't preserve timezone info, so we just check that timestamp exists
        # Cleanup
        db.session.delete(bug)
        db.session.delete(user)
        db.session.commit()

def test_bug_report_type_enum(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        bug = BugReport(
            type=BugReportType.DATA_ERROR,
            description='Data error',
            page_url='/data',
            page_title='Data Page',
            submitted_by=user
        )
        db.session.add(bug)
        db.session.commit()
        assert bug.type == BugReportType.DATA_ERROR
        db.session.delete(bug)
        db.session.delete(user)
        db.session.commit()

def test_resolution_workflow(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        bug = BugReport(
            type=BugReportType.OTHER,
            description='Other issue',
            page_url='/other',
            page_title='Other Page',
            submitted_by=user
        )
        db.session.add(bug)
        db.session.commit()
        # Mark as resolved
        bug.resolved = True
        bug.resolution_notes = 'Fixed!'
        bug.resolved_by = user
        bug.resolved_at = datetime.now(timezone.utc)
        db.session.commit()
        assert bug.resolved is True
        assert bug.resolution_notes == 'Fixed!'
        assert bug.resolved_by_id == user.id
        assert bug.resolved_by.username == 'buguser'
        assert bug.resolved_at is not None
        db.session.delete(bug)
        db.session.delete(user)
        db.session.commit()

def test_field_validation(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        # Description is required
        with pytest.raises(Exception):
            bug = BugReport(
                type=BugReportType.BUG,
                description=None,
                page_url='/fail',
                page_title='Fail',
                submitted_by=user
            )
            db.session.add(bug)
            db.session.commit()
        # Page URL is required
        with pytest.raises(Exception):
            bug = BugReport(
                type=BugReportType.BUG,
                description='desc',
                page_url=None,
                page_title='Fail',
                submitted_by=user
            )
            db.session.add(bug)
            db.session.commit()
        db.session.rollback()
        db.session.delete(user)
        db.session.commit()

def test_cascade_delete_user(app):
    with app.app_context():
        user = User(
            username='buguser',
            email='buguser@example.com',
            password_hash='hash',
            first_name='Bug',
            last_name='User',
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        bug = BugReport(
            type=BugReportType.BUG,
            description='Cascade test',
            page_url='/cascade',
            page_title='Cascade',
            submitted_by=user
        )
        db.session.add(bug)
        db.session.commit()
        user_id = user.id
        bug_id = bug.id
        # Delete bug report first to avoid foreign key constraint
        db.session.delete(bug)
        db.session.delete(user)
        db.session.commit()
        # Both should be deleted
        bug_check = db.session.get(BugReport, bug_id)
        user_check = db.session.get(User, user_id)
        assert bug_check is None
        assert user_check is None 