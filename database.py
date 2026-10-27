"""
database.py
Handles SQLite database connection, table creation, and demo data seeding.
Everything uses parameterized queries (?, ?) to prevent SQL injection.
Passwords are safe and hashed with werkzeug.security.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# On Vercel, serverless containers have a read-only root directory.
# SQLite must write to /tmp to prevent "readonly database" errors.
if os.environ.get("VERCEL"):
    default_db = "/tmp/fairshift.db"
else:
    default_db = "fairshift.db"

DB_NAME = os.environ.get("DATABASE_PATH", default_db)


def get_db(db_path=None):
    """Returns a SQLite connection with dict-like row access."""
    path = db_path or DB_NAME
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Creates the necessary tables if they don't already exist."""
    conn = get_db(db_path)
    cursor = conn.cursor()

    # 1. Users table (Workers & Employers/Admins)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- 'worker' or 'admin'
            full_name TEXT NOT NULL,
            sector TEXT NOT NULL, -- 'Construction Site' or 'College'
            hourly_rate REAL DEFAULT 120.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Shifts table (Shift clock-in/out and automatic overtime hours)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            sector TEXT NOT NULL,
            check_in TIMESTAMP NOT NULL,
            check_out TIMESTAMP,
            regular_hours REAL DEFAULT 0.0,
            overtime_hours REAL DEFAULT 0.0,
            total_hours REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active', -- 'active' or 'completed'
            FOREIGN KEY (worker_id) REFERENCES users (id)
        );
    """)

    # 3. Safety hazards table (Hazard reporting with status lifecycle)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hazards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            worker_id INTEGER, -- nullable for anonymous submissions
            sector TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            hazard_type TEXT NOT NULL,
            severity TEXT NOT NULL, -- 'Low', 'Medium', 'High'
            status TEXT DEFAULT 'Reported', -- 'Reported', 'In Review', 'Fixed'
            admin_notes TEXT DEFAULT '',
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES users (id)
        );
    """)

    # 4. Anonymous feedback table (Pure anonymous workplace sentiment)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anonymous_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector TEXT NOT NULL,
            category TEXT NOT NULL,
            rating INTEGER NOT NULL, -- 1 to 5
            comments TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


def seed_demo_data(db_path=None):
    """
    Populates the database with realistic demo data across Construction & College sectors.
    Safe to call multiple times: only seeds if users table is empty.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM users;")
    user_count = cursor.fetchone()["count"]

    if user_count == 0:
        # Default hashed password for demo accounts
        admin_pass = generate_password_hash("admin123")
        worker_pass = generate_password_hash("worker123")

        # 1. Insert Demo Users
        users_data = [
            ("admin", admin_pass, "admin", "Karthik Raja (Supervisor)", "All", 0.0),
            ("ramu", worker_pass, "worker", "Ramu Kumar", "Construction Site", 125.0),
            ("priya", worker_pass, "worker", "Priya Selvam", "College", 110.0),
            ("murugan", worker_pass, "worker", "Murugan Velu", "Construction Site", 120.0),
        ]
        cursor.executemany("""
            INSERT INTO users (username, password_hash, role, full_name, sector, hourly_rate)
            VALUES (?, ?, ?, ?, ?, ?);
        """, users_data)

        # 2. Insert Demo Completed Shifts
        now = datetime.now()
        day1 = now - timedelta(days=3)
        day2 = now - timedelta(days=2)
        day3 = now - timedelta(days=1)

        shifts_data = [
            # Ramu: 2 days of good work (8 hrs and 9.5 hrs -> overtime demo!)
            (2, "Construction Site", day1.replace(hour=8, minute=0, second=0).isoformat(),
             day1.replace(hour=16, minute=0, second=0).isoformat(), 8.0, 0.0, 8.0, "completed"),
            (2, "Construction Site", day2.replace(hour=8, minute=0, second=0).isoformat(),
             day2.replace(hour=17, minute=30, second=0).isoformat(), 8.0, 1.5, 9.5, "completed"),

            # Priya: Normal 8 hrs shift in College
            (3, "College", day1.replace(hour=7, minute=0, second=0).isoformat(),
             day1.replace(hour=15, minute=0, second=0).isoformat(), 8.0, 0.0, 8.0, "completed"),
            (3, "College", day2.replace(hour=7, minute=0, second=0).isoformat(),
             day2.replace(hour=16, minute=30, second=0).isoformat(), 8.0, 1.5, 9.5, "completed"),

            # Murugan: Extreme shifts to immediately showcase Fatigue Detection!
            # 11.5 hours on Day 2, followed by another shift starting only 7 hours later!
            (4, "Construction Site", day2.replace(hour=7, minute=0, second=0).isoformat(),
             day2.replace(hour=18, minute=30, second=0).isoformat(), 8.0, 3.5, 11.5, "completed"),
            (4, "Construction Site", day3.replace(hour=1, minute=30, second=0).isoformat(),
             day3.replace(hour=13, minute=0, second=0).isoformat(), 8.0, 3.5, 11.5, "completed"),
        ]
        cursor.executemany("""
            INSERT INTO shifts (worker_id, sector, check_in, check_out, regular_hours, overtime_hours, total_hours, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, shifts_data)

        # 3. Insert Demo Sector-Specific Safety Hazards
        hazards_data = [
            ("FS-HAZ-101", 2, "Construction Site", "Loose scaffolding planks on 3rd floor",
             "Wooden planks on scaffold near Tower B are vibrating and unbolted.", "Scaffolding", "High", "In Review",
             "Inspection scheduled with site safety engineer."),
            ("FS-HAZ-102", 4, "Construction Site", "Frayed electrical winch cable",
             "Ground hoist cable has visible copper wire tear.", "Electrical", "High", "Fixed",
             "Cable replaced and winch tested by electrical supervisor."),
            ("FS-HAZ-103", 3, "College", "Wet slippery stairs near Central Library",
             "Water leak from AC drain line making marble steps dangerously slick.", "Slip/Trip", "Medium", "Reported",
             ""),
            ("FS-HAZ-104", 3, "College", "Broken glass pane on classroom fire exit door",
             "Shard of glass dangling from door frame in Block C corridor.", "Equipment", "Medium", "In Review",
             "Maintenance worker assigned to replace the glass sheet."),
        ]
        cursor.executemany("""
            INSERT INTO hazards (ticket_id, worker_id, sector, title, description, hazard_type, severity, status, admin_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, hazards_data)

        # 4. Insert Demo Anonymous Feedback
        feedback_data = [
            ("Construction Site", "Safety Gear", 4, "Helmets provided are good, but we need more heat reflective vests."),
            ("Construction Site", "Timely Pay", 5, "Overtime calculations are much clearer this month."),
            ("College", "Workplace Culture", 2, "Cleaning chemical fumes in lab restrooms need better exhaust fans."),
            ("College", "Manager Behavior", 5, "Supervisor Karthik listens politely and resolves shift swaps promptly."),
        ]
        cursor.executemany("""
            INSERT INTO anonymous_feedback (sector, category, rating, comments)
            VALUES (?, ?, ?, ?);
        """, feedback_data)

        conn.commit()

    conn.close()

