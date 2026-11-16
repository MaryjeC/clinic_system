"""
School Clinic Health Monitoring System
Run:  python app.py   then open http://127.0.0.1:5000
"""
import csv
import os
import re
import sqlite3
from collections import Counter
from datetime import date, datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   session, g)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"   # needed for sessions and flash messages

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "clinic_visits.csv")
DB_FILE = os.path.join(BASE_DIR, "users.db")   # user accounts are stored here
FIELDS = ["visit_id", "student_id", "age", "gender", "course", "complaint", "date"]

COURSES = ["BSIT", "BSCS", "BSN", "BSEd", "BSBA", "BSCrim", "BSHM"]
COMPLAINTS = ["Fever", "Headache", "Cough and Colds", "Stomachache", "Dysmenorrhea",
              "Dizziness", "Toothache", "Allergy", "Wound/Injury", "Asthma", "Other"]
AGE_GROUPS = ["17-18", "19-20", "21-22", "23-24", "25+"]


# ---------------------------------------------------------------
# 0. USER ACCOUNTS (SQLite database + login helpers)
# ---------------------------------------------------------------
def get_db():
    """Open a connection to users.db (one per request)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row      # lets us use row["username"]
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Close the database connection when the request is finished."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the users table if it doesn't exist yet."""
    with sqlite3.connect(DB_FILE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT NOT NULL,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
        """)


@app.before_request
def load_logged_in_user():
    """Before every page, check the session and remember who is logged in."""
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    """Put @login_required above a route to block visitors who aren't logged in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------
# 1. DATA FUNCTIONS (reading and writing the CSV file)
# ---------------------------------------------------------------
def load_visits():
    """Read every row of clinic_visits.csv and return a list of dictionaries."""
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        visits = list(csv.DictReader(f))
    for v in visits:
        v["age"] = int(v["age"])
    return visits


def next_visit_id(visits):
    """Make the next ID, e.g. CL450 -> CL451."""
    if not visits:
        return "CL001"
    last_number = max(int(v["visit_id"][2:]) for v in visits)
    return f"CL{last_number + 1:03d}"


def save_visit(visit):
    """Add one new visit to the end of the CSV file."""
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(visit)


# ---------------------------------------------------------------
# 2. ANALYSIS FUNCTIONS (KPIs and chart data)
# ---------------------------------------------------------------
def age_group(age):
    """Put an age into a group, e.g. 19 -> '19-20'."""
    if age <= 18:
        return "17-18"
    if age <= 20:
        return "19-20"
    if age <= 22:
        return "21-22"
    if age <= 24:
        return "23-24"
    return "25+"


def month_label(date_text):
    """'2026-09-01' -> 'Sep 2026'"""
    return datetime.strptime(date_text, "%Y-%m-%d").strftime("%b %Y")


def compute_kpis(visits):
    """The 4 KPIs: total visits, most common illness, male/female, monthly cases."""
    total = len(visits)
    complaints = Counter(v["complaint"] for v in visits)
    genders = Counter(v["gender"] for v in visits)
    months = Counter(v["date"][:7] for v in visits)          # '2026-09'

    top_illness, top_count = complaints.most_common(1)[0] if complaints else ("None", 0)
    latest_month = max(months) if months else None

    return {
        "total_visits": total,
        "top_illness": top_illness,
        "top_illness_count": top_count,
        "male": genders.get("Male", 0),
        "female": genders.get("Female", 0),
        "latest_month": month_label(latest_month + "-01") if latest_month else "-",
        "latest_month_cases": months.get(latest_month, 0),
        "avg_monthly": round(total / len(months), 1) if months else 0,
    }


def compute_charts(visits):
    """Data for the 4 charts, as labels + values lists that Chart.js can use."""
    illness = Counter(v["complaint"] for v in visits).most_common()

    months = Counter(v["date"][:7] for v in visits)
    month_keys = sorted(months)

    course = Counter(v["course"] for v in visits).most_common()

    ages = Counter(age_group(v["age"]) for v in visits)

    return {
        "illness":  {"labels": [k for k, _ in illness], "values": [n for _, n in illness]},
        "monthly":  {"labels": [month_label(m + "-01") for m in month_keys],
                     "values": [months[m] for m in month_keys]},
        "course":   {"labels": [k for k, _ in course], "values": [n for _, n in course]},
        "age":      {"labels": AGE_GROUPS, "values": [ages.get(g, 0) for g in AGE_GROUPS]},
    }


def filter_visits(visits, course="", gender="", month=""):
    """Keep only the visits that match the chosen filters (blank = all)."""
    result = visits
    if course:
        result = [v for v in result if v["course"] == course]
    if gender:
        result = [v for v in result if v["gender"] == gender]
    if month:
        result = [v for v in result if v["date"].startswith(month)]
    return result


# ---------------------------------------------------------------
# 3. ACCOUNT ROUTES (register, login, logout)
# ---------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))

    form = {}
    if request.method == "POST":
        form = request.form
        full_name = form.get("full_name", "").strip()
        username = form.get("username", "").strip().lower()
        password = form.get("password", "")
        confirm = form.get("confirm", "")
        errors = []

        if not full_name:
            errors.append("Full name is required.")
        if not re.fullmatch(r"[a-z0-9_]{4,20}", username):
            errors.append("Username must be 4-20 characters: letters, numbers or _ only.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        db = get_db()
        if not errors and db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            errors.append("That username is already taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            db.execute(
                "INSERT INTO users (full_name, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (full_name, username, generate_password_hash(password),
                 datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
            flash("Account created! You can log in now.", "success")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))

    form = {}
    if request.method == "POST":
        form = request.form
        username = form.get("username", "").strip().lower()
        password = form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect username or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            next_page = request.args.get("next", "")
            # only allow redirects inside this site
            if next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))

    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------
