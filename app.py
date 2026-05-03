from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory
from models import db, User, Note, College
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret123'
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit
db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Ensure at least one college exists for the admin
    if not College.query.first():
        default_college = College(name="Main Campus")
        db.session.add(default_college)
        db.session.commit()

    # Auto-create Admin account if it doesn't exist
    if not User.query.filter_by(role='admin').first():
        college = College.query.first()
        admin_user = User(username='admin', email='admin@notehub.com', 
                          password='admin123', role='admin', 
                          college_id=college.id, is_verified=True)
        db.session.add(admin_user)
        db.session.commit()

@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/signin1", methods=["GET", "POST"])
def signin1():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        college_name = request.form.get('college')

        if password != confirm_password:
            return "Passwords do not match"

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            return "Email already registered"

        college = College.query.filter_by(name=college_name).first()
        if not college:
            college = College(name=college_name)
            db.session.add(college)
            db.session.commit()

        new_user = User(username=username, email=email, password=password, role=role, college_id=college.id)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template("register.html")


# HOME
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') == 'student':
        return redirect(url_for('student_dashboard'))
    
    # Teacher/Admin View: Filter notes by current user's college
    current_college_id = session.get('college_id')
    query = Note.query.filter_by(college_id=current_college_id)
    
    subject_filter = request.args.get('subject')
    if subject_filter:
        query = query.filter(Note.subject.ilike(f"%{subject_filter}%"))
        
    notes = query.order_by(Note.created_at.desc()).all()
    return render_template("notes.html", notes=notes, username=session.get('username'))


@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Multi-college isolation
    current_college_id = session.get('college_id')
    query = Note.query.filter_by(college_id=current_college_id)
    
    subject_filter = request.args.get('subject')
    if subject_filter:
        query = query.filter(Note.subject.ilike(f"%{subject_filter}%"))
        
    notes = query.order_by(Note.created_at.desc()).all()
    return render_template("student_dashboard.html", notes=notes, username=session.get('username'))


@app.route("/login")
def login():
    return render_template("login.html")



@app.route('/login1', methods=['POST'])
def login1():
    password = request.form.get('password')
    login_id = request.form.get('username')
    
    # Find user by username OR email and verify password
    user_data = User.query.filter(
        (User.username == login_id) | (User.email == login_id)
    ).filter_by(password=password).first()

    if user_data:
        session['username'] = user_data.username
        session['user_id'] = user_data.id
        session['email'] = user_data.email
        session['role'] = user_data.role
        session['college_id'] = user_data.college_id
        
        if user_data.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_data.role == 'student':
            return redirect('/student_dashboard')
        return redirect('/')
    else:
        return "Invalid credentials. Please register if you don't have an account."
    
@app.route("/create")
def create():
    return "upload 1 pan kon kel nahi "


@app.route("/upload")
def upload():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template('upload.html', user=user)

@app.route("/upload1", methods=["POST"])
def upload1():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    if not user.is_verified:
        return "Access Denied: Your account is pending verification."

    title = request.form.get('title')
    subject = request.form.get('subject')
    file = request.files.get("file")
    
    # Basic validation to prevent NOT NULL errors in database
    if not title or not subject:
        return "Error: Title and Subject are required fields."

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Enrich subject data from form selections (Class and Semester)
        note_class = request.form.get('class', 'N/A')
        semester = request.form.get('semester', 'N/A')
        full_subject = f"{subject} ({note_class} - {semester})"

        new_note = Note(
            title=title, 
            subject=full_subject, 
            file_path=filename, 
            college_id=user.college_id, 
            teacher_id=user.id
        )
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('home'))
    
    return "Invalid file. Only PDFs are allowed."

@app.route("/download/<int:note_id>")
def download_note(note_id):
    note = Note.query.get_or_404(note_id)
    note.download_count += 1
    db.session.commit()
    return send_from_directory(app.config['UPLOAD_FOLDER'], note.file_path)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, password=password, role='admin').first()
        if user:
            session['user_id'] = user.id
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))
    unverified_teachers = User.query.filter_by(role='teacher', is_verified=False).all()
    return render_template("admin_dashboard.html", users=unverified_teachers)

@app.route("/admin/approve/<int:user_id>")
def approve_teacher(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))
    user = User.query.get_or_404(user_id)
    user.is_verified = True
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/user")
def user():
    if 'user_id' not in session:
        return redirect('/login')
    
    users = User.query.all()
    return render_template("users.html", users=users)
    
@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('role', None)
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)