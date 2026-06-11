import pytest
from app import app, db
from models import Todo

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

@pytest.fixture
def runner():
    return app.test_cli_runner()

def test_create_todo(client):
    response = client.post('/todos', json={'title': 'Test Todo', 'description': 'Test Description'})
    assert response.status_code == 201
    assert response.json['title'] == 'Test Todo'
    assert response.json['description'] == 'Test Description'

def test_get_todos(client):
    response = client.get('/todos')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_update_todo(client):
    # First, create a todo
    response = client.post('/todos', json={'title': 'Update Test', 'description': 'Update Description'})
    todo_id = response.json['id']

    # Update the todo
    update_response = client.put(f'/todos/{todo_id}', json={'title': 'Updated Title', 'description': 'Updated Description'})
    assert update_response.status_code == 200
    assert update_response.json['title'] == 'Updated Title'

def test_delete_todo(client):
    # First, create a todo
    response = client.post('/todos', json={'title': 'Delete Test', 'description': 'Delete Description'})
    todo_id = response.json['id']

    # Delete the todo
    delete_response = client.delete(f'/todos/{todo_id}')
    assert delete_response.status_code == 200
    assert delete_response.json['message'] == 'Todo deleted successfully'
