"""
Daily Deadline Digest — Scheduled background task.

Runs once daily, checks deadlines due tomorrow (or within N days),
and either sends an email (if SMTP env vars are set) or prints/logs the digest.

Configuration (via .env or environment):
    DIGEST_DAYS         Days ahead to check (default 1 = due tomorrow)
    DIGEST_TIME         HH:MM to run daily (default "08:00")
    SMTP_HOST           e.g. "smtp.gmail.com"
    SMTP_PORT           e.g. 587
    SMTP_USER           Sender email address
    SMTP_PASS           Sender email password / app password
    NOTIFY_EMAIL        Recipient email address

Usage:
    from digest_scheduler import start_digest_scheduler
    start_digest_scheduler()   # call once at app startup
"""

import logging
import os
import smtplib
import threading
import time
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from deadline_db import get_upcoming_deadlines, format_deadlines_as_markdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------

def _build_email_body(deadlines: list) -> str:
    """Build a human-readable plain text + HTML email body."""
    today_str = date.today().strftime("%A, %B %d, %Y")
    days      = int(os.getenv("DIGEST_DAYS", "1"))

    plain_lines = [
        f"📅 Deadline Digest — {today_str}",
        f"Showing deadlines due within the next {days} day(s).\n",
    ]
    for d in deadlines:
        dl = d.get("days_left", "?")
        label = "TODAY" if dl == 0 else ("TOMORROW" if dl == 1 else f"in {dl} days")
        plain_lines.append(
            f"  • [{d['course_name']}] {d['assignment_name']} — due {d['due_date']} ({label})"
        )
    plain_lines.append("\n\nStay on top of your work! 💪")
    plain_text = "\n".join(plain_lines)

    # HTML version
    rows = ""
    for d in deadlines:
        dl = d.get("days_left", "?")
        label = "TODAY" if dl == 0 else ("TOMORROW" if dl == 1 else f"in {dl} days")
        color = "#ef4444" if dl == 0 else ("#f97316" if dl == 1 else "#eab308")
        rows += (
            f"<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #e5e7eb'>{d['course_name']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #e5e7eb'>{d['assignment_name']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #e5e7eb'>{d['due_date']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #e5e7eb;"
            f"color:{color};font-weight:bold'>{label}</td>"
            f"</tr>"
        )

    html = f"""
    <html><body style='font-family:Inter,Arial,sans-serif;background:#f9fafb;padding:20px'>
      <div style='max-width:600px;margin:auto;background:#fff;border-radius:12px;
                  padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.08)'>
        <h2 style='color:#6366f1'>📅 Deadline Digest</h2>
        <p style='color:#6b7280'>{today_str} — next {days} day(s)</p>
        <table style='width:100%;border-collapse:collapse'>
          <thead>
            <tr style='background:#f3f4f6'>
              <th style='padding:8px;text-align:left'>Course</th>
              <th style='padding:8px;text-align:left'>Assignment</th>
              <th style='padding:8px;text-align:left'>Due Date</th>
              <th style='padding:8px;text-align:left'>When</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style='margin-top:20px;color:#6b7280'>Stay on top of your work! 💪</p>
      </div>
    </body></html>"""

    return plain_text, html


def _send_email(deadlines: list) -> bool:
    """
    Send digest email via SMTP.

    Returns True on success, False if SMTP is not configured or sending fails.
    """
    smtp_host    = os.getenv("SMTP_HOST", "")
    smtp_port    = int(os.getenv("SMTP_PORT", "587"))
    smtp_user    = os.getenv("SMTP_USER", "")
    smtp_pass    = os.getenv("SMTP_PASS", "")
    notify_email = os.getenv("NOTIFY_EMAIL", "")

    if not all([smtp_host, smtp_user, smtp_pass, notify_email]):
        return False  # SMTP not configured — caller will log/print instead

    plain_text, html_text = _build_email_body(deadlines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📅 Deadline Digest — {len(deadlines)} upcoming"
    msg["From"]    = smtp_user
    msg["To"]      = notify_email
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_text,  "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, notify_email, msg.as_string())
        logger.info(f"📧 Digest email sent to {notify_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Digest logic
# ---------------------------------------------------------------------------

def run_digest() -> None:
    """
    Core digest action:
        1. Query upcoming deadlines.
        2. Try to send email.
        3. Fall back to print/log if SMTP not configured.
    """
    days      = int(os.getenv("DIGEST_DAYS", "1"))
    deadlines = get_upcoming_deadlines(days=days)

    if not deadlines:
        logger.info("🔔 Daily digest: no deadlines in the next %d day(s).", days)
        return

    logger.info("🔔 Daily digest: %d deadline(s) due soon.", len(deadlines))

    email_sent = _send_email(deadlines)

    if not email_sent:
        # Print to stdout / logs as fallback
        print("\n" + "=" * 60)
        print(f"📅 DEADLINE DIGEST — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        print(format_deadlines_as_markdown(deadlines))
        print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Background scheduler
# ---------------------------------------------------------------------------

def _scheduler_loop(run_time: str) -> None:
    """
    Background thread: runs the digest once per day at `run_time` (HH:MM).
    Uses a lightweight polling approach — no external `schedule` dependency.
    """
    logger.info(f"⏰ Digest scheduler started — will run daily at {run_time}")
    last_run_date = None

    while True:
        now  = datetime.now()
        hhmm = now.strftime("%H:%M")

        if hhmm == run_time and now.date() != last_run_date:
            logger.info("⏰ Running daily digest...")
            try:
                run_digest()
            except Exception as e:
                logger.error(f"Digest error: {e}")
            last_run_date = now.date()

        time.sleep(30)   # check every 30 seconds


def start_digest_scheduler() -> threading.Thread:
    """
    Start the daily digest as a daemon background thread.
    Call this once at application startup.

    Returns:
        The daemon Thread (already started).
    """
    run_time = os.getenv("DIGEST_TIME", "08:00")

    thread = threading.Thread(
        target=_scheduler_loop,
        args=(run_time,),
        daemon=True,          # dies when main process exits
        name="DeadlineDigest",
    )
    thread.start()
    logger.info(f"✅ Digest scheduler thread started (daily at {run_time})")
    return thread
