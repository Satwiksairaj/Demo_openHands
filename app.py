from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import Expense
from datetime import datetime
from extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db.init_app(app)

@app.route('/expenses')
def expenses():
    expenses_list = Expense.query.all()
    return render_template('index.html', expenses=expenses_list)

@app.route('/add', methods=['POST'])
def add_expense():
    amount = request.form.get('amount')
    category = request.form.get('category')
    description = request.form.get('description')
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
    payment_method = request.form.get('payment_method')

    if not amount or not category or not date or not payment_method:
        return redirect(url_for('expenses'))

    new_expense = Expense(amount=amount, category=category, description=description, date=date, payment_method=payment_method)
    db.session.add(new_expense)
    db.session.commit()

    return redirect(url_for('expenses'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    expense = Expense.query.get(id)
    if expense:
        db.session.delete(expense)
        db.session.commit()
    return redirect(url_for('expenses'))

@app.route('/dashboard')
def dashboard():
    total_spending = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    category_breakdown = db.session.query(Expense.category, db.func.sum(Expense.amount)).group_by(Expense.category).all()
    largest_expense = db.session.query(db.func.max(Expense.amount)).scalar() or 0

    category_summary = {category: amount for category, amount in category_breakdown}

    return render_template('dashboard.html', 
                           total_spending=total_spending, 
                           category_breakdown=category_summary, 
                           largest_expense=largest_expense)

@app.route('/api/summary')
def api_summary():
    total_spent = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    by_category = db.session.query(Expense.category, db.func.sum(Expense.amount)).group_by(Expense.category).all()
    by_month = db.session.query(db.func.strftime('%Y-%m', Expense.date), db.func.sum(Expense.amount)).group_by(db.func.strftime('%Y-%m', Expense.date)).all()
    largest_single_expense = db.session.query(db.func.max(Expense.amount)).scalar() or 0

    summary = {
        'total_spent': total_spent,
        'by_category': {category: amount for category, amount in by_category},
        'by_month': {month: amount for month, amount in by_month},
        'largest_single_expense': largest_single_expense
    }

    return jsonify(summary)

if __name__ == '__main__':
    app.run(debug=True)