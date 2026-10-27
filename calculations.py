"""
calculations.py
Contains pure business logic functions for FairShift:
- Shift hours & automatic overtime calculation
- Transparent payslip generation
- Safety hazard status lifecycle validation
- Worker fatigue and burnout detection

Keeping these functions pure (no database or web code) makes them simple,
clean, and 100% testable with pytest.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Overtime rule: Any shift longer than 8.0 hours counts as overtime
STANDARD_SHIFT_HOURS = 8.0

# Overtime rate multiplier (1.5x regular pay rate)
OVERTIME_MULTIPLIER = 1.5

# Valid hazard statuses in strict progression order
VALID_HAZARD_STATUSES = ["Reported", "In Review", "Fixed"]


def calculate_shift_hours(check_in: datetime, check_out: datetime) -> Tuple[float, float, float]:
    """
    Calculate regular, overtime, and total hours between check-in and check-out.
    Rule: Standard shift is up to 8.0 hours. Anything beyond is overtime.
    
    Returns:
        (regular_hours, overtime_hours, total_hours)
    """
    if check_out < check_in:
        raise ValueError("Check-out time cannot be earlier than check-in time.")

    # Calculate total duration in seconds and convert to hours
    duration_seconds = (check_out - check_in).total_seconds()
    total_hours = round(duration_seconds / 3600.0, 2)

    if total_hours <= STANDARD_SHIFT_HOURS:
        regular_hours = total_hours
        overtime_hours = 0.0
    else:
        regular_hours = STANDARD_SHIFT_HOURS
        overtime_hours = round(total_hours - STANDARD_SHIFT_HOURS, 2)

    return regular_hours, overtime_hours, total_hours


def calculate_payslip(
    hourly_rate: float,
    regular_hours: float,
    overtime_hours: float,
    multiplier: float = OVERTIME_MULTIPLIER
) -> Dict[str, Any]:
    """
    Generate a simple, 100% transparent payslip breakdown.
    - Base Pay = Regular Hours * Hourly Rate
    - Overtime Pay = Overtime Hours * (Hourly Rate * Multiplier)
    - Total Gross = Base Pay + Overtime Pay
    - Deductions = 0 (Unorganized workers often suffer from mystery deductions)
    """
    if hourly_rate < 0 or regular_hours < 0 or overtime_hours < 0:
        raise ValueError("Rates and hours cannot be negative.")

    base_pay = round(regular_hours * hourly_rate, 2)
    overtime_rate = round(hourly_rate * multiplier, 2)
    overtime_pay = round(overtime_hours * overtime_rate, 2)
    total_pay = round(base_pay + overtime_pay, 2)

    return {
        "hourly_rate": hourly_rate,
        "overtime_rate": overtime_rate,
        "regular_hours": regular_hours,
        "overtime_hours": overtime_hours,
        "total_hours": round(regular_hours + overtime_hours, 2),
        "base_pay": base_pay,
        "overtime_pay": overtime_pay,
        "deductions": 0.0,
        "total_pay": total_pay,
        "currency": "₹"
    }


def is_valid_hazard_transition(current_status: str, new_status: str) -> bool:
    """
    Check if a hazard status update follows the valid lifecycle:
    'Reported' -> 'In Review' -> 'Fixed'
    
    A status can stay the same, advance forward, but cannot move backwards.
    """
    if current_status not in VALID_HAZARD_STATUSES or new_status not in VALID_HAZARD_STATUSES:
        return False

    current_idx = VALID_HAZARD_STATUSES.index(current_status)
    new_idx = VALID_HAZARD_STATUSES.index(new_status)

    # Valid if advancing by 0 (same) or 1 step forward
    # Allow moving directly from Reported to Fixed if resolved immediately
    return new_idx >= current_idx


def detect_fatigue(shifts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate fatigue risk for a worker based on:
    1. Single shift exceeding 10 hours
    2. Weekly total hours exceeding 48 hours
    3. Less than 10 hours rest between consecutive shifts
    
    Returns a dictionary with risk level and human-readable reasons.
    """
    reasons = []
    risk_level = "Normal"
    is_fatigued = False

    if not shifts:
        return {
            "is_fatigued": False,
            "risk_level": "Normal",
            "reasons": ["No shift records found."]
        }

    # 1. Check for excessively long individual shifts (> 10 hours)
    for shift in shifts:
        total_hrs = shift.get("total_hours", 0.0)
        if total_hrs > 10.0:
            reasons.append(f"Excessive single shift: {total_hrs} hrs (exceeds safe 10h limit)")
            risk_level = "High Risk"
            is_fatigued = True

    # 2. Check cumulative hours in the given dataset (weekly hours)
    total_cumulative = sum(s.get("total_hours", 0.0) for s in shifts)
    if total_cumulative > 48.0:
        reasons.append(f"High cumulative hours: {round(total_cumulative, 1)} hrs (safe limit is 48h/week)")
        risk_level = "High Risk"
        is_fatigued = True
    elif total_cumulative > 40.0 and risk_level == "Normal":
        risk_level = "Moderate"

    # 3. Check for back-to-back shifts with insufficient rest (< 10 hours)
    sorted_shifts = sorted(
        [s for s in shifts if s.get("check_in") and s.get("check_out")],
        key=lambda x: x["check_in"]
    )
    for i in range(len(sorted_shifts) - 1):
        prev_end = sorted_shifts[i]["check_out"]
        next_start = sorted_shifts[i + 1]["check_in"]
        
        # Ensure they are datetime objects
        if isinstance(prev_end, str):
            prev_end = datetime.fromisoformat(prev_end)
        if isinstance(next_start, str):
            next_start = datetime.fromisoformat(next_start)

        rest_hours = (next_start - prev_end).total_seconds() / 3600.0
        if rest_hours < 10.0 and rest_hours >= 0:
            reasons.append(f"Insufficient rest between shifts: only {round(rest_hours, 1)}h rest")
            risk_level = "High Risk"
            is_fatigued = True

    if not reasons:
        reasons.append("Working hours are within safe labor standards.")

    return {
        "is_fatigued": is_fatigued,
        "risk_level": risk_level,
        "reasons": reasons
    }

