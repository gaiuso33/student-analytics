import secrets
import sqlite3
import sys
import time
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db
from validation import ValidationError, clean_username, password_problem

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

PUBLIC_PATHS = {"/api/health", "/api/auth/login"}
# Used to spend the same time on unknown usernames as on real ones.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def error(status, code, message, **extra):
    return jsonify(error=code, message=message, **extra), status


def public_user(row):
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


# ---------- tokens ----------
def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")


def make_token(user):
    return _serializer().dumps({"uid": user["id"], "v": user["token_version"]})


def user_from_token(token):
    try:
        data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except BadSignature:  # includes SignatureExpired
        return None
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (data.get("uid"),)).fetchone()
    if row is None or not row["active"] or row["token_version"] != data.get("v"):
        return None
    return row


def authenticate():
    """before_request hook: every /api route except health and login needs a valid bearer token."""
    if request.method == "OPTIONS" or not request.path.startswith("/api/") or request.path in PUBLIC_PATHS:
        return None
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.startswith("Bearer ") else ""
    user = user_from_token(token) if token else None
    if user is None:
        return error(401, "unauthorized", "Please sign in.")
    g.user = user
    return None


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            return error(403, "forbidden", "You don't have permission to do that.")
        return view(*args, **kwargs)

    return wrapper


def staff_required(view):
    """Staff and administrators (people who may record follow-ups)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user["role"] not in ("admin", "staff"):
            return error(403, "forbidden", "You don't have permission to do that.")
        return view(*args, **kwargs)

    return wrapper


# ---------- audit ----------
def audit(action, detail="", username=None):
    if username is None:
        username = g.user["username"] if "user" in g else None
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (username, action, detail) VALUES (?, ?, ?)",
        (username, action, detail),
    )
    db.commit()


# ---------- login throttling (per process) ----------
def _failures():
    return current_app.extensions.setdefault("login_failures", {})


def _throttle_key(username):
    return (request.remote_addr, username.lower())


def _seconds_locked(key):
    entry = _failures().get(key)
    if entry and entry[1] > time.time():
        return int(entry[1] - time.time()) + 1
    return 0


def _record_failure(key):
    count, _ = _failures().get(key, (0, 0))
    count += 1
    if count >= current_app.config["LOGIN_MAX_FAILS"]:
        _failures()[key] = (0, time.time() + current_app.config["LOGIN_LOCK_SECONDS"])
    else:
        _failures()[key] = (count, 0)


# ---------- routes ----------
@bp.post("/login")
def login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not username or not password:
        raise ValidationError("Enter your username and password")

    key = _throttle_key(username)
    wait = _seconds_locked(key)
    if wait:
        resp = jsonify(
            error="too_many_attempts",
            message=f"Too many failed attempts. Try again in {wait} seconds.",
            retry_after=wait,
        )
        resp.status_code = 429
        resp.headers["Retry-After"] = str(wait)
        return resp

    row = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    valid = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, password)
    if row is None or not row["active"] or not valid:
        _record_failure(key)
        audit("login.failed", f"username={username[:32]}", username=username[:32])
        return error(401, "invalid_credentials", "Incorrect username or password.")

    _failures().pop(key, None)
    audit("login", "", username=row["username"])
    return jsonify(
        token=make_token(row),
        expires_in=current_app.config["TOKEN_MAX_AGE"],
        user=public_user(row),
    )


@bp.get("/me")
def me():
    return jsonify(user=public_user(g.user))


@bp.post("/change-password")
def change_password():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    if not check_password_hash(g.user["password_hash"], str(body.get("current_password", ""))):
        return error(400, "validation_error", "Current password is incorrect.", field="current_password")
    problem = password_problem(body.get("new_password"), current_app.config["MIN_PASSWORD_LENGTH"])
    if problem:
        raise ValidationError(problem, "new_password")

    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?",
        (generate_password_hash(body["new_password"]), g.user["id"]),
    )
    db.commit()
    row = db.execute("SELECT * FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    audit("password.change", "")
    # Other sessions are signed out; this one gets a fresh token.
    return jsonify(token=make_token(row), user=public_user(row))


# ---------- first-run admin ----------
def _maybe_create_demo_viewer(app, conn, admin_username):
    name = app.config.get("DEMO_VIEWER_USERNAME")
    password = app.config.get("DEMO_VIEWER_PASSWORD")
    if not name or not password:
        return
    try:
        name = clean_username(name)
    except ValidationError as exc:
        print(f"WARNING: demo viewer not created: {exc.message}")
        return
    problem = password_problem(password, app.config["MIN_PASSWORD_LENGTH"])
    if problem:
        print(f"WARNING: demo viewer not created: {problem}")
        return
    if name.lower() == admin_username.lower():
        print("WARNING: demo viewer not created: it must differ from the admin username")
        return
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'viewer')",
        (name, generate_password_hash(password)),
    )



def ensure_first_admin(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return
        username = app.config["ADMIN_USERNAME"]
        password = app.config["ADMIN_PASSWORD"]
        generated = not password
        if generated:
            password = secrets.token_urlsafe(12)
        else:
            problem = password_problem(password, app.config["MIN_PASSWORD_LENGTH"])
            if problem:  # refuse to start with a weak, deliberately chosen admin password
                sys.exit(f"ADMIN_PASSWORD is not acceptable: {problem}")
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            (username, generate_password_hash(password)),
        )
        _maybe_create_demo_viewer(app, conn, admin_username=username)
        conn.commit()
    finally:
        conn.close()
    if generated:
        print("\n" + "=" * 60)
        print("  First run: created the admin account")
        print(f"    username: {username}")
        print(f"    password: {password}")
        print("  This password is shown once. Sign in and change it.")
        print("=" * 60 + "\n")
