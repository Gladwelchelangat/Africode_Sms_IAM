from flask import Flask, render_template, request, url_for, redirect, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, current_user, roles_required, hash_password
from flask_mailman import Mail
import config

app = Flask(__name__)
Bootstrap5(app)
app.config.from_object(config)
db = SQLAlchemy(app)

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True)
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    webauthn = db.relationship('WebAuth', backref='user', uselist=False)

class WebAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher = db.relationship('User', backref='course_taught')  # Fixed: Changed 'user' to 'User'

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship('Course', backref='enrollment')
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student = db.relationship('User', backref='enrollments')
    grade = db.Column(db.Float, nullable=True)  # Fixed: Changed db.Float(225) to db.Float

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)
mail = Mail(app)

@app.route('/')
@login_required
def index():
    courses_count = Course.query.count()
    students_count = User.query.join(User.roles).filter(Role.name == 'Student').count()
    teachers_count = User.query.join(User.roles).filter(Role.name == 'Teacher').count()
    return render_template('index.html',courses_count = courses_count, students_count = students_count, teachers_count = teachers_count)

@app.route('/courses')
@login_required
def courses():
    if current_user.has_role('Admin') or current_user.has_role('Teacher'):
        courses = Course.query.all()
    else:
        # Fetch all courses for students to allow them to enroll in courses they're not already in
        courses = Course.query.all()

    return render_template('courses.html', courses=courses)



@app.route('/course/<int:course_id>')
@login_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    
    return render_template('course_details.html', course=course)  


@app.route('/create_course', methods=['GET', 'POST'])
@roles_required('Admin')
def create_course():
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        course = Course(name=name, teacher_id=teacher_id)
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!')
        return redirect(url_for('courses'))
    teachers = User.query.join(roles_users).join(User.roles).filter(Role.name == 'Teacher').all()  # Fixed: Corrected query for filtering teachers
    return render_template('create_course.html', teachers=teachers)

@app.route('/enroll/<int:course_id>', methods=['GET', 'POST'])
@roles_required('Student')  # Only students can access this route
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    if Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first():
        flash('You are already enrolled in this course!')
    else:
        enrollment = Enrollment(course_id=course_id, student_id=current_user.id)
        db.session.add(enrollment)
        db.session.commit()
        flash('You have been enrolled in this course!')
    
    return redirect(url_for('course_details', course_id=course_id))



@app.route('/grade/<int:enrollment_id>', methods=['GET', 'POST'])
@roles_required('Teacher')
def grade(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    
    # Check if the current user is the teacher of the course
    if enrollment.course.teacher_id != current_user.id:
        flash('You are not the teacher of this course')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':
        grade = request.form.get('grade')
        if grade:
            try:
                grade_value = float(grade)
                if 0 <= grade_value <= 100:  # Example range check
                    enrollment.grade = grade_value
                    db.session.commit()
                    flash('Grade submitted successfully')
                else:
                    flash('Grade must be between 0 and 100')
            except ValueError:
                flash('Invalid grade value')
        else:
            flash('No grade provided')
    
    return redirect(url_for('course_details', course_id=enrollment.course_id))


@app.route('/register_student', methods=['GET', 'POST'])
@roles_required('Admin')
def register_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
        else:
            student_role = user_datastore.find_role('Student')
            hashed_password = hash_password(password)
            user_datastore.create_user(email=email, password=hashed_password, roles=[student_role])
            db.session.commit()
            flash('Student registered successfully!')
        return redirect(url_for('register_student'))
    return render_template('register_student.html')
@app.route('/manage_students')
@roles_required('Teacher')
def manage_students():
    # Fetch the courses taught by the current teacher
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('manage_students.html', courses=courses)

@app.route('/manage_courses')
@roles_required('Teacher')
def manage_courses():
    # Fetch the courses taught by the current teacher
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('manage_course.html', courses=courses)



@app.route('/grade_course/<int:course_id>', methods=['GET', 'POST'])
@roles_required('Teacher')
def grade_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if the current user is the teacher of this course
    if course.teacher_id != current_user.id:
        flash('You are not the teacher of this course')
        return redirect(url_for('manage_students'))
    
    # Fetch all enrollments for this course
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    
    return render_template('grade_course.html', course=course, enrollments=enrollments)

@app.route('/view_grades')
@roles_required('Student')  # Only students should access this page
@login_required
def view_grades():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    return render_template('view_grades.html', enrollments=enrollments)
@app.route('/view_students_in_course/<int:course_id>')
@roles_required('Teacher')
@login_required
def view_students_in_course(course_id):
    course = Course.query.get_or_404(course_id)
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    return render_template('view_students_in_course.html', course=course, enrollments=enrollments)
@app.route('/add_material/<int:course_id>', methods=['GET', 'POST'])
@roles_required('Teacher')
@login_required
def add_material(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        # Handle form submission to add material
        material = request.form.get('material')
        # Add logic to save the material for the course
        
        flash('Material added successfully!')
        return redirect(url_for('manage_courses'))
    
    return render_template('add_material.html', course=course)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # create roles
        user_datastore.find_or_create_role(name='Admin', description='Administrator')
        user_datastore.find_or_create_role(name='Teacher', description='Teacher')
        user_datastore.find_or_create_role(name='Student', description='Student')

        # create users
        if not user_datastore.find_user(email='chelangatgladwel9@gmail.com'):
            hashed_password = hash_password('Gladwel 254')
            user_datastore.create_user(email='chelangatgladwel9@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Admin')])
            db.session.commit()

        if not user_datastore.find_user(email='chelangatgladwel88@gmail.com'):
            hashed_password = hash_password('Gladwel 254')
            user_datastore.create_user(email='chelangatgladwel88@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Teacher')])
            db.session.commit()

        if not user_datastore.find_user(email='enockbett427@gmail.com'):
            hashed_password = hash_password('password')
            user_datastore.create_user(email='enockbett427@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Student')])
            db.session.commit()


    app.run( port=8000,debug=True)