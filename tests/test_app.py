import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to MySite!' in response.data
    assert b'Home' in response.data
    assert b'Features' in response.data
    assert b'Pricing' in response.data
    assert b'Contact' in response.data
