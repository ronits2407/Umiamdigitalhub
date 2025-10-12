# app.py
import os
from datetime import datetime, timedelta
from functools import wraps
# IMPORTANT: We now import render_template, not render_template_string
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, HiddenField, DateTimeLocalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- App and DB Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Custom Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'HMC Admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Models (Unchanged) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Student')
    # Updated columns to match schema
    name = db.Column(db.Text)
    roll_number = db.Column(db.Text)
    room_number = db.Column(db.Text)
    studying_year = db.Column(db.Text)  # Changed from Numeric to Text
    Branch = db.Column(db.Text)
    profile_pic_url = db.Column(db.Text)
    # ...existing relationships...

class UmiamStudent(db.Model):
    __tablename__ = 'umiam_students'
    email = db.Column(db.String(120), primary_key=True)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='announcements')

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Submitted')
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    complainant = db.relationship('User', backref='complaints') # Corrected relationship
    anonymous = db.Column(db.String(3), nullable=False, default='no')  # Add this line
    comments = db.Column(db.Text, nullable=True)  # Add this line

class Facility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    availability = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class AddStudentForm(FlaskForm):
    email = StringField('Student Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Add Student')

    def validate_email(self, email):
        student = UmiamStudent.query.filter_by(email=email.data.strip().lower()).first()
        if student:
            raise ValidationError('This email is already in the UMIAM student database.')

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.String(4), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), default='Normal')  # Normal, Important, Urgent
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Alumni(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_year = db.Column(db.String(4), nullable=False)
    current_position = db.Column(db.String(100))
    company = db.Column(db.String(100))
    linkedin = db.Column(db.String(200))
    email = db.Column(db.String(120))
    achievements = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    event = db.relationship('Event', backref='registrations')
    user = db.relationship('User', backref='event_registrations')

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Forms ---
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    # Updated fields to match schema
    name = StringField('Full Name', validators=[DataRequired()])
    roll_number = StringField('Roll Number', validators=[DataRequired()])
    room_number = StringField('Room Number', validators=[DataRequired()])
    studying_year = SelectField('Year of Study', choices=[
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
        ('Ph.D', 'Ph.D'),
        ('M.Tech', 'M.Tech')
    ], validators=[DataRequired()])
    Branch = SelectField('Branch', choices=[
        ('CSE', 'Computer Science'),
        ('ECE', 'Electronics'),
        ('ME', 'Mechanical'),
        ('CE', 'Civil')
    ], validators=[DataRequired()])
    verification_code = StringField('Verification Code', validators=[Optional()])
    role = SelectField('Role', choices=[('Student', 'Student'), ('HMC Admin', 'HMC Admin')], validators=[DataRequired()])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('That username is already taken.')
    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('That email is already in use.')
        if not email.data.lower().endswith('@iitg.ac.in'):
            raise ValidationError('Please use your official IITG email address.')
        email_data = email.data.strip().lower()
        student = UmiamStudent.query.filter_by(email=email_data).first()
        if not student:
            raise ValidationError('You are not am UMIAM resident, please contact an HMC member if you think this is an error. ')
    def validate_verification_code(self, field):
        if self.role.data == 'HMC Admin' and field.data != 'UMIAM-HMC':
            raise ValidationError('Invalid verification code.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ComplaintForm(FlaskForm):
    category = SelectField('Category', choices=[('Maintenance', 'Maintenance'), ('Mess/Food', 'Mess/Food'), ('Security', 'Security'), ('Internet', 'Internet'), ('Other', 'Other')], validators=[DataRequired()])
    details = TextAreaField('Details', validators=[DataRequired(), Length(min=10, max=500)])
    anonymous = SelectField('Submit as', choices=[
        ('no', 'Identify myself'), 
        ('yes', 'Submit anonymously')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit Complaint')

class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Update Announcement')
    add = SubmitField('Add Announcement')

class FacilityForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    availability = StringField('Availability', validators=[DataRequired()])
    image_url = StringField('Image URL')
    submit = SubmitField('Update Facility')

class NoticeForm(FlaskForm):
    message = StringField('Message', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('Normal', 'Normal'), ('Important', 'Important'), ('Urgent', 'Urgent')], validators=[DataRequired()])
    submit = SubmitField('Update Notice')

class AchievementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    year = StringField('Year', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    image_url = StringField('Image URL')
    submit = SubmitField('Add Achievement')

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    roll_number = StringField('Roll Number', validators=[DataRequired()])
    room_number = StringField('Room Number', validators=[DataRequired()])
    studying_year = SelectField('Year of Study', choices=[
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
        ('Ph.D', 'Ph.D'),
        ('M.Tech', 'M.Tech')
    ], validators=[DataRequired()])
    Branch = SelectField('Branch', choices=[
        ('CSE', 'Computer Science'),
        ('ECE', 'Electronics'),
        ('ME', 'Mechanical'),
        ('CE', 'Civil')
    ], validators=[DataRequired()])
    profile_pic_url = StringField('Profile Picture URL')
    submit = SubmitField('Update Profile')

class EventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_datetime = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_datetime = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    image_url = StringField('Image URL')
    submit = SubmitField('Create Event')

class AdminEditProfileForm(FlaskForm):
    roll_number = StringField('Roll Number', validators=[DataRequired()])
    room_number = StringField('Room Number', validators=[DataRequired()])
    studying_year = SelectField('Year of Study', choices=[
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
        ('Ph.D', 'Ph.D'),
        ('M.Tech', 'M.Tech')
    ], validators=[DataRequired()])
    Branch = SelectField('Branch', choices=[
        ('CSE', 'Computer Science'),
        ('ECE', 'Electronics'),
        ('ME', 'Mechanical'),
        ('CE', 'Civil')
    ], validators=[DataRequired()])
    profile_pic_url = StringField('Profile Picture URL')
    role = SelectField('Role', choices=[('Student', 'Student'), ('HMC Admin', 'HMC Admin')], validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class AlumniForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    batch_year = StringField('Batch Year', validators=[DataRequired()])
    current_position = StringField('Current Position', validators=[DataRequired()])
    company = StringField('Company')
    linkedin = StringField('LinkedIn Profile URL')
    email = StringField('Email', validators=[Optional(), Email()])
    achievements = TextAreaField('Achievements')
    image_url = StringField('Profile Image URL')
    submit = SubmitField('Save Alumni')

# --- Routes (MODIFIED to use render_template) ---
@app.route('/')
@app.route('/home')
def home():
    notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()
    return render_template('home.html', title='Home', notices=notices)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password,
            role=form.role.data,
            name=form.name.data,
            roll_number=form.roll_number.data,
            room_number=form.room_number.data,
            studying_year=form.studying_year.data,
            Branch=form.Branch.data
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    elif request.method == 'POST':
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    announcements = Announcement.query.order_by(Announcement.date_posted.desc()).limit(5).all()
    total_students = User.query.filter_by(role='Student').count()
    total_complaints = Complaint.query.count()
    resolved_complaints = Complaint.query.filter_by(status='Resolved').count()
    pending_complaints = total_complaints - resolved_complaints
    total_events = Event.query.count()
    total_facilities = Facility.query.count()
    total_alumni = Alumni.query.count()

    return render_template('dashboard.html', title='Dashboard',
                           announcements=announcements,
                           total_students=total_students,
                           total_complaints=total_complaints,
                           resolved_complaints=resolved_complaints,
                           pending_complaints=pending_complaints,
                           total_events=total_events,
                           total_facilities=total_facilities,
                           total_alumni=total_alumni)

@app.route('/submit_complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    form = ComplaintForm()
    if form.validate_on_submit():
        complaint = Complaint(
            category=form.category.data, 
            details=form.details.data, 
            complainant=current_user if form.anonymous.data == 'no' else None,
            anonymous=form.anonymous.data
        )
        # Adjust time to IST (+5:30)
        if complaint.submission_date is None:
            complaint.submission_date = datetime.utcnow()
        complaint.submission_date = complaint.submission_date + timedelta(hours=5, minutes=30)
        db.session.add(complaint)
        db.session.commit()
        flash('Your complaint has been submitted successfully!', 'success')
        return redirect(url_for('my_complaints'))
    return render_template('submit_complaint.html', title='Submit Complaint', form=form)

@app.route('/my_complaints')
@login_required
def my_complaints():
    user_complaints = Complaint.query.filter_by(complainant=current_user).order_by(Complaint.submission_date.desc()).all()
    return render_template('my_complaints.html', title='My Complaints', complaints=user_complaints)

@app.route('/admin/complaints')
@login_required
@admin_required
def admin_complaints():
    all_complaints = Complaint.query.order_by(Complaint.submission_date.desc()).all()
    return render_template('admin_complaints.html', title='Admin - All Complaints', complaints=all_complaints)

@app.route('/facilities')
def facilities():
    facilities = Facility.query.order_by(Facility.name).all()
    return render_template('facilities.html', title='Hostel Facilities', facilities=facilities)

@app.route('/achievements')
def achievements():
    achievements = Achievement.query.order_by(Achievement.year.desc()).all()
    return render_template('achievements.html', title='Hostel Achievements', achievements=achievements)

@app.route('/alumni')
def alumni():
    alumni_list = Alumni.query.order_by(Alumni.batch_year.desc()).all()
    return render_template('alumni.html', title='Alumni Network', alumni=alumni_list)

@app.route('/events')
@login_required
def events():
    events = Event.query.order_by(Event.start_datetime).all()
    return render_template('events.html', title='Events', events=events, EventRegistration=EventRegistration)

@app.route('/admin/announcement/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    form = AnnouncementForm(obj=announcement)
    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.content = form.content.data
        db.session.commit()
        flash('Announcement has been updated!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_announcement.html', title='Edit Announcement', form=form, announcement=announcement)

@app.route('/admin/facility/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_facility(id):
    facility = Facility.query.get_or_404(id)
    form = FacilityForm(obj=facility)
    if form.validate_on_submit():
        facility.name = form.name.data
        facility.description = form.description.data
        facility.location = form.location.data
        facility.availability = form.availability.data
        facility.image_url = form.image_url.data
        db.session.commit()
        flash('Facility has been updated!', 'success')
        return redirect(url_for('facilities'))
    return render_template('edit_facility.html', title='Edit Facility', form=form, facility=facility)

@app.route('/admin/notice/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_notice(id):
    notice = Notice.query.get_or_404(id)
    form = NoticeForm(obj=notice)
    if form.validate_on_submit():
        notice.message = form.message.data
        notice.priority = form.priority.data
        db.session.commit()
        flash('Notice has been updated!', 'success')
        return redirect(url_for('home'))
    return render_template('edit_notice.html', title='Edit Notice', form=form, notice=notice)

@app.route('/admin/notice/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_notice():
    form = NoticeForm()
    if form.validate_on_submit():
        notice = Notice(message=form.message.data, priority=form.priority.data)
        db.session.add(notice)
        db.session.commit()
        flash('Notice has been added!', 'success')
        return redirect(url_for('home'))
    return render_template('add_notice.html', title='Add Notice', form=form)

@app.route('/admin/announcement/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    form = AnnouncementForm()
    if form.add.data and form.validate():
        announcement = Announcement(title=form.title.data, content=form.content.data, author=current_user)
        # Adjust time to IST (+5:30)
        if announcement.date_posted is None:
            announcement.date_posted = datetime.utcnow()  # Initialize if None
        announcement.date_posted = announcement.date_posted + timedelta(hours=5, minutes=30)
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement has been added!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_announcement.html', title='Add Announcement', form=form)

@app.route('/admin/achievement/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_achievement():
    form = AchievementForm()
    if form.validate_on_submit():
        achievement = Achievement(
            title=form.title.data,
            description=form.description.data,
            year=form.year.data,
            category=form.category.data,
            image_url=form.image_url.data
        )
        db.session.add(achievement)
        db.session.commit()
        flash('Achievement has been added!', 'success')
        return redirect(url_for('achievements'))
    return render_template('add_achievement.html', title='Add Achievement', form=form)

@app.route('/admin/event/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            start_datetime=form.start_datetime.data,
            end_datetime=form.end_datetime.data,
            image_url=form.image_url.data
        )
        db.session.add(event)
        db.session.commit()
        flash('Event has been added!', 'success')
        return redirect(url_for('events'))
    return render_template('add_event.html', title='Add Event', form=form)

@app.route('/admin/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    form = AddStudentForm()
    if form.validate_on_submit():
        new_student = UmiamStudent(
            email=form.email.data.strip().lower()
        )
        db.session.add(new_student)
        db.session.commit()
        flash('Student email added successfully to the UMIAM database.', 'success')
        return redirect(url_for('add_student'))  # or redirect to admin dashboard
    return render_template('add_student.html', title='Add Student', form=form)


@app.route('/admin/facility/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_facility():
    form = FacilityForm()
    if form.validate_on_submit():
        facility = Facility(
            name=form.name.data,
            description=form.description.data,
            location=form.location.data,
            availability=form.availability.data,
            image_url=form.image_url.data
        )
        db.session.add(facility)
        db.session.commit()
        flash('Facility has been added!', 'success')
        return redirect(url_for('facilities'))
    return render_template('add_facility.html', title='Add Facility', form=form)

@app.route('/admin/event/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_event(id):
    event = Event.query.get_or_404(id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.location = form.location.data
        event.start_datetime = form.start_datetime.data
        event.end_datetime = form.end_datetime.data
        event.image_url = form.image_url.data
        db.session.commit()
        flash('Event has been updated!', 'success')
        return redirect(url_for('events'))
    return render_template('edit_event.html', title='Edit Event', form=form, event=event)

@app.route('/admin/announcement/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash('Announcement has been deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/complaint/status/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_complaint_status(id):
    complaint = Complaint.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status in ['Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed']:
        complaint.status = new_status
        db.session.commit()
        flash(f'Complaint status updated to {new_status}', 'success')
    return redirect(url_for('admin_complaints'))

@app.route('/profile/settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.roll_number = form.roll_number.data
        current_user.room_number = form.room_number.data
        current_user.studying_year = form.studying_year.data
        current_user.Branch = form.Branch.data
        if form.profile_pic_url.data:
            current_user.profile_pic_url = form.profile_pic_url.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile_settings'))
    return render_template('profile_settings.html', title='Profile Settings', form=form)

@app.route('/admin/event/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_event(id):
    event = Event.query.get_or_404(id)
    # Delete associated registrations
    EventRegistration.query.filter_by(event_id=event.id).delete()
    db.session.delete(event)
    db.session.commit()
    flash('Event has been deleted!', 'success')
    return redirect(url_for('events'))

@app.route('/event/register/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    registration = EventRegistration.query.filter_by(event_id=event.id, user_id=current_user.id).first()

    if registration:
        db.session.delete(registration)
        db.session.commit()
        flash('You have unregistered from the event.', 'info')
    else:
        registration = EventRegistration(event_id=event.id, user_id=current_user.id)
        db.session.add(registration)
        db.session.commit()
        flash('You have registered for the event!', 'success')

    return redirect(url_for('events'))

@app.route('/admin/event/registrations/<int:event_id>')
@login_required
@admin_required
def view_event_registrations(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = EventRegistration.query.filter_by(event_id=event.id).all()
    return render_template('event_registrations.html', title='Event Registrations', event=event, registrations=registrations)

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', title='Manage Users', users=users)

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminEditProfileForm(obj=user)
    if form.validate_on_submit():
        user.roll_number = form.roll_number.data
        user.room_number = form.room_number.data
        user.studying_year = form.studying_year.data
        user.Branch = form.Branch.data
        user.profile_pic_url = form.profile_pic_url.data
        user.role = form.role.data
        db.session.commit()
        flash('User information has been updated!', 'success')
        return redirect(url_for('manage_users'))
    return render_template('edit_user.html', title='Edit User', form=form, user=user)

@app.route('/admin/complaint/comment/<int:id>', methods=['POST'])
@login_required
@admin_required
def update_complaint_comment(id):
    complaint = Complaint.query.get_or_404(id)
    comment = request.form.get('comment')
    complaint.comments = comment
    db.session.commit()
    flash('Comment has been updated!', 'success')
    return redirect(url_for('admin_complaints'))

@app.route('/admin/facility/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_facility(id):
    facility = Facility.query.get_or_404(id)
    db.session.delete(facility)
    db.session.commit()
    flash('Facility has been deleted!', 'success')
    return redirect(url_for('facilities'))

@app.route('/admin/achievement/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_achievement(id):
    achievement = Achievement.query.get_or_404(id)
    form = AchievementForm(obj=achievement)
    if form.validate_on_submit():
        achievement.title = form.title.data
        achievement.description = form.description.data
        achievement.year = form.year.data
        achievement.category = form.category.data
        achievement.image_url = form.image_url.data
        db.session.commit()
        flash('Achievement has been updated!', 'success')
        return redirect(url_for('achievements'))
    return render_template('edit_achievement.html', title='Edit Achievement', form=form, achievement=achievement)

@app.route('/admin/achievement/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_achievement(id):
    achievement = Achievement.query.get_or_404(id)
    db.session.delete(achievement)
    db.session.commit()
    flash('Achievement has been deleted!', 'success')
    return redirect(url_for('achievements'))

@app.route('/admin/alumni/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_alumni():
    form = AlumniForm()
    if form.validate_on_submit():
        alumni = Alumni(
            name=form.name.data,
            batch_year=form.batch_year.data,
            current_position=form.current_position.data,
            company=form.company.data,
            linkedin=form.linkedin.data,
            email=form.email.data,
            achievements=form.achievements.data,
            image_url=form.image_url.data
        )
        db.session.add(alumni)
        db.session.commit()
        flash('Alumni has been added successfully!', 'success')
        return redirect(url_for('alumni'))
    return render_template('add_alumni.html', title='Add Alumni', form=form)

@app.route('/admin/alumni/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_alumni(id):
    alumni = Alumni.query.get_or_404(id)
    form = AlumniForm(obj=alumni)
    if form.validate_on_submit():
        alumni.name = form.name.data
        alumni.batch_year = form.batch_year.data
        alumni.current_position = form.current_position.data
        alumni.company = form.company.data
        alumni.linkedin = form.linkedin.data
        alumni.email = form.email.data
        alumni.achievements = form.achievements.data
        alumni.image_url = form.image_url.data
        db.session.commit()
        flash('Alumni information has been updated!', 'success')
        return redirect(url_for('alumni'))
    return render_template('add_alumni.html', title='Edit Alumni', form=form, alumni=alumni)

@app.route('/admin/alumni/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_alumni(id):
    alumni = Alumni.query.get_or_404(id)
    db.session.delete(alumni)
    db.session.commit()
    flash('Alumni has been deleted!', 'success')
    return redirect(url_for('alumni'))

# --- (All HTML Template strings have been removed from this file) ---

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)