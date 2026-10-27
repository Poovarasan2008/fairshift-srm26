"""
app.py
The main web server for FairShift - Decent Work Platform (UN SDG 8).
Connects the Worker mobile interface and the Employer/Admin dashboard
to the SQLite database.

Designed to be lightweight, easy to understand, and deployable to Google Cloud Run.
"""

import os
import random
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, jsonify
)
from werkzeug.security import check_password_hash

import database
from calculations import (
    calculate_shift_hours, calculate_payslip, is_valid_hazard_transition, detect_fatigue
)

# 1. Initialize Flask App
app = Flask(__name__)

# Security: Secret key comes from environment variable (zero hardcoded secrets)
app.secret_key = os.environ.get("SECRET_KEY", "fairshift-dev-secret-key-change-in-prod")

# Initialize database tables and seed demo data on startup
with app.app_context():
    database.init_db()
    database.seed_demo_data()


# ==============================================================================
# Helper Decorators for Authentication & Permissions
# ==============================================================================

def login_required(f):
    """Ensures a user must be logged in to view a page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Ensures only users with the 'admin' role can access the page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# Authentication Routes (Login & Logout)
# ==============================================================================

@app.route("/")
def index():
    """Home route redirects to the appropriate portal or login."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("worker_portal"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles simple login for both workers and managers."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        # Query database safely with parameterized query (prevents SQL injection)
        conn = database.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            # Save user session details
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            session["sector"] = user["sector"]
            session["hourly_rate"] = user["hourly_rate"]

            flash(f"Welcome back, {user['full_name']}!", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("worker_portal"))
        else:
            flash("Invalid username or password. Check demo credentials below.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clears the session and logs out."""
    session.clear()
    flash("You have successfully logged out.", "info")
    return redirect(url_for("login"))


# ==============================================================================
# Worker Portal Routes (Mobile-First, Big Buttons, Inclusivity)
# ==============================================================================

@app.route("/worker")
@login_required
def worker_portal():
    """Main worker interface: clock in/out, payslip, hazard reporting, tracking."""
    worker_id = session["user_id"]
    conn = database.get_db()
    cursor = conn.cursor()

    # 1. Check if the worker is currently clocked in (active shift)
    cursor.execute("""
        SELECT * FROM shifts 
        WHERE worker_id = ? AND status = 'active' 
        ORDER BY id DESC LIMIT 1;
    """, (worker_id,))
    active_shift = cursor.fetchone()

    # 2. Fetch completed shifts for this worker
    cursor.execute("""
        SELECT * FROM shifts 
        WHERE worker_id = ? AND status = 'completed' 
        ORDER BY id DESC LIMIT 10;
    """, (worker_id,))
    past_shifts = cursor.fetchall()

    # 3. Calculate worker's cumulative payslip
    total_reg = sum(s["regular_hours"] for s in past_shifts)
    total_ot = sum(s["overtime_hours"] for s in past_shifts)
    hourly_rate = session.get("hourly_rate", 120.0)
    payslip = calculate_payslip(hourly_rate, total_reg, total_ot)

    # 4. Fetch hazards submitted by this worker (for status tracking)
    cursor.execute("""
        SELECT * FROM hazards 
        WHERE worker_id = ? 
        ORDER BY id DESC;
    """, (worker_id,))
    my_hazards = cursor.fetchall()

    conn.close()

    return render_template(
        "worker.html",
        active_shift=active_shift,
        past_shifts=past_shifts,
        payslip=payslip,
        my_hazards=my_hazards
    )


@app.route("/worker/clock-in", methods=["POST"])
@login_required
def clock_in():
    """Clock in for a shift."""
    worker_id = session["user_id"]
    sector = session.get("sector", "General")

    conn = database.get_db()
    cursor = conn.cursor()

    # Verify worker isn't already clocked in
    cursor.execute("SELECT id FROM shifts WHERE worker_id = ? AND status = 'active';", (worker_id,))
    existing = cursor.fetchone()

    if existing:
        flash("You are already clocked in!", "warning")
    else:
        now_iso = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO shifts (worker_id, sector, check_in, status)
            VALUES (?, ?, ?, 'active');
        """, (worker_id, sector, now_iso))
        conn.commit()
        flash("Successfully clocked in! Have a safe shift.", "success")

    conn.close()
    return redirect(url_for("worker_portal"))


@app.route("/worker/clock-out", methods=["POST"])
@login_required
def clock_out():
    """Clock out and automatically compute regular and overtime hours."""
    worker_id = session["user_id"]
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM shifts 
        WHERE worker_id = ? AND status = 'active' 
        ORDER BY id DESC LIMIT 1;
    """, (worker_id,))
    active_shift = cursor.fetchone()

    if not active_shift:
        flash("No active shift found to clock out.", "warning")
    else:
        check_in_dt = datetime.fromisoformat(active_shift["check_in"])
        check_out_dt = datetime.now()
        
        # Calculate regular hours and automatic overtime using our pure calculations module
        regular_hrs, overtime_hrs, total_hrs = calculate_shift_hours(check_in_dt, check_out_dt)

        cursor.execute("""
            UPDATE shifts 
            SET check_out = ?, regular_hours = ?, overtime_hours = ?, total_hours = ?, status = 'completed'
            WHERE id = ?;
        """, (check_out_dt.isoformat(), regular_hrs, overtime_hrs, total_hrs, active_shift["id"]))
        conn.commit()

        msg = f"Shift completed! Logged: {total_hrs} hrs (Standard: {regular_hrs} hrs"
        if overtime_hrs > 0:
            msg += f" + Overtime: {overtime_hrs} hrs at 1.5x pay!)"
        else:
            msg += ")"
        flash(msg, "success")

    conn.close()
    return redirect(url_for("worker_portal"))


