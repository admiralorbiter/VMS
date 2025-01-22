import pytest
from app import app as flask_app
from models import db
from config import TestingConfig
from models.user import User
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    flask_app.config.from_object(TestingConfig)
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Test',
        last_name='User',
        is_admin=False
    )
    with app.app_context():
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()

@pytest.fixture
def test_admin(app):
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('admin123'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def auth_headers(test_user, client):
    # Login and get session cookie
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    return {'Cookie': response.headers.get('Set-Cookie', '')} 