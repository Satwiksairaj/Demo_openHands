from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

from extensions import db
from models import Expense

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
@app.route('/add', methods=['POST'])
def add_expense():
    amount = request.form.get('amount')
    category = request.form.get('category')
    description = request.form.get('description')
    date_str = request.form.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    payment_method = request.form.get('payment_method')

    # Create new expense
    new_expense = Expense(amount=amount, category=category, description=description, date=date, payment_method=payment_method)

    # Add to database
    db.session.add(new_expense)
    db.session.commit()

    # Redirect after post
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)