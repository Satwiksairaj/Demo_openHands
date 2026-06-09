from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Employee, Department

import logging
app = Flask(__name__)

app.config['SECRET_KEY'] = 'a_random_secure_key'
# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

@app.route('/api/stats')
def stats_api():
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(is_active=True).count()
    inactive_employees = Employee.query.filter_by(is_active=False).count()
    department_counts = {
        department.name: Employee.query.filter_by(department_id=department.id).count() for department in Department.query.all()
    }
    return jsonify({
        'total_employees': total_employees,
        'active_employees': active_employees,
        'inactive_employees': inactive_employees,
        'department_counts': department_counts
    })
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/')
@app.route('/employees')
def list_employees():
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        name = request.form['name']
        department_id = request.form['department_id']
        new_employee = Employee(name=name, department_id=department_id)
        db.session.add(new_employee)
        db.session.commit()
        flash('Employee added successfully!')
        return redirect(url_for('list_employees'))
    departments = Department.query.all()
    return render_template('add_employee.html', departments=departments)

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    employee = Employee.query.get(employee_id)
    if not employee:
        logging.error(f"Error editing employee {employee_id}: Employee not found")
        flash('Employee not found.')
        return redirect(url_for('list_employees'))
    if request.method == 'POST':
        try:
            employee.name = request.form['name']
            employee.department_id = request.form['department_id']
            db.session.commit()
            flash('Employee updated successfully!')
            return redirect(url_for('list_employees'))
        except Exception as e:
            logging.error(f"Error editing employee {employee_id}: {str(e)}")
            flash('An error occurred while updating the employee.')
            return redirect(url_for('list_employees'))
    departments = Department.query.all()
    return render_template('edit_employee.html', employee=employee, departments=departments)

@app.before_request
def ensure_log_file_exists():
    import os
    if not os.path.exists('app.log'):
        with open('app.log', 'w'):
            pass


@app.route('/deactivate_employee/<int:employee_id>')
def deactivate_employee(employee_id):
    try:
        employee = Employee.query.get(employee_id)
        if not employee:
            logging.error(f"Error deactivating employee {employee_id}: Employee not found")
            flash('Employee not found.')
            return redirect(url_for('list_employees'))
        employee.is_active = False
        db.session.commit()
        flash('Employee deactivated successfully!')
    except Exception as e:
        logging.error(f"Error deactivating employee {employee_id}: {str(e)}")
        flash('An error occurred while deactivating the employee.')
    return redirect(url_for('list_employees'))
@app.route('/report_issue', methods=['POST'])
def report_issue():
    try:
        description = request.form['description']
        logging.info(f'Received issue report: {description}')
        flash('Thank you for reporting the issue. We will look into it.')
    except Exception as e:
        logging.error(f"Error reporting issue: {str(e)}")
        flash('An error occurred while submitting your issue report.')
    return redirect(url_for('list_employees'))
def initialize_database():
    with app.app_context():
        db.create_all()
        if Employee.query.count() == 0:  # Only initialize if empty
            department1 = Department(name='HR')
            department2 = Department(name='Engineering')
            department3 = Department(name='Sales')
            department4 = Department(name='Marketing')
            db.session.add_all([department1, department2, department3, department4])
            db.session.commit()

            employees = [
                Employee(name='Alice', department=department1),
                Employee(name='Bob', department=department1),
                Employee(name='Charlie', department=department2),
                Employee(name='Diana', department=department2),
                Employee(name='Evan', department=department3),
                Employee(name='Fiona', department=department3),
                Employee(name='George', department=department4),
                Employee(name='Hannah', department=department4),
                Employee(name='Ivan', department=department1),
                Employee(name='Jack', department=department2),
                Employee(name='Karen', department=department3),
                Employee(name='Liam', department=department4)
            ]
            db.session.add_all(employees)
            db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)