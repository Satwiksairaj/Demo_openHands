import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to the Task Manager!' in response.data

def test_invalid_route(client):
    response = client.get('/invalid-url')
    assert response.status_code == 404
    assert b'This URL is incorrect.' in response.data