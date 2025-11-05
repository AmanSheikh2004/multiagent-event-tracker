from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # student, teacher, iqc
    department = db.Column(db.String(120), nullable=True)  # AIML, CSE(Core), ALL

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(400), nullable=False)
    uploaded_by = db.Column(db.String(120), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, needs_review, saved, failed
    raw_text = db.Column(db.Text, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

class ExtractedEntity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    label = db.Column(db.String(100))  # EVENT_NAME, DATE, DEPARTMENT, CATEGORY
    text = db.Column(db.Text)
    confidence = db.Column(db.Float, default=0.0)

    document = db.relationship('Document', backref='entities')

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    name = db.Column(db.String(500))
    date = db.Column(db.Date)
    department = db.Column(db.String(120))
    category = db.Column(db.String(120))  # Faculty Event, Student Event, Student Quiz
    validated = db.Column(db.Boolean, default=False)

    document = db.relationship('Document', backref='events')
