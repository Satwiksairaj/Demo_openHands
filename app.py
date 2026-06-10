from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'

db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return jsonify(error="This URL is incorrect."), 404

if __name__ == '__main__':
    app.run(debug=True)