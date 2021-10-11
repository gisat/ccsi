from datetime import datetime
from flask import g

from ccsi import db, auth
from ccsi import bcrypt


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def hash_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User ({self.id} , {self.email})"


@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datasetName = db.Column(db.String, nullable=False)
    products = db.relationship('Product', backref='dataset', lazy=True)

    def __repr__(self):
        return f"{self.datasetName}"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    productName = db.Column(db.String, nullable=False)
    path = db.Column(db.String, nullable=False)
    cache_date = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"), nullable=False)

    def __repr__(self):
        return f"User ({self.id} , {self.dataset})"


