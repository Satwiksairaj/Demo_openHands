import pytest
from app import app
from extensions import db
from models import Expense

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_expenses.db'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

# Test cases will go here

# Sample test case
def test_expense_creation(client):
    response = client.post('/add', data={
        'amount': 100,
        'category': 'Food',
        'description': 'Groceries',
        'date': '2023-09-30',
        'payment_method': 'Card'
    })
    assert response.status_code == 302  # Redirect after post
    expenses = Expense.query.all()
    assert len(expenses) == 1
    assert expenses[0].amount == 100
    assert expenses[0].category == 'Food'
    assert expenses[0].description == 'Groceries'
    assert str(expenses[0].date) == '2023-09-30'
    assert expenses[0].payment_method == 'Card'