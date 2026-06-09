import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_redirects_to_tasks(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.location.endswith('/tasks')

def test_tasks_page(client):
    response = client.get('/tasks')
    assert response.status_code == 200
    assert b'Task List' in response.data

def test_404_error_page(client):
    response = client.get('/undefined_route')
    assert response.status_code == 404
    assert b'Sorry, the page you are looking for does not exist.' in response.data
