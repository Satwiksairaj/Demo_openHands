from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blogs.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'

db.init_app(app)

@app.route('/')
def index():
    # Placeholder for main route
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
