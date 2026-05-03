"""
database.py
-----------
Handles all SQLite3 operations for the hospital queueing system.
Modules used: sqlite3, datetime, uuid
"""

import sqlite3
import datetime
import uuid
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mediqueue.db")

# ─── Priority constants ────────────────────────────────────────────────────────
PRIORITY_MAP = {
    "EMERGENCY": 1,
    "URGENT":    2,
    "REGULAR":   3,
}

PRIORITY_COLORS = {
    "EMERGENCY": "🔴",
    "URGENT":    "🟡",
    "REGULAR":   "🟢",
}

STATUS_OPEN       = "Waiting"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE       = "Served"
STATUS_CANCELLED  = "Cancelled"


def get_connection():
    """Return a SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id              TEXT PRIMARY KEY,
            ticket_number   TEXT NOT NULL,
            full_name       TEXT NOT NULL,
            age             INTEGER NOT NULL,
            sex             TEXT NOT NULL,
            contact         TEXT,
            chief_complaint TEXT NOT NULL,
            priority        TEXT NOT NULL,
            priority_level  INTEGER NOT NULL,
            department      TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'Waiting',
            registered_at   TEXT NOT NULL,
            called_at       TEXT,
            served_at       TEXT,
            notes           TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT UNIQUE NOT NULL
        )
    """)


    default_departments = [
        "General / OPD",
        "Emergency Room",
        "Pediatrics",
        "Cardiology",
        "Orthopedics",
        "OB-GYN",
        "Neurology",
        "Dermatology",
    ]
    for dept in default_departments:
        cursor.execute(
            "INSERT OR IGNORE INTO departments (name) VALUES (?)", (dept,)
        )

    conn.commit()
    conn.close()


# ─── Ticket number generation ──────────────────────────────────────────────────

def _generate_ticket(priority: str) -> str:
    """Generate a human-readable ticket number like E-001, U-005, R-012."""
    conn = get_connection()
    prefix = priority[0]  # E, U, R
    count = conn.execute(
        "SELECT COUNT(*) FROM patients WHERE priority = ?", (priority,)
    ).fetchone()[0]
    conn.close()
    return f"{prefix}-{count + 1:03d}"


# ─── CRUD operations ───────────────────────────────────────────────────────────

def register_patient(
    full_name: str,
    age: int,
    sex: str,
    contact: str,
    chief_complaint: str,
    priority: str,
    department: str,
    notes: str = "",
) -> dict:
    """Insert a new patient record. Returns the created patient as a dict."""
    conn = get_connection()
    patient_id     = str(uuid.uuid4())
    ticket_number  = _generate_ticket(priority)
    priority_level = PRIORITY_MAP[priority]
    registered_at  = datetime.datetime.now().isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO patients
            (id, ticket_number, full_name, age, sex, contact,
             chief_complaint, priority, priority_level, department,
             status, registered_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_id, ticket_number, full_name, age, sex, contact,
            chief_complaint, priority, priority_level, department,
            STATUS_OPEN, registered_at, notes,
        ),
    )
    conn.commit()

    patient = dict(conn.execute(
        "SELECT * FROM patients WHERE id = ?", (patient_id,)
    ).fetchone())
    conn.close()
    return patient


def get_queue(status_filter: list = None) -> list:
    """
    Return patients ordered by priority level then registration time.
    Optionally filter by a list of status strings.
    """
    conn = get_connection()
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        rows = conn.execute(
            f"""
            SELECT * FROM patients
            WHERE status IN ({placeholders})
            ORDER BY priority_level ASC, registered_at ASC
            """,
            status_filter,
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM patients
            ORDER BY priority_level ASC, registered_at ASC
            """
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_next_patient() -> dict | None:
    """Return the highest-priority waiting patient, or None."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT * FROM patients
        WHERE status = ?
        ORDER BY priority_level ASC, registered_at ASC
        LIMIT 1
        """,
        (STATUS_OPEN,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def call_patient(patient_id: str):
    """Mark a patient as In Progress and record the called_at time."""
    conn = get_connection()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE patients SET status = ?, called_at = ? WHERE id = ?",
        (STATUS_IN_PROGRESS, now, patient_id),
    )
    conn.commit()
    conn.close()


def serve_patient(patient_id: str):
    """Mark a patient as Served and record the served_at time."""
    conn = get_connection()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE patients SET status = ?, served_at = ? WHERE id = ?",
        (STATUS_DONE, now, patient_id),
    )
    conn.commit()
    conn.close()


def cancel_patient(patient_id: str):
    """Mark a patient as Cancelled."""
    conn = get_connection()
    conn.execute(
        "UPDATE patients SET status = ? WHERE id = ?",
        (STATUS_CANCELLED, patient_id),
    )
    conn.commit()
    conn.close()


def get_departments() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def get_stats() -> dict:
    """Return summary statistics for the analytics page."""
    conn = get_connection()

    total    = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    waiting  = conn.execute("SELECT COUNT(*) FROM patients WHERE status = 'Waiting'").fetchone()[0]
    in_prog  = conn.execute("SELECT COUNT(*) FROM patients WHERE status = 'In Progress'").fetchone()[0]
    served   = conn.execute("SELECT COUNT(*) FROM patients WHERE status = 'Served'").fetchone()[0]
    cancelled = conn.execute("SELECT COUNT(*) FROM patients WHERE status = 'Cancelled'").fetchone()[0]

    by_priority = conn.execute(
        "SELECT priority, COUNT(*) as cnt FROM patients GROUP BY priority"
    ).fetchall()

    by_dept = conn.execute(
        "SELECT department, COUNT(*) as cnt FROM patients GROUP BY department ORDER BY cnt DESC"
    ).fetchall()

    # Average wait time in minutes (registered_at → called_at)
    avg_wait_rows = conn.execute(
        """
        SELECT registered_at, called_at FROM patients
        WHERE called_at IS NOT NULL
        """
    ).fetchall()

    wait_times = []
    for row in avg_wait_rows:
        reg  = datetime.datetime.fromisoformat(row["registered_at"])
        call = datetime.datetime.fromisoformat(row["called_at"])
        wait_times.append((call - reg).total_seconds() / 60)

    avg_wait = round(sum(wait_times) / len(wait_times), 1) if wait_times else 0

    # Hourly registration breakdown
    hourly = conn.execute(
        """
        SELECT strftime('%H', registered_at) as hour, COUNT(*) as cnt
        FROM patients
        GROUP BY hour
        ORDER BY hour
        """
    ).fetchall()

    conn.close()

    return {
        "total":       total,
        "waiting":     waiting,
        "in_progress": in_prog,
        "served":      served,
        "cancelled":   cancelled,
        "by_priority": [dict(r) for r in by_priority],
        "by_dept":     [dict(r) for r in by_dept],
        "avg_wait_min": avg_wait,
        "hourly":      [dict(r) for r in hourly],
    }