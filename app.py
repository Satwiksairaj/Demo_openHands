from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def index():
    return 'Hello, Expense Tracker!'  # Placeholder route

if __name__ == '__main__':
    app.run(debug=True)
