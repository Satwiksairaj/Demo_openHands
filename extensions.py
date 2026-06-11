from flask_sqlalchemy import SQLAlchemy

# Create the SQLAlchemy db instance
# This is imported by both the application factory and models
# Making sure that db is only ever initialized once
db = SQLAlchemy()
