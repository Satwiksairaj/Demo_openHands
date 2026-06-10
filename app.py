from flask import Flask, render_template, request, redirect, url_for, jsonify
from extensions import db
from models import Task

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if request.method == 'POST':
        data = request.form
        from datetime import datetime

        due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()

        new_task = Task(
            title=data.get('title'),
            description=data.get('description'),
            priority=data.get('priority'),
            due_date=due_date,
            completed=False
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('tasks'))

    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)


@app.route('/tasks/<int:id>/complete')
def complete_task(id):
    task = Task.query.get_or_404(id)
    task.completed = True
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/tasks/<int:id>/delete')
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/api/tasks')
def api_tasks():
    open_tasks = Task.query.filter_by(completed=False).count()
    completed_tasks = Task.query.filter_by(completed=True).count()
    return jsonify(open=open_tasks, completed=completed_tasks)


@app.route('/stats')
def stats():
    # Logic to calculate and display task statistics
    total_tasks = Task.query.count()
    open_tasks = Task.query.filter_by(completed=False).count()
    completed_tasks = Task.query.filter_by(completed=True).count()
    return render_template('stats.html', total=total_tasks, open=open_tasks, completed=completed_tasks)


if __name__ == '__main__':
    app.run(debug=True)