import pytest
from app import app, db
from models import Task

@pytest.fixture(scope='module')
def test_client():
    flask_app = app
    flask_app.config['TESTING'] = True
    testing_client = flask_app.test_client()

    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()

@pytest.fixture(scope='module')
def init_database():
    db.session.commit()
    db.drop_all()
    db.create_all()

    # Insert task data
    task1 = Task(title='Test Task 1', description='This is a test task', priority='high')
    task2 = Task(title='Test Task 2', description='This is another test task', priority='low', completed=True)
    db.session.add(task1)
    db.session.add(task2)

    db.session.commit()

    yield db  # this is where the testing happens!

    db.drop_all()


def test_task_creation(test_client, init_database):
    response = test_client.post('/tasks', data=dict(title='Test Task 3', description='Another test task', priority='medium'))
    assert response.status_code == 302
    assert Task.query.filter_by(title='Test Task 3').first() is not None


def test_task_completion(test_client, init_database):
    task = Task.query.filter_by(title='Test Task 1').first()
    response = test_client.get(f'/tasks/{task.id}/complete')
    assert response.status_code == 302
    assert Task.query.get(task.id).completed


def test_api_task_counts(test_client, init_database):
    response = test_client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert data['open'] == Task.query.filter_by(completed=False).count()
    assert data['completed'] == Task.query.filter_by(completed=True).count()
