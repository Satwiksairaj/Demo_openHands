import pytest
from app import app, db
from models import User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


def test_register(client):
    response = client.post('/register', data={'username': 'testuser', 'password': 'testpassword'})
    assert response.status_code == 302
    # Check if redirected to login page after registration
    assert '/login' in response.headers['Location']


def test_login(client):
    # First, register a user
    client.post('/register', data={'username': 'testuser', 'password': 'testpassword'})
    
    # Attempt to log in
    response = client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    assert response.status_code == 302
    # Check if redirected to dashboard page after login
    assert '/dashboard' in response.headers['Location']


def test_logout(client):
    # First, register and log in a user
    client.post('/register', data={'username': 'testuser', 'password': 'testpassword'})
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    
    # Log out
    response = client.get('/logout')
    assert response.status_code == 302
    # Check if redirected to login page after logout
    assert '/login' in response.headers['Location']
