"""
tests/test_fairshift.py
Unit tests using pytest to verify:
1. Shift hours & automatic overtime calculation
2. Transparent payslip math (base + 1.5x overtime)
3. Hazard lifecycle status transitions (Reported -> In Review -> Fixed)
4. Worker fatigue and burnout detection rules
5. Database initialization and demo seed verification
"""

import pytest
from datetime import datetime, timedelta
import os
import sqlite3

from calculations import (
    calculate_shift_hours,
    calculate_payslip,
    is_valid_hazard_transition,
    detect_fatigue
)
import database


# ==============================================================================
# 1. Tests for Shift & Automatic Overtime Calculation
# ==============================================================================

def test_standard_shift_under_eight_hours():
    """A shift under or equal to 8 hours should have zero overtime."""
    check_in = datetime(2026, 10, 27, 8, 0, 0)
    check_out = datetime(2026, 10, 27, 16, 0, 0) # Exactly 8 hours

    regular, overtime, total = calculate_shift_hours(check_in, check_out)
    assert total == 8.0
    assert regular == 8.0
    assert overtime == 0.0


def test_overtime_shift_above_eight_hours():
    """Any time beyond 8 hours must automatically be categorized as overtime."""
    check_in = datetime(2026, 10, 27, 8, 0, 0)
    check_out = datetime(2026, 10, 27, 18, 30, 0) # 10.5 hours

    regular, overtime, total = calculate_shift_hours(check_in, check_out)
    assert total == 10.5
    assert regular == 8.0
    assert overtime == 2.5


def test_invalid_checkout_before_checkin():
    """Check-out cannot be earlier than check-in."""
    check_in = datetime(2026, 10, 27, 16, 0, 0)
    check_out = datetime(2026, 10, 27, 8, 0, 0)

    with pytest.raises(ValueError):
        calculate_shift_hours(check_in, check_out)


# ==============================================================================
# 2. Tests for Transparent Payslip Calculation
# ==============================================================================

def test_payslip_breakdown():
    """Verifies that base pay and 1.5x overtime pay calculate with 100% transparency."""
    hourly_rate = 100.0  # ₹100 per hour
    regular_hours = 8.0
    overtime_hours = 2.0  # 2 hours overtime

    payslip = calculate_payslip(hourly_rate, regular_hours, overtime_hours)

    # Base pay: 8 * 100 = 800
    assert payslip["base_pay"] == 800.0
    # Overtime rate: 100 * 1.5 = 150
    assert payslip["overtime_rate"] == 150.0
    # Overtime pay: 2 * 150 = 300
    assert payslip["overtime_pay"] == 300.0
    # Total take-home pay: 800 + 300 = 1100
    assert payslip["total_pay"] == 1100.0
    # Zero mystery deductions
    assert payslip["deductions"] == 0.0


# ==============================================================================
# 3. Tests for Hazard Status Transitions
# ==============================================================================

def test_valid_hazard_status_transitions():
    """Status must advance: Reported -> In Review -> Fixed."""
    assert is_valid_hazard_transition("Reported", "In Review") is True
    assert is_valid_hazard_transition("In Review", "Fixed") is True
    assert is_valid_hazard_transition("Reported", "Fixed") is True # Direct resolution allowed
    assert is_valid_hazard_transition("Reported", "Reported") is True # Same status allowed


def test_invalid_hazard_status_transitions():
    """Status cannot move backwards or use arbitrary non-standard names."""
    assert is_valid_hazard_transition("Fixed", "Reported") is False
    assert is_valid_hazard_transition("Fixed", "In Review") is False
    assert is_valid_hazard_transition("Reported", "Cancelled") is False
    assert is_valid_hazard_transition("UnknownStatus", "Fixed") is False


# ==============================================================================
# 4. Tests for Worker Fatigue & Burnout Detection
# ==============================================================================

def test_fatigue_detection_single_shift_exceeded():
    """A single shift exceeding 10 hours must trigger a fatigue alert."""
    shifts = [
        {"total_hours": 11.5, "check_in": "2026-10-25T08:00:00", "check_out": "2026-10-25T19:30:00"}
    ]
    fatigue = detect_fatigue(shifts)
    assert fatigue["is_fatigued"] is True
    assert fatigue["risk_level"] == "High Risk"
    assert any("Excessive single shift" in reason for reason in fatigue["reasons"])


