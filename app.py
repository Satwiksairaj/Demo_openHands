from flask import Flask, render_template, request, redirect
from models import Expense, db
from datetime import date
from database import seed_data

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def initialize_database():
    db.create_all()
    seed_data()

@app.route('/', methods=['GET'])
def index():
    category_filter = request.args.get('category', '')
    if category_filter:
        expenses = Expense.query.filter_by(category=category_filter).all()
    else:
        expenses = Expense.query.all()
    categories = Expense.query.with_entities(Expense.category).distinct().all()
    return render_template('index.html', expenses=expenses, categories=categories)

@app.route('/add', methods=['POST'])
def add_expense():
    amount = request.form['amount']
    category = request.form['category']
    description = request.form['description']
    expense_date = request.form['date']
    payment_method = request.form['payment_method']
    new_expense = Expense(
        amount=float(amount),
        category=category,
        description=description,
        date=date.fromisoformat(expense_date),
        payment_method=payment_method
    )
    db.session.add(new_expense)
    db.session.commit()
    return redirect('/')

@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return redirect('/')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Placeholder for dashboard logic
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
