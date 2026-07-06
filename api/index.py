"""
Student Management System - Flask Application
Entry point for Vercel serverless deployment (@vercel/python) and for
local development (see main.py in the project root).
"""
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# --- Database URL handling -------------------------------------------------
# Neon / most managed Postgres providers hand out URLs prefixed with
# "postgres://". SQLAlchemy 1.4+ / psycopg2 require "postgresql://".
db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'local.db')}")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url

# --- Engine/pool tuning ------------------------------------------------------
# On Vercel each request may run in its own short-lived function instance, so
# SQLAlchemy's own connection pool can't be reused across invocations anyway.
# For Postgres we hand pooling off to Neon's built-in PgBouncer (use the
# "-pooler" connection string from the Neon dashboard) and disable SQLAlchemy's
# local pool with NullPool, so every request opens/closes cleanly against the
# pooler instead of holding a stale connection. For local SQLite dev, a
# regular pool with pool_recycle is fine since there's a single long-running
# process.
is_postgres = db_url.startswith("postgresql")

if is_postgres:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": NullPool,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10,
            # Disable server-side prepared statement caching — PgBouncer's
            # transaction pooling mode (which Neon's pooler uses) doesn't
            # support prepared statements persisting across statements.
            "options": "-c statement_timeout=15000",
        },
    }
else:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

