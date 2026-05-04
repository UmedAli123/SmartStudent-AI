from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Student, Mark, Attendance, PredictionHistory
from ml_engine import MLEngine
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'smart-stu-secret-key-123')

# Database Configuration (PostgreSQL for Render, SQLite for Local)
uri = os.environ.get('DATABASE_URL', 'sqlite:///students.db')
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

ml_engine = MLEngine()
ml_engine.load()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    student_count = Student.query.count()
    prediction_count = PredictionHistory.query.count()
    high_risk_count = PredictionHistory.query.filter_by(risk_level='High').count()
    
    recent_students = Student.query.order_by(Student.id.desc()).limit(5).all()
    return render_template('dashboard.html', 
                           student_count=student_count, 
                           prediction_count=prediction_count, 
                           high_risk_count=high_risk_count,
                           recent_students=recent_students)

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if request.method == 'POST':
        name = request.form.get('name')
        roll = request.form.get('roll_number')
        email = request.form.get('email')
        contact = request.form.get('contact')
        
        # New ML features
        age = int(request.form.get('age', 17))
        gender = int(request.form.get('gender', 1))
        ethnicity = int(request.form.get('ethnicity', 0))
        parental_edu = int(request.form.get('parental_education', 2))
        study_time = float(request.form.get('study_time', 10.0))

        new_student = Student(
            name=name, 
            roll_number=roll, 
            email=email, 
            contact=contact,
            age=age,
            gender=gender,
            ethnicity=ethnicity,
            parental_education=parental_edu,
            study_time=study_time
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully!', 'success')
        return redirect(url_for('students'))
        
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/student/delete/<int:id>')
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash('Student record deleted.', 'info')
    return redirect(url_for('students'))

@app.route('/entry/<int:student_id>', methods=['GET', 'POST'])
@login_required
def entry(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        # Attendance
        status = request.form.get('attendance_status')
        absences = int(request.form.get('absences', 0))
        
        # Marks
        quiz = float(request.form.get('quiz', 0))
        assign = float(request.form.get('assignment', 0))
        mid = float(request.form.get('midterm', 0))
        final = float(request.form.get('final', 0))
        
        # Calculation
        total = quiz + assign + mid + final
        perc = (total / 400) * 100 # Assuming 400 total
        
        grade = 'F'
        if perc >= 80: grade = 'A'
        elif perc >= 70: grade = 'B'
        elif perc >= 60: grade = 'C'
        elif perc >= 50: grade = 'D'
        
        # Save Marks
        mark = Mark(student_id=student.id, quiz_score=quiz, assignment_score=assign, 
                    midterm_score=mid, final_score=final, total_marks=total, 
                    percentage=perc, grade=grade)
        
        # Save Attendance (Simplified for this demo)
        att = Attendance(student_id=student.id, date=datetime.utcnow().date(), 
                         status=status, absences_count=absences)
        
        db.session.add(mark)
        db.session.add(att)
        db.session.commit()
        
        flash('Academic data recorded!', 'success')
        return redirect(url_for('predict', student_id=student.id))
        
    return render_template('entry.html', student=student)

@app.route('/predict/<int:student_id>')
@login_required
def predict(student_id):
    student = Student.query.get_or_404(student_id)
    latest_att = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.id.desc()).first()
    absences = latest_att.absences_count if latest_att else 10 # Default to 10 if none
    
    # Prepare input for ML model
    # Features: Age, Gender, Ethnicity, ParentalEducation, StudyTimeWeekly, 
    # Absences, Tutoring, ParentalSupport, Extracurricular, Sports, Music, Volunteering
    input_data = {
        'Age': student.age or 17,
        'Gender': student.gender or 1,
        'Ethnicity': student.ethnicity or 0,
        'ParentalEducation': student.parental_education or 2,
        'StudyTimeWeekly': student.study_time or 10.0,
        'Absences': absences,
        'Tutoring': 1 if student.study_time > 15 else 0, # Logic mapping
        'ParentalSupport': 3, # Default mid
        'Extracurricular': 0,
        'Sports': 0,
        'Music': 0,
        'Volunteering': 0
    }
    
    result = ml_engine.predict(input_data)
    
    # Save History
    history = PredictionHistory(
        student_id=student.id,
        predicted_grade=result['predicted_grade'],
        risk_level=result['risk_level'],
        input_data_snapshot=json.dumps(input_data)
    )
    db.session.add(history)
    db.session.commit()
    
    return render_template('predict.html', student=student, result=result)

@app.route('/history')
@login_required
def history():
    all_history = PredictionHistory.query.order_by(PredictionHistory.prediction_date.desc()).all()
    return render_template('history.html', history=all_history)

@app.route('/history/clear')
@login_required
def clear_history():
    PredictionHistory.query.delete()
    db.session.commit()
    flash('All prediction history has been cleared.', 'info')
    return redirect(url_for('history'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create a default user if none exists
        if not User.query.filter_by(email='admin@example.com').first():
            admin = User(
                email='admin@example.com',
                name='Admin Teacher',
                password=generate_password_hash('admin123', method='pbkdf2:sha256')
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True, port=5001)
