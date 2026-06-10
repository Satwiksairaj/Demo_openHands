from extensions import db

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