PER_PAGE = 10


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Staff")  # 'Admin' | 'Staff'

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    father_name = db.Column(db.String(120), nullable=False)
    program = db.Column(db.String(80), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --------------------------------------------------------------------------
# Auth helpers / decorators
# --------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "Admin":
            flash("You do not have permission to perform this action.", "danger")
            return redirect(url_for("students"))
        return view_func(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {
        "current_user_name": session.get("username"),
        "current_user_role": session.get("role"),
    }


# --------------------------------------------------------------------------
# Bootstrap: create tables + seed a default admin + sample students (idempotent)
# --------------------------------------------------------------------------
SAMPLE_STUDENTS = [
    # roll_no, name, father_name, program, semester, section, phone, address
    ("CS-101", "Ahmed Hassan", "Muhammad Hassan", "BS Computer Science", 3, "A", "03001234567", "House 12, Street 4, Saddiqabad, Punjab"),
    ("CS-102", "Fatima Zahra", "Imran Zahra", "BS Computer Science", 3, "A", "03011234568", "House 45, Model Town, Lahore, Punjab"),
    ("CS-103", "Bilal Sheikh", "Anwar Sheikh", "BS Computer Science", 5, "B", "03021234569", "House 8, Satellite Town, Rawalpindi, Punjab"),
    ("CS-104", "Ayesha Malik", "Tariq Malik", "BS Computer Science", 1, "A", "03031234570", "House 21, Gulberg, Lahore, Punjab"),
    ("CS-105", "Usman Farooq", "Farooq Ahmed", "BS Computer Science", 7, "A", "03041234571", "House 3, DHA Phase 5, Karachi, Sindh"),
    ("SE-201", "Zainab Riaz", "Riaz Ahmed", "BS Software Engineering", 2, "A", "03051234572", "House 17, Township, Lahore, Punjab"),
    ("SE-202", "Hamza Iqbal", "Iqbal Nasir", "BS Software Engineering", 4, "B", "03061234573", "House 30, Johar Town, Lahore, Punjab"),
    ("SE-203", "Sana Aslam", "Aslam Khan", "BS Software Engineering", 6, "A", "03071234574", "House 5, Cantt, Multan, Punjab"),
    ("SE-204", "Umar Siddiqui", "Siddiqui Anwar", "BS Software Engineering", 2, "B", "03081234575", "House 9, Faisal Town, Lahore, Punjab"),
    ("BBA-301", "Mariam Yousaf", "Yousaf Khan", "BS Business Administration", 5, "A", "03091234576", "House 14, Bahria Town, Islamabad"),
    ("BBA-302", "Ali Raza", "Raza Muhammad", "BS Business Administration", 1, "A", "03101234577", "House 22, G-9, Islamabad"),
    ("BBA-303", "Hira Shahid", "Shahid Mehmood", "BS Business Administration", 3, "B", "03111234578", "House 6, Askari 10, Lahore, Punjab"),
    ("EE-401", "Danish Elahi", "Elahi Bakhsh", "BS Electrical Engineering", 6, "A", "03121234579", "House 11, Wapda Town, Lahore, Punjab"),
    ("EE-402", "Noor Fatima", "Fatima Hussain", "BS Electrical Engineering", 4, "A", "03131234580", "House 19, Samanabad, Lahore, Punjab"),
    ("EE-403", "Kashif Mahmood", "Mahmood Sarwar", "BS Electrical Engineering", 8, "B", "03141234581", "House 2, Cantt, Sialkot, Punjab"),
    ("MATH-501", "Rabia Aziz", "Aziz Ahmad", "BS Mathematics", 2, "A", "03151234582", "House 27, Green Town, Lahore, Punjab"),
    ("MATH-502", "Junaid Akhtar", "Akhtar Javed", "BS Mathematics", 5, "A", "03161234583", "House 4, Iqbal Town, Faisalabad, Punjab"),
    ("MATH-503", "Sadia Kausar", "Kausar Pervaiz", "BS Mathematics", 7, "B", "03171234584", "House 33, Model Colony, Karachi, Sindh"),
    ("CS-106", "Waqas Ahmed", "Ahmed Bashir", "BS Computer Science", 1, "B", "03181234585", "House 16, Peoples Colony, Faisalabad, Punjab"),
    ("SE-205", "Amna Tariq", "Tariq Rasheed", "BS Software Engineering", 8, "A", "03191234586", "House 40, Cavalry Ground, Lahore, Punjab"),
]


def seed_students():
    if Student.query.count() > 0:
        return
    for roll_no, name, father_name, program, semester, section, phone, address in SAMPLE_STUDENTS:
        db.session.add(Student(
            roll_no=roll_no,
            name=name,
            father_name=father_name,
            program=program,
            semester=semester,
            section=section,
            phone=phone,
            address=address,
        ))
    db.session.commit()


def init_db():
    db.create_all()
    if User.query.count() == 0:
        admin = User(username="admin", email="admin@example.com", role="Admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
    seed_students()


with app.app_context():
    init_db()


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    total_students = Student.query.count()

    program_breakdown = (
        db.session.query(Student.program, db.func.count(Student.id))
        .group_by(Student.program)
        .order_by(db.func.count(Student.id).desc())
        .all()
    )

    recent_students = (
        Student.query.order_by(Student.created_at.desc()).limit(5).all()
    )

    total_programs = len(program_breakdown)

    return render_template(
        "dashboard.html",
        total_students=total_students,
        program_breakdown=program_breakdown,
        recent_students=recent_students,
        total_programs=total_programs,
    )


# --------------------------------------------------------------------------
# Students - list / search / filter / paginate
# --------------------------------------------------------------------------
@app.route("/students")
@login_required
def students():
    search = request.args.get("q", "").strip()
    program_filter = request.args.get("program", "").strip()
    semester_filter = request.args.get("semester", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Student.query

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Student.name.ilike(like), Student.roll_no.ilike(like)))

    if program_filter:
        query = query.filter(Student.program == program_filter)

    if semester_filter:
        query = query.filter(Student.semester == int(semester_filter))

    query = query.order_by(Student.created_at.desc())
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    all_programs = [p[0] for p in db.session.query(Student.program).distinct().all()]

    return render_template(
        "students.html",
        students=pagination.items,
        pagination=pagination,
        search=search,
        program_filter=program_filter,
        semester_filter=semester_filter,
        all_programs=all_programs,
    )


def _validate_student_form(form):
    """Returns (data_dict, errors_list)."""
    errors = []
    data = {
        "roll_no": form.get("roll_no", "").strip(),
        "name": form.get("name", "").strip(),
        "father_name": form.get("father_name", "").strip(),
        "program": form.get("program", "").strip(),
        "semester": form.get("semester", "").strip(),
        "section": form.get("section", "").strip(),
        "phone": form.get("phone", "").strip(),
        "address": form.get("address", "").strip(),
    }

    required_fields = [
        "roll_no", "name", "father_name", "program",
        "semester", "section", "phone", "address",
    ]
    for field in required_fields:
        if not data[field]:
            errors.append(f"{field.replace('_', ' ').title()} is required.")

    if data["semester"]:
        try:
            data["semester"] = int(data["semester"])
            if not (1 <= data["semester"] <= 12):
                errors.append("Semester must be between 1 and 12.")
        except ValueError:
            errors.append("Semester must be a valid number.")

    if data["phone"] and not (data["phone"].replace("+", "").replace("-", "").isdigit()):
        errors.append("Phone number contains invalid characters.")

    return data, errors


@app.route("/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "GET":
        return render_template("student_form.html", mode="add", student=None)

    data, errors = _validate_student_form(request.form)
    if errors:
        for e in errors:
            flash(e, "danger")
        return render_template("student_form.html", mode="add", student=data)

    student = Student(**data)
    try:
        db.session.add(student)
        db.session.commit()
        flash(f"Student '{student.name}' added successfully.", "success")
        return redirect(url_for("students"))
    except IntegrityError:
        db.session.rollback()
        flash(f"Roll number '{data['roll_no']}' already exists. Please use a unique roll number.", "danger")
        return render_template("student_form.html", mode="add", student=data)


@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == "GET":
        return render_template("student_form.html", mode="edit", student=student)

    data, errors = _validate_student_form(request.form)
    if errors:
        for e in errors:
            flash(e, "danger")
        merged = {**data, "id": student_id}
        return render_template("student_form.html", mode="edit", student=merged)

    try:
        student.roll_no = data["roll_no"]
        student.name = data["name"]
        student.father_name = data["father_name"]
        student.program = data["program"]
        student.semester = data["semester"]
        student.section = data["section"]
        student.phone = data["phone"]
        student.address = data["address"]
        db.session.commit()
        flash(f"Student '{student.name}' updated successfully.", "success")
        return redirect(url_for("students"))
    except IntegrityError:
        db.session.rollback()
        flash(f"Roll number '{data['roll_no']}' already exists. Please use a unique roll number.", "danger")
        merged = {**data, "id": student_id}
        return render_template("student_form.html", mode="edit", student=merged)


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    name = student.name
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{name}' deleted.", "info")
    return redirect(url_for("students"))


@app.route("/students/report")
@login_required
def students_report():
    search = request.args.get("q", "").strip()
    program_filter = request.args.get("program", "").strip()
    semester_filter = request.args.get("semester", "").strip()

    query = Student.query

    if search:
        like = f"%{search}%"
        query = query.filter(or_(Student.name.ilike(like), Student.roll_no.ilike(like)))
    if program_filter:
        query = query.filter(Student.program == program_filter)
    if semester_filter:
        query = query.filter(Student.semester == int(semester_filter))

    report_students = query.order_by(Student.program, Student.semester, Student.name).all()

    return render_template(
        "students_report.html",
        students=report_students,
        generated_at=datetime.utcnow(),
        filters={"q": search, "program": program_filter, "semester": semester_filter},
    )


# --------------------------------------------------------------------------
# Local dev entry point (also used by Vercel via `app` module-level object)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
