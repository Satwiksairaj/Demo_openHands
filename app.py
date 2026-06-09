from flask import Flask, render_template, request, redirect, url_for, jsonify
from extensions import db
from models import Expense

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db.init_app(app)

@app.route('/')
@app.route('/expenses')
def list_expenses():
    category = request.args.get('category')
    if category:
        expenses = Expense.query.filter_by(category=category).all()
    else:
        expenses = Expense.query.all()
    return render_template('expenses.html', expenses=expenses)

@app.route('/add', methods=['POST'])
def add_expense():
    amount = request.form.get('amount')
    category = request.form.get('category')
    description = request.form.get('description')
    date = request.form.get('date')
    payment_method = request.form.get('payment_method')
    from datetime import datetime
    
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    new_expense = Expense(amount=amount, category=category, description=description, date=date_obj, payment_method=payment_method)
    db.session.add(new_expense)
    db.session.commit()
    return redirect(url_for('list_expenses'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('list_expenses'))

@app.route('/dashboard')
def dashboard():
    # Placeholder for dashboard summary logic
    return render_template('dashboard.html')

@app.route('/api/summary')
def api_summary():
    # Placeholder for API summary logic
    return jsonify({})

if __name__ == '__main__':
    app.run(debug=True)
