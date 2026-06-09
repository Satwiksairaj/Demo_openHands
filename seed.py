from extensions import db
from models import Expense
from app import app
from datetime import datetime

# Seed data
expenses_data = [
    {'amount': 50.00, 'category': 'Food', 'description': 'Groceries', 'date': '2023-01-15', 'payment_method': 'Credit Card'},
    {'amount': 15.00, 'category': 'Transport', 'description': 'Bus Fare', 'date': '2023-01-18', 'payment_method': 'Cash'},
    {'amount': 200.00, 'category': 'Shopping', 'description': 'Clothes', 'date': '2023-01-20', 'payment_method': 'Debit Card'},
    # Add more expenses to make it 15 sample expenses
]

with app.app_context():
    db.create_all()
    for exp_data in expenses_data:
        exp = Expense(
            amount=exp_data['amount'],
            category=exp_data['category'],
            description=exp_data['description'],
            date=datetime.strptime(exp_data['date'], '%Y-%m-%d'),
            payment_method=exp_data['payment_method']
        )
        db.session.add(exp)

    db.session.commit()
    print('Database initialized with seed data.')