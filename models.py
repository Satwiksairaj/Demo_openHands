from sqlalchemy import Column, Integer, String, Boolean, Date
from extensions import db


class Task(db.Model):
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(String(200), nullable=True)
    priority = Column(String(10), nullable=False)
    due_date = Column(Date, nullable=True)
    completed = Column(Boolean, default=False)
