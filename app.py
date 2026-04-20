from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret123'
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20)) # 'student' or 'teacher'

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

with app.app_context():
    db.create_all()



@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/signin1", methods=["GET", "POST"])
def signin1():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            return "Passwords do not match"

        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            return "Email already registered"

        new_user = User(email=email, password=password, role=role)

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
        return redirect('/student_dashboard')
    return render_template("notes.html", data=[])


@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('role') == 'teacher':
        return redirect('/')
    
    notes = Note.query.order_by(Note.created_at.desc()).all()
    return render_template("student_dashboard.html", notes=notes, username=session.get('email'))


@app.route("/login")
def login():
    return render_template("login.html")



@app.route('/login1', methods=['POST'])
def login1():
    email = request.form.get('email')  
    password = request.form.get('password')
    role = request.form.get('role')

    user_data = User.query.filter_by(email=email, password=password, role=role).first()

    if user_data:
        session['user_id'] = user_data.id
        session['email'] = user_data.email
        session['role'] = user_data.role
        if user_data.role == 'student':
            return redirect('/student_dashboard')
        return redirect('/')
    else:
        return "Invalid credentials. Please register if you don't have an account."

@app.route("/create")
def create():
    return "upload 1 pan kon kel nahi "


@app.route("/upload")
def upload():
    return render_template('upload.html')

@app.route("/upload1", methods=["POST"])
def upload1():
    file = request.files["file"]
    
    if file:
        filename = secure_filename(file.filename)
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('home'))
    
    return "No File Selected"


if __name__ == "__main__":
    app.run(debug=True)