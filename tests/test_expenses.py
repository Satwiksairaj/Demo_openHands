import pytest
from app import app, db
from models import Expense
from datetime import date

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client

def test_add_expense(client):
    response = client.post('/add', data={
        'amount': '100.00',
        'category': 'Test',
        'description': 'Test expense',
        'date': '2023-10-10',
        'payment_method': 'Cash'
    })
    assert response.status_code == 302
    with app.app_context():
        expense = Expense.query.first()
        assert expense is not None
        assert expense.amount == 100.00
        assert expense.category == 'Test'
        assert expense.description == 'Test expense'
        assert expense.date == date(2023, 10, 10)
        assert expense.payment_method == 'Cash'

def test_delete_expense(client):
    with app.app_context():
        expense = Expense(amount=50.0, category='Test', description='Test expense', date=date.today(), payment_method='Cash')
        db.session.add(expense)
        db.session.commit()
        expense_id = expense.id
        
        response = client.post(f'/delete/{expense_id}')
        assert response.status_code == 302
        assert Expense.query.count() == 0
