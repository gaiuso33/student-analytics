"""Business rules and settings. Override with environment variables."""
import os


class Config:
    DATABASE = os.environ.get("DATABASE", "students.db")
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]
    # Local development only (set by `python app.py`): also allow http://localhost:<any port> and
    # http://127.0.0.1:<any port>, so a Vite dev server that moved to another port still works.
    CORS_ALLOW_ANY_LOCALHOST = False
    # A record passes when score >= PASS_MARK (keep in sync with src/utils/grades.js)
    PASS_MARK = float(os.environ.get("PASS_MARK", 60))
    # A student is at risk when cumulative GPA is below this value
    AT_RISK_GPA = float(os.environ.get("AT_RISK_GPA", 2.0))
    # Fill an empty database with demo data on startup
    # Set SEED_DEMO_DATA=0 in production so fake students are never added to a real database.
    SEED_IF_EMPTY = os.environ.get("SEED_DEMO_DATA", "1").lower() in ("1", "true", "yes")

    # ---- insights ----
    # A student's semester GPA must move by at least this much to be called out as improving/declining.
    INSIGHT_GPA_CHANGE = float(os.environ.get("INSIGHT_GPA_CHANGE", 1.0))

    # ---- reminders ----
    # Follow-ups due within this many days (and overdue ones) "need attention".
    REMINDER_DAYS_AHEAD = int(os.environ.get("REMINDER_DAYS_AHEAD", 2))
    # Email digests (python manage.py send-reminders). Nothing is sent unless SMTP_HOST is set.
    SMTP_HOST = os.environ.get("SMTP_HOST") or None
    SMTP_PORT = int(os.environ.get("SMTP_PORT") or 587)
    SMTP_USER = os.environ.get("SMTP_USER") or None
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or None
    SMTP_SECURITY = (os.environ.get("SMTP_SECURITY") or "starttls").lower()  # starttls | ssl | none
    MAIL_FROM = os.environ.get("MAIL_FROM") or os.environ.get("SMTP_USER") or "no-reply@localhost"
    SITE_URL = (os.environ.get("SITE_URL") or "http://localhost:5173").rstrip("/")  # used for the link in emails
    # Emails say how many follow-ups need attention. Student names are only included when this is on.
    # Notes are never included.
    REMINDER_INCLUDE_NAMES = os.environ.get("REMINDER_INCLUDE_NAMES", "0").lower() in ("1", "true", "yes")

    # ---- bulk import ----
    MAX_IMPORT_ROWS = int(os.environ.get("MAX_IMPORT_ROWS", 5000))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # request size cap (bytes)

    # ---- authentication ----
    # Signs login tokens. Set a long random value in production (python -c "import secrets; print(secrets.token_hex(32))").
    # If unset, a random key is generated at startup and everyone is signed out on each restart.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", 8 * 3600))  # seconds
    # First-run admin account (only used when there are no users yet).
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")  # if unset, a random one is printed once
    # Optional read-only account created on first run (handy for sharing a demo without giving out the admin login).
    DEMO_VIEWER_USERNAME = os.environ.get("DEMO_VIEWER_USERNAME")
    DEMO_VIEWER_PASSWORD = os.environ.get("DEMO_VIEWER_PASSWORD")
    # Optional teacher account limited to the first class, to show class-level access in a demo.
    DEMO_STAFF_USERNAME = os.environ.get("DEMO_STAFF_USERNAME")
    DEMO_STAFF_PASSWORD = os.environ.get("DEMO_STAFF_PASSWORD")
    MIN_PASSWORD_LENGTH = 10
    LOGIN_MAX_FAILS = int(os.environ.get("LOGIN_MAX_FAILS", 5))
    LOGIN_LOCK_SECONDS = int(os.environ.get("LOGIN_LOCK_SECONDS", 60))
