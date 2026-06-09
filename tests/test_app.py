import pytest
from app import app, db
import datetime
from models import Expense

@pytest.fixture(scope='module')
def test_client():
    flask_app = app
    testing_client = flask_app.test_client()

    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client

    ctx.pop()

@pytest.fixture(scope='function')
def init_db():
    db.create_all()
    yield db
    db.drop_all()

def test_expense_creation(test_client, init_db):
    response = test_client.post('/add', data=dict(amount=100, category='Food', description='Dinner', date='2023-01-25', payment_method='Credit Card'))
    assert response.status_code == 302  # redirection implies success
    assert Expense.query.filter_by(amount=100).first() is not None

def test_expense_deletion(test_client, init_db):
    # Create a sample expense
    expense = Expense(amount=50, category='Transport', description='Taxi', date=datetime.date(2023, 1, 20), payment_method='Cash')
    db.session.add(expense)
    db.session.commit()

    # Delete the expense
    response = test_client.post(f'/delete/{expense.id}')
    assert response.status_code == 302
    assert Expense.query.get(expense.id) is None

def test_api_summary(test_client, init_db):
    # Add sample data
    db.session.add_all([
        Expense(amount=200, category='Shopping', description='Grocery', date=datetime.date(2023, 1, 10), payment_method='Debit Card'),
        Expense(amount=300, category='Utilities', description='Electricity Bill', date=datetime.date(2023, 1, 15), payment_method='Bank Transfer'),
    ])
    db.session.commit()

    response = test_client.get('/api/summary')
    json_data = response.get_json()

    assert response.status_code == 200
    assert json_data['total_spent'] == 500
    assert json_data['by_category']['Shopping'] == 200
    assert json_data['by_category']['Utilities'] == 300
    assert json_data['largest_single_expense'] == 300