def test_fatigue_detection_weekly_cumulative_hours():
    """Working more than 48 hours weekly must flag fatigue."""
    shifts = [
        {"total_hours": 10.0},
        {"total_hours": 10.0},
        {"total_hours": 10.0},
        {"total_hours": 10.0},
        {"total_hours": 10.0}, # Total = 50 hours (> 48h limit)
    ]
    fatigue = detect_fatigue(shifts)
    assert fatigue["is_fatigued"] is True
    assert any("High cumulative hours" in reason for reason in fatigue["reasons"])


def test_fatigue_detection_back_to_back_shifts():
    """Less than 10 hours rest between shifts must trigger a fatigue alert."""
    shift1_end = datetime(2026, 10, 25, 20, 0, 0)
    shift2_start = datetime(2026, 10, 26, 3, 0, 0) # Only 7 hours rest!

    shifts = [
        {"total_hours": 8.0, "check_in": datetime(2026, 10, 25, 12, 0, 0), "check_out": shift1_end},
        {"total_hours": 8.0, "check_in": shift2_start, "check_out": datetime(2026, 10, 26, 11, 0, 0)}
    ]
    fatigue = detect_fatigue(shifts)
    assert fatigue["is_fatigued"] is True
    assert any("Insufficient rest between shifts" in reason for reason in fatigue["reasons"])


def test_normal_safe_shift_schedule():
    """Normal 8-hour shift with ample rest should NOT trigger fatigue."""
    shifts = [
        {
            "total_hours": 8.0,
            "check_in": datetime(2026, 10, 25, 8, 0, 0),
            "check_out": datetime(2026, 10, 25, 16, 0, 0)
        },
        {
            "total_hours": 8.0,
            "check_in": datetime(2026, 10, 26, 8, 0, 0), # 16 hours of rest!
            "check_out": datetime(2026, 10, 26, 16, 0, 0)
        }
    ]
    fatigue = detect_fatigue(shifts)
    assert fatigue["is_fatigued"] is False
    assert fatigue["risk_level"] == "Normal"


# ==============================================================================
# 5. Tests for Database Initialization & Seed Data
# ==============================================================================

def test_database_initialization_and_seeding(tmp_path):
    """Verifies that SQLite tables and cross-sector demo data initialize cleanly."""
    test_db = str(tmp_path / "test_fairshift.db")
    database.init_db(test_db)
    database.seed_demo_data(test_db)

    conn = database.get_db(test_db)
    cursor = conn.cursor()

    # Verify users created
    cursor.execute("SELECT COUNT(*) as count FROM users;")
    assert cursor.fetchone()["count"] >= 4

    # Verify both sectors are present
    cursor.execute("SELECT DISTINCT sector FROM users WHERE role = 'worker';")
    sectors = {row["sector"] for row in cursor.fetchall()}
    assert "Construction Site" in sectors
    assert "College" in sectors

    # Verify hazards created
    cursor.execute("SELECT COUNT(*) as count FROM hazards;")
    assert cursor.fetchone()["count"] >= 4

    conn.close()


# ==============================================================================
# 6. Tests for Flask Web Client & Routes
# ==============================================================================

@pytest.fixture
def client():
    """Provides a Flask test client with an in-memory/isolated database."""
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_login_and_worker_portal(client):
    """Test logging in as worker Ramu and accessing the worker portal."""
    # 1. Login
    resp = client.post("/login", data={"username": "ramu", "password": "worker123"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Ramu Kumar" in resp.data
    assert b"Construction Site" in resp.data

    # 2. Worker submits a hazard
    hazard_resp = client.post("/worker/report-hazard", data={
        "title": "Loose cable on floor",
        "description": "Cable crossing path near generator",
        "hazard_type": "Electrical",
        "severity": "High",
        "is_anonymous": "false"
    }, follow_redirects=True)
    assert hazard_resp.status_code == 200
    assert b"Hazard reported successfully" in hazard_resp.data


def test_admin_dashboard_access_and_filter(client):
    """Test logging in as admin and viewing the dashboard."""
    # 1. Login as admin
    resp = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Employer &amp; Safety Oversight Dashboard" in resp.data or b"Employer & Safety Oversight Dashboard" in resp.data
    assert b"Worker Fatigue &amp; Burnout Alerts" in resp.data or b"Worker Fatigue & Burnout Alerts" in resp.data

    # 2. Filter by College sector
    filter_resp = client.get("/admin?sector=College")
    assert filter_resp.status_code == 200
    assert b"Priya Selvam" in filter_resp.data

