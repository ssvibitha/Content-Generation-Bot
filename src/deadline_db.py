"""
Deadline Database — SQLite storage for student deadlines.

Schema:
    deadlines(id, course_name, assignment_name, due_date, source_file, status, created_at)

Helper functions:
    init_db()                               — create table if not exists
    add_deadline(course, assignment,        — insert, skip duplicates
                 due_date, source_file)
    get_upcoming_deadlines(days=3)          — deadlines due within N days
    mark_done(assignment_name)              — set status = 'done'
    get_all_deadlines()                     — all rows as list of dicts
"""

import sqlite3
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Database lives at project root
_DB_PATH = Path(__file__).parent.parent / "deadlines.db"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the deadlines table if it does not already exist."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deadlines (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name     TEXT    NOT NULL,
                assignment_name TEXT    NOT NULL,
                due_date        TEXT    NOT NULL,   -- YYYY-MM-DD
                source_file     TEXT    DEFAULT '',
                status          TEXT    DEFAULT 'pending'
                                        CHECK(status IN ('pending', 'done')),
                created_at      TEXT    DEFAULT (date('now'))
            )
        """)
        conn.commit()
    logger.info(f"✅ Deadline DB initialised at: {_DB_PATH}")


def add_deadline(
    course: str,
    assignment: str,
    due_date: str,
    source_file: str = "",
) -> bool:
    """
    Insert a deadline record, skipping exact duplicates.

    Duplicate check: same (course_name, assignment_name, due_date).

    Returns:
        True  — row was inserted.
        False — duplicate, skipped.
    """
    with _get_connection() as conn:
        # Check for existing row
        existing = conn.execute(
            """
            SELECT id FROM deadlines
            WHERE course_name = ?
              AND assignment_name = ?
              AND due_date = ?
            """,
            (course.strip(), assignment.strip(), due_date.strip()),
        ).fetchone()

        if existing:
            logger.debug(
                f"Duplicate skipped: {course} / {assignment} / {due_date}"
            )
            return False

        conn.execute(
            """
            INSERT INTO deadlines
                (course_name, assignment_name, due_date, source_file, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (course.strip(), assignment.strip(), due_date.strip(), source_file),
        )
        conn.commit()
        logger.info(f"📌 Added deadline: [{course}] {assignment} → {due_date}")
        return True


def get_upcoming_deadlines(days: int = 3) -> List[Dict[str, Any]]:
    """
    Return pending deadlines due within the next `days` calendar days,
    sorted by due_date ascending.

    Args:
        days: Window in days from today (inclusive).

    Returns:
        List of dicts with keys:
            id, course_name, assignment_name, due_date,
            source_file, status, created_at, days_left
    """
    today = date.today()
    cutoff = today + timedelta(days=days)

    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM   deadlines
            WHERE  status   = 'pending'
              AND  due_date >= ?
              AND  due_date <= ?
            ORDER BY due_date ASC
            """,
            (today.isoformat(), cutoff.isoformat()),
        ).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        try:
            due = date.fromisoformat(d["due_date"])
            d["days_left"] = (due - today).days
        except ValueError:
            d["days_left"] = None
        result.append(d)

    return result


def mark_done(assignment_name: str) -> int:
    """
    Mark all pending deadlines whose assignment_name matches (case-insensitive)
    as 'done'.

    Returns:
        Number of rows updated.
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE deadlines
            SET    status = 'done'
            WHERE  LOWER(assignment_name) = LOWER(?)
              AND  status = 'pending'
            """,
            (assignment_name.strip(),),
        )
        conn.commit()
        count = cursor.rowcount
        logger.info(f"✅ Marked {count} deadline(s) done: '{assignment_name}'")
        return count


def get_all_deadlines() -> List[Dict[str, Any]]:
    """
    Return all deadline rows (pending and done), sorted by due_date ascending.
    """
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM deadlines ORDER BY due_date ASC"
        ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Formatting helpers (used by UI and MCP server)
# ---------------------------------------------------------------------------

def format_deadlines_as_markdown(deadlines: List[Dict[str, Any]]) -> str:
    """Render deadlines as a compact course-first list with due-date details."""
    if not deadlines:
        return "🎉 No upcoming deadlines — you're all caught up!"

    lines = []
    for d in deadlines:
        days_left = d.get("days_left")
        due_date = d.get("due_date", "")

        if days_left is None:
            dl_str = "?"
            day_label = "days"
        elif days_left == 0:
            dl_str = "0"
            day_label = "days"
        elif days_left == 1:
            dl_str = "1"
            day_label = "day"
        else:
            dl_str = str(days_left)
            day_label = "days"

        assignment = d.get("assignment_name", "")
        course = d.get("course_name", "")
        if assignment:
            title = f"{course} — {assignment}" if course else assignment
        else:
            title = course

        lines.append(f"- {title}")
        lines.append(f"  due in {dl_str} {day_label} ({due_date})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Init on import
# ---------------------------------------------------------------------------

init_db()
