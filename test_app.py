import pytest
from flask import url_for
from app import app, db, Expense
from datetime import datetime

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

    with app.app_context():
        db.drop_all()


def test_create_expense(client):
    response = client.post('/add', data={
        'amount': '20.5',
        'category': 'Food',
        'description': 'Lunch',
        'date': datetime(2023, 10, 10).date(),
        'payment_method': 'Credit Card'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Food' in response.data


def test_delete_expense(client):
    # First create an expense to delete
    test_create_expense(client)

    # Get the first expense id
    expense = Expense.query.first()

    # Send a delete request
    response = client.post(f'/delete/{expense.id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Food' not in response.data


def test_filter_expense_by_category(client):
    from datetime import datetime

    # Create two expenses
    client.post('/add', data={
        'amount': '10.5',
        'category': 'Transport',
        'description': 'Bus ticket',
        'date': datetime(2023, 10, 10).date(),
        'payment_method': 'Cash'
    }, follow_redirects=True)

    client.post('/add', data={
        'amount': '20.5',
        'category': 'Food',
        'description': 'Lunch',
        'date': datetime(2023, 10, 10).date(),
        'payment_method': 'Credit Card'
    }, follow_redirects=True)

    # Filter by category 'Food'
    response = client.get('/expenses?category=Food')
    assert response.status_code == 200

    data = response.data.decode('utf-8')
    assert 'Food' in data
    assert 'Transport' not in data


def test_api_summary(client):
    # Create expenses for summary test
    client.post('/add', data={
        'amount': '20.0',
        'category': 'Groceries',
        'description': 'Weekly groceries',
        'date': datetime(2023, 10, 10).date(),
        'payment_method': 'Debit Card'
    }, follow_redirects=True)

    # Test API summary
    response = client.get(url_for('api_summary'))
    assert response.status_code == 200
    # Further assertion logic for API contract
