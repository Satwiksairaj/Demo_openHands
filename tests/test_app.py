import pytest
try:
    from app import app
except Exception:
    from app import create_app
    app = create_app()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to the Home Page!' in response.data
    assert b'Home' in response.data
    assert b'About' in response.data
    assert b'Contact' in response.data
