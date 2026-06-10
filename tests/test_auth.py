import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from models import db, User, Expense
from datetime import date

@pytest.fixture
def app():
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['WTF_CSRF_ENABLED'] = False
    
    db.init_app(test_app)
    bcrypt = Bcrypt(test_app)
    login_manager = LoginManager(test_app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from flask import request, redirect, url_for
    from flask_login import login_user, logout_user
    
    @test_app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            if User.query.filter_by(email=email).first():
                return redirect(url_for('register'))
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
        return 'Register Page'
    
    @test_app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home'))
        return 'Login Page'
    
    @test_app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('login'))
    
    @test_app.route('/')
    def home():
        return 'Home Page'
    
    with test_app.app_context():
        db.create_all()
    
    return test_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_register(client, app):
    with app.app_context():
        response = client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 302
        assert User.query.filter_by(email='test@example.com').first() is not None

def test_login(client, app):
    with app.app_context():
        client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 302

def test_logout(client, app):
    with app.app_context():
        client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        response = client.get('/logout')
        assert response.status_code == 302

def test_duplicate_registration(client, app):
    with app.app_context():
        client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        response = client.post('/register', data={
            'email': 'test@example.com',
            'password': 'password456'
        })
        assert response.status_code == 302
        assert User.query.filter_by(email='test@example.com').count() == 1
