from models import Expense, db
from datetime import date

def seed_data():
    if Expense.query.count() == 0:
        sample_expenses = [
            Expense(amount=50.0, category='Food', description='Groceries', date=date(2023, 10, 1), payment_method='Credit Card'),
            Expense(amount=20.0, category='Transport', description='Bus ticket', date=date(2023, 10, 2), payment_method='Cash'),
            Expense(amount=100.0, category='Entertainment', description='Concert', date=date(2023, 10, 3), payment_method='Debit Card'),
            Expense(amount=200.0, category='Rent', description='Monthly rent', date=date(2023, 10, 4), payment_method='Bank Transfer'),
            Expense(amount=30.0, category='Utilities', description='Electricity bill', date=date(2023, 10, 5), payment_method='Credit Card'),
        ]
        db.session.bulk_save_objects(sample_expenses)
        db.session.commit()
