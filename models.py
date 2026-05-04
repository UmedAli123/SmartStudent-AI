from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='Teacher') # Teacher or Admin

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    age = db.Column(db.Integer)
    gender = db.Column(db.Integer) # 0: Female, 1: Male
    ethnicity = db.Column(db.Integer)
    parental_education = db.Column(db.Integer)
    study_time = db.Column(db.Float) # Weekly study time
    
    marks = db.relationship('Mark', backref='student', lazy=True, cascade="all, delete-orphan")
    attendance = db.relationship('Attendance', backref='student', lazy=True, cascade="all, delete-orphan")
    predictions = db.relationship('PredictionHistory', backref='student', lazy=True, cascade="all, delete-orphan")

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    quiz_score = db.Column(db.Float, default=0.0)
    assignment_score = db.Column(db.Float, default=0.0)
    midterm_score = db.Column(db.Float, default=0.0)
    final_score = db.Column(db.Float, default=0.0)
    total_marks = db.Column(db.Float, default=0.0)
    percentage = db.Column(db.Float, default=0.0)
    grade = db.Column(db.String(2))
    date_entered = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10)) # 'Present' or 'Absent'
    absences_count = db.Column(db.Integer, default=0) # Total absences for prediction logic

class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    predicted_grade = db.Column(db.String(2))
    risk_level = db.Column(db.String(20))
    input_data_snapshot = db.Column(db.Text) # JSON string of inputs used
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow)
