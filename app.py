from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Task

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'


db.init_app(app)

@app.route('/tasks', methods=['GET', 'POST'])
def get_tasks():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority')
        due_date = request.form.get('due_date')
        new_task = Task(title=title, description=description, priority=priority, due_date=due_date, completed=False)
        db.session.add(new_task)
        db.session.commit()
        flash('Task created successfully!', 'success')
        return redirect(url_for('get_tasks'))
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

@app.route('/tasks/<int:id>/complete')
def complete_task(id):
    task = Task.query.get(id)
    if task:
        task.completed = True
        db.session.commit()
        flash('Task marked as complete!', 'success')
    else:
        flash('Task not found!', 'danger')
    return redirect(url_for('get_tasks'))

@app.route('/tasks/<int:id>/delete')
def delete_task(id):
    task = Task.query.get(id)
    if task:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully!', 'success')
    else:
        flash('Task not found!', 'danger')
    return redirect(url_for('get_tasks'))
@app.route('/api/tasks')
def api_tasks():
    open_tasks = Task.query.filter_by(completed=False).count()
    completed_tasks = Task.query.filter_by(completed=True).count()
    return jsonify({'open': open_tasks, 'completed': completed_tasks})

@app.route('/stats')
def stats():
    open_tasks = Task.query.filter_by(completed=False).count()
    completed_tasks = Task.query.filter_by(completed=True).count()
    total_tasks = Task.query.count()
    return render_template('stats.html', open_tasks=open_tasks, completed_tasks=completed_tasks, total_tasks=total_tasks)



if __name__ == '__main__':
    app.run(debug=True)
