from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, current_user, roles_required, hash_password
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail  # Updated to use flask_mail instead of flask_mailman
import config

app = Flask(__name__)
Bootstrap5(app)
app.config.from_object(config)
db = SQLAlchemy(app)

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)  # Added default value
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
    teacher = db.relationship('User', backref='courses_taught')  # Changed to 'courses_taught' for clarity

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    grade = db.Column(db.Float, nullable=True)  # Removed argument (40) from Float
    
    course = db.relationship('Course', backref='enrollments')
    student = db.relationship('User', backref='enrollments')

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

mail = Mail(app)

@app.route('/')
@login_required
def index():
    courses_count=Course.query.count()
    students_count=User.query.join(User.roles).filter(Role.name=='Students').count()
    teachers_count=User.query.join(User.roles).filter(Role.name=='Teachers').count()

    
    return render_template('index.html',courses_count=courses_count,students_count=students_count,teachers_count=teachers_count)

@app.route('/courses')
@login_required
def courses():
    if current_user.has_role('admin') or current_user.has_role('teacher'):
        courses = Course.query.all()
    else:
        courses = [current_user.enrollments for enronllment in current_user.enrollments]
    return render_template('courses.html', courses=courses)

@app.route('/courses/<int:course_id>', methods=['GET'])
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    return render_template('course_details.html', course=course, enrollments=enrollments)

@app.route('/create_course', methods=['GET', 'POST'])
@roles_required('admin')
def create_course():
    if request.method == 'POST':
        name = request.form['name']
        teacher_id = request.form['teacher_id']
        course = Course(name=name, teacher_id=teacher_id)
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully')
        return redirect(url_for('courses'))

    teachers = User.query.join(User.roles).filter(Role.name=='Teacher').all()
    return render_template('create_course.html', teachers=teachers)

@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()

    if enrollment:
        flash('You are already enrolled in this course')
    else:
        enrollment = Enrollment(student_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash('You have enrolled successfully in this course')  # Fixed typo

    return redirect(url_for('course_details', course_id=course_id))

@app.route('/grade/<int:enrollment_id>', methods=['GET', 'POST'])
@roles_required('teacher')
def grade(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    if enrollment.course.teacher_id != current_user.id:  # Changed comparison to teacher_id
        flash('You are not the teacher of this course')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':  # Ensure grade is updated only if form is submitted
        grade = request.form.get('grade')
        if grade:
            try:
                enrollment.grade = float(grade)
                db.session.commit()
                flash('Grade submitted successfully')
            except ValueError:
                flash('Invalid grade value')
        else:
            flash('No grade provided')
    
    return redirect(url_for('course_details', course_id=enrollment.course_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Create roles
        admin_role = user_datastore.find_or_create_role(name='Admin', description='Administrator')
        teacher_role = user_datastore.find_or_create_role(name='Teacher', description='Teacher')
        student_role = user_datastore.find_or_create_role(name='Student', description='Student')

        # Create users
        if not user_datastore.find_user(email='chelangatgladwel9@gmail.com'):
            hashed_password = hash_password('Gladwel 254')
            # Ensure roles are retrieved and not None
            admin_role = user_datastore.find_role('Admin')
            if admin_role:
                user_datastore.create_user(email='chelangatgladwel9@gmail.com', password=hashed_password, roles=[admin_role])
                db.session.commit()
            else:
                print("Admin role not found.")

            if not user_datastore.find_user(email='chelangatgladwel88@gmail.com'):
                hashed_password = hash_password('Gladwel 254')
            # Ensure roles are retrieved and not None
            admin_role = user_datastore.find_role('Admin')
            if teacher_role:
                user_datastore.create_user(email='chelangatgladwel88@gmail.com', password=hashed_password, roles=[teacher_role])
                db.session.commit()
            else:
                print("Teacher role not found.")        

    app.run(debug=True)