@app.route("/worker/report-hazard", methods=["POST"])
@login_required
def report_hazard():
    """Worker submits a workplace safety hazard (via text or voice transcription)."""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    hazard_type = request.form.get("hazard_type", "General").strip()
    severity = request.form.get("severity", "Medium").strip()
    is_anonymous = request.form.get("is_anonymous") == "true"

    if not title or not description:
        flash("Please provide both a title and description for the hazard.", "danger")
        return redirect(url_for("worker_portal"))

    worker_id = None if is_anonymous else session["user_id"]
    sector = session.get("sector", "General")
    ticket_id = f"FS-HAZ-{random.randint(1000, 9999)}"

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hazards (ticket_id, worker_id, sector, title, description, hazard_type, severity, status, admin_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Reported', '');
    """, (ticket_id, worker_id, sector, title, description, hazard_type, severity))
    conn.commit()
    conn.close()

    flash(f"Hazard reported successfully! Your Tracking Ticket ID is {ticket_id}.", "success")
    return redirect(url_for("worker_portal"))


@app.route("/worker/feedback", methods=["POST"])
@login_required
def submit_feedback():
    """Worker submits 100% anonymous feedback to improve work conditions."""
    category = request.form.get("category", "General").strip()
    comments = request.form.get("comments", "").strip()
    try:
        rating = int(request.form.get("rating", 3))
    except ValueError:
        rating = 3

    if not comments:
        flash("Please write a comment or suggestion.", "danger")
        return redirect(url_for("worker_portal"))

    sector = session.get("sector", "General")

    conn = database.get_db()
    cursor = conn.cursor()
    # Note: Worker ID is completely omitted! Anonymity is guaranteed by schema.
    cursor.execute("""
        INSERT INTO anonymous_feedback (sector, category, rating, comments)
        VALUES (?, ?, ?, ?);
    """, (sector, category, rating, comments))
    conn.commit()
    conn.close()

    flash("Your anonymous feedback has been recorded safely.", "success")
    return redirect(url_for("worker_portal"))


# ==============================================================================
# Employer / Admin Dashboard Routes (Visibility, Fatigue Alerts, Safety)
# ==============================================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    """Employer dashboard with cross-industry sector filter and analytics."""
    sector_filter = request.args.get("sector", "All")

    conn = database.get_db()
    cursor = conn.cursor()

    # 1. Fetch Workers (Filtered by sector if selected)
    if sector_filter and sector_filter != "All":
        cursor.execute("SELECT * FROM users WHERE role = 'worker' AND sector = ?;", (sector_filter,))
    else:
        cursor.execute("SELECT * FROM users WHERE role = 'worker';")
    workers = cursor.fetchall()

    # 2. Fetch Shifts & Run Fatigue Detection for Each Worker
    fatigue_alerts = []
    total_hours_sum = 0.0
    total_ot_sum = 0.0

    for worker in workers:
        cursor.execute("""
            SELECT * FROM shifts 
            WHERE worker_id = ? AND status = 'completed'
            ORDER BY check_in ASC;
        """, (worker["id"],))
        worker_shifts = [dict(s) for s in cursor.fetchall()]

        # Accumulate metrics
        total_hours_sum += sum(s.get("total_hours", 0.0) for s in worker_shifts)
        total_ot_sum += sum(s.get("overtime_hours", 0.0) for s in worker_shifts)

        # Run Fatigue Detection algorithm
        fatigue_info = detect_fatigue(worker_shifts)
        if fatigue_info["is_fatigued"]:
            fatigue_alerts.append({
                "worker_name": worker["full_name"],
                "sector": worker["sector"],
                "risk_level": fatigue_info["risk_level"],
                "reasons": fatigue_info["reasons"]
            })

    # 3. Fetch Safety Hazards (Filtered by sector if applicable)
    if sector_filter and sector_filter != "All":
        cursor.execute("""
            SELECT h.*, u.full_name as reporter_name 
            FROM hazards h 
            LEFT JOIN users u ON h.worker_id = u.id 
            WHERE h.sector = ? 
            ORDER BY h.id DESC;
        """, (sector_filter,))
    else:
        cursor.execute("""
            SELECT h.*, u.full_name as reporter_name 
            FROM hazards h 
            LEFT JOIN users u ON h.worker_id = u.id 
            ORDER BY h.id DESC;
        """)
    hazards = cursor.fetchall()

    # 4. Fetch Anonymous Feedback
    if sector_filter and sector_filter != "All":
        cursor.execute("SELECT * FROM anonymous_feedback WHERE sector = ? ORDER BY id DESC;", (sector_filter,))
    else:
        cursor.execute("SELECT * FROM anonymous_feedback ORDER BY id DESC;")
    feedbacks = cursor.fetchall()

    # Metrics Summary
    open_hazards_count = sum(1 for h in hazards if h["status"] != "Fixed")

    conn.close()

    return render_template(
        "admin.html",
        selected_sector=sector_filter,
        workers=workers,
        hazards=hazards,
        feedbacks=feedbacks,
        fatigue_alerts=fatigue_alerts,
        total_hours=round(total_hours_sum, 1),
        total_ot=round(total_ot_sum, 1),
        open_hazards_count=open_hazards_count
    )


@app.route("/admin/update-hazard", methods=["POST"])
@admin_required
def update_hazard():
    """Admin updates the status and notes for a safety hazard."""
    hazard_id = request.form.get("hazard_id")
    new_status = request.form.get("status")
    admin_notes = request.form.get("admin_notes", "").strip()

    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM hazards WHERE id = ?;", (hazard_id,))
    hazard = cursor.fetchone()

    if not hazard:
        flash("Hazard ticket not found.", "danger")
    else:
        current_status = hazard["status"]
        if is_valid_hazard_transition(current_status, new_status):
            cursor.execute("""
                UPDATE hazards 
                SET status = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?;
            """, (new_status, admin_notes, hazard_id))
            conn.commit()
            flash(f"Hazard status updated from '{current_status}' to '{new_status}'.", "success")
        else:
            flash(f"Invalid status transition from '{current_status}' to '{new_status}'.", "warning")

    conn.close()
    return redirect(url_for("admin_dashboard"))


# ==============================================================================
# Google Cloud Run Entry Point
# ==============================================================================

if __name__ == "__main__":
    # Google Cloud Run injects the PORT environment variable (default: 8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

