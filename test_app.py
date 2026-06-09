import pytest
from flask import url_for
from app import app, initialize_database, db
from models import Employee, Department

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost.localdomain'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            initialize_database()
        yield client

    with app.app_context():
        db.drop_all()


def test_add_employee(client):
    with app.app_context():
        # initial count
        response = client.get(url_for('list_employees'))
        assert b'Alice' in response.data  # ensures Alice is in initial data
        count_before = Employee.query.count()
    
    # add new employee
    response = client.post(url_for('add_employee'), data=dict(name='Zoe', department_id=1), follow_redirects=True)
    assert b'Employee added successfully!' in response.data
    assert Employee.query.count() == count_before + 1
    

def test_edit_employee(client):
    with app.app_context():
        response = client.get(url_for('edit_employee', employee_id=1))
        assert b'Alice' in response.data
        response = client.post(url_for('edit_employee', employee_id=1), data=dict(name='Alice Smith', department_id=1), follow_redirects=True)
        assert b'Employee updated successfully!' in response.data
        assert Employee.query.get(1).name == 'Alice Smith'


def test_deactivate_employee(client):
    with app.app_context():
        response = client.get(url_for('deactivate_employee', employee_id=1), follow_redirects=True)
        assert b'Employee deactivated successfully!' in response.data
        assert not Employee.query.get(1).is_active


def test_search_employees(client):
    # Mock search functionality or logic as needed
    # Depending on implementation in app.py
    pass


def test_stats_api(client):
    with app.app_context():
        response = client.get(url_for('stats_api'))
        # Ensure stats endpoint is returning correct data
        stats = {'total_employees': 12, 'active_employees': 12, 'inactive_employees': 0, 'department_counts': {'HR': 3, 'Engineering': 3, 'Sales': 3, 'Marketing': 3}}
        assert response.json == stats
def test_log_error_handling(client, caplog):
    with app.app_context():
        # Trigger error by accessing non-existent employee
        client.get(url_for('edit_employee', employee_id=999), follow_redirects=True)
        # Check that log contains the error
        assert any('Error editing employee' in message for message in caplog.text.split('\n'))

def test_report_issue(client):
    with app.app_context():
        response = client.post(url_for('report_issue'), data={'description': 'Test issue'}, follow_redirects=True)
        assert b'Thank you for reporting the issue' in response.data
        # Verify logging took place
        with open('app.log', 'r') as file:
            log_content = file.read()
        assert 'Received issue report: Test issue' in log_content