# 4. CLINIC ROUTES (the main pages; login required)
# ---------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    all_visits = load_visits()
    course = request.args.get("course", "")
    gender = request.args.get("gender", "")
    month = request.args.get("month", "")
    visits = filter_visits(all_visits, course, gender, month)

    month_options = sorted({v["date"][:7] for v in all_visits})
    recent = sorted(visits, key=lambda v: (v["date"], v["visit_id"]), reverse=True)[:5]
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return render_template(
        "dashboard.html",
        greeting=greeting,
        recent=recent,
        kpis=compute_kpis(visits),
        charts=compute_charts(visits),
        courses=COURSES,
        month_options=[(m, month_label(m + "-01")) for m in month_options],
        selected={"course": course, "gender": gender, "month": month},
    )


@app.route("/visits")
@login_required
def visit_list():
    visits = load_visits()
    search = request.args.get("q", "").strip().lower()
    complaint = request.args.get("complaint", "")
    if search:
        visits = [v for v in visits
                  if search in v["student_id"].lower() or search in v["visit_id"].lower()]
    if complaint:
        visits = [v for v in visits if v["complaint"] == complaint]
    visits = sorted(visits, key=lambda v: (v["date"], v["visit_id"]), reverse=True)
    return render_template("visits.html", visits=visits, complaints=COMPLAINTS,
                           search=search, selected_complaint=complaint)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_visit():
    if request.method == "POST":
        form = request.form
        errors = []

        student_id = form.get("student_id", "").strip().upper()
        if not student_id:
            errors.append("Student ID is required.")

        try:
            age = int(form.get("age", ""))
            if not 10 <= age <= 80:
                errors.append("Age must be between 10 and 80.")
        except ValueError:
            errors.append("Age must be a number.")
            age = None

        gender = form.get("gender", "")
        if gender not in ("Male", "Female"):
            errors.append("Please choose a gender.")

        course = form.get("course", "")
        if course not in COURSES:
            errors.append("Please choose a course.")

        complaint = form.get("complaint", "")
        if complaint == "Other":
            complaint = form.get("other_complaint", "").strip().title()
        if not complaint:
            errors.append("Please enter the complaint.")

        visit_date = form.get("date", "")
        try:
            datetime.strptime(visit_date, "%Y-%m-%d")
        except ValueError:
            errors.append("Please enter a valid date.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_visit.html", courses=COURSES,
                                   complaints=COMPLAINTS, form=form)

        visits = load_visits()
        new_visit = {
            "visit_id": next_visit_id(visits),
            "student_id": student_id,
            "age": age,
            "gender": gender,
            "course": course,
            "complaint": complaint,
            "date": visit_date,
        }
        save_visit(new_visit)
        flash(f"Visit {new_visit['visit_id']} saved for {student_id}.", "success")
        return redirect(url_for("visit_list"))

    return render_template("add_visit.html", courses=COURSES, complaints=COMPLAINTS,
                           form={"date": date.today().isoformat()})


init_db()   # make sure the users table exists when the app starts

if __name__ == "__main__":
    app.run(debug=True)
