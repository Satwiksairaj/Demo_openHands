import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Task
from datetime import datetime

@pytest.fixture

def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_task_creation(client):
    response = client.post('/tasks', data={
        'title': 'Test Task',
        'description': 'This is a test task.',
        'priority': 'high',
        'due_date': '2023-12-31'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test Task' in response.data


def test_complete_task(client):
    with app.app_context():
        due_date = datetime.strptime('2023-12-31', '%Y-%m-%d').date()
        task = Task(title='Complete Task', description='Complete this task.', priority='medium', due_date=due_date)
        db.session.add(task)
        db.session.commit()
        task_id = task.id  # Immediately capture the ID while session-bound
        
    response = client.get(f'/tasks/{task_id}/complete', follow_redirects=True)

    response = client.get(f'/tasks/{task.id}/complete', follow_redirects=True)
    assert response.status_code == 200
    assert b'Completed' in response.data


def test_api_tasks(client):
    due_date = datetime.strptime('2023-11-30', '%Y-%m-%d').date()
    
    client.post('/tasks', data={'title': 'Open Task', 'description': 'Open', 'priority': 'low', 'due_date': due_date}, follow_redirects=True)
    task_data = client.get('/api/tasks').get_json()
    assert task_data['open'] == 1
    assert task_data['completed'] == 0