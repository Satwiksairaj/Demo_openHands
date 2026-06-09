from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Employee, Department


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'  # Example database URI
db.init_app(app)


@app.route('/')
def index():
    return render_template('employees.html')

@app.route('/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        # Logic to add employee
        pass
    return render_template('add_employee.html')

def initialize_database(app):
    with app.app_context():
        db.create_all()
        if Employee.query.count() == 0:
            # Add initial data
            hr = Department(name='HR')
            it = Department(name='IT')
            finance = Department(name='Finance')
            marketing = Department(name='Marketing')
            db.session.add_all([hr, it, finance, marketing])
            employees = [
                Employee(name='Alice', department=hr),
                Employee(name='Bob', department=hr),
                Employee(name='Charlie', department=it),
                Employee(name='David', department=it),
                Employee(name='Eve', department=finance),
                Employee(name='Frank', department=finance),
                Employee(name='Grace', department=marketing),
                Employee(name='Heidi', department=marketing),
                Employee(name='Ivan', department=hr, is_active=False),
                Employee(name='Judy', department=it, is_active=False),
                Employee(name='Karl', department=finance),
                Employee(name='Laura', department=marketing)
            ]
            db.session.add_all(employees)
            db.session.commit()

initialize_database(app)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    if request.method == 'POST':
        # Logic to edit employee
        pass
    return render_template('edit_employee.html', employee={})

@app.route('/deactivate/<int:id>')
def deactivate_employee(id):
    # Logic to deactivate employee
    pass

@app.route('/search', methods=['GET'])
def search_employees():
    # Logic to search employees
    return render_template('employees.html')

@app.route('/api/stats')
def stats_api():
    # Logic to return API stats
    return jsonify({})

if __name__ == '__main__':
    app.run(debug=True)
