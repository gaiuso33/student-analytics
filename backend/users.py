import sqlite3

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import generate_password_hash

from auth import admin_required, audit, error
from db import get_db
from validation import (
    ValidationError, clean_class_list, clean_email, clean_role, clean_scope, clean_username, password_problem,
)

bp = Blueprint("users", __name__, url_prefix="/api")


def classes_by_user(db):
    out = {}
    for r in db.execute("SELECT user_id, class_name FROM user_classes ORDER BY class_name COLLATE NOCASE"):
        out.setdefault(r["user_id"], []).append(r["class_name"])
    return out


def set_classes(db, user_id, classes):
    db.execute("DELETE FROM user_classes WHERE user_id = ?", (user_id,))
    db.executemany("INSERT OR IGNORE INTO user_classes (user_id, class_name) VALUES (?, ?)", [(user_id, c) for c in classes])


def user_dict(row, classes=()):
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "active": bool(row["active"]),
        "email": row["email"],
        # "all" = every student; "classes" = only students in `classes`. Administrators always see everyone.
        "scope": row["scope"] if row["role"] != "admin" else "all",
        "classes": sorted(classes, key=str.lower) if row["role"] != "admin" else [],
        "created_at": row["created_at"],
    }


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    return body


@bp.get("/users")
@admin_required
def list_users():
    db = get_db()
    classes = classes_by_user(db)
    rows = db.execute("SELECT * FROM users ORDER BY username COLLATE NOCASE").fetchall()
    return jsonify([user_dict(r, classes.get(r["id"], ())) for r in rows])


@bp.post("/users")
@admin_required
def create_user():
    body = json_body()
    username = clean_username(body.get("username"))
    role = clean_role(body.get("role", "viewer"))
    problem = password_problem(body.get("password"), current_app.config["MIN_PASSWORD_LENGTH"])
    if problem:
        raise ValidationError(problem, "password")
    email = clean_email(body.get("email"))
    scope = clean_scope(body.get("scope", "all"))
    classes = clean_class_list(body.get("classes", []))
    if role == "admin":  # administrators always see every student
        scope, classes = "all", []
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, password_hash, role, email, scope) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(body["password"]), role, email, scope),
        )
    except sqlite3.IntegrityError:
        return error(409, "conflict", "That username is already taken")
    set_classes(db, cur.lastrowid, classes)
    db.commit()
    audit("user.create", f"id={cur.lastrowid} username={username} role={role} scope={scope} classes={len(classes)}")
    row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(user_dict(row, classes)), 201


@bp.patch("/users/<int:user_id>")
@admin_required
def update_user(user_id):
    body = json_body()
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return error(404, "not_found", "User not found")

    if user_id == g.user["id"]:
        # An admin can't lock themselves out; this also guarantees one admin always remains.
        if any(k in body for k in ("role", "active", "password")):
            return error(400, "validation_error",
                         "You can't change your own role, status or password here. "
                         "Use the account page for your password.")

    role = clean_role(body["role"]) if "role" in body else row["role"]
    if "active" in body and not isinstance(body["active"], bool):
        raise ValidationError("active must be true or false", "active")
    active = int(body["active"]) if "active" in body else row["active"]
    password_hash = row["password_hash"]
    if "password" in body:
        problem = password_problem(body["password"], current_app.config["MIN_PASSWORD_LENGTH"])
        if problem:
            raise ValidationError(problem, "password")
        password_hash = generate_password_hash(body["password"])

    email = clean_email(body["email"]) if "email" in body else row["email"]
    scope = clean_scope(body["scope"]) if "scope" in body else row["scope"]
    new_classes = clean_class_list(body["classes"]) if "classes" in body else None
    if role == "admin":  # administrators always see every student, so limits make no sense for them
        scope, new_classes = "all", []
    # Only role, status and password changes sign the person out; email and class changes don't (they apply at once).
    bump = 1 if any(k in body for k in ("role", "active", "password")) else 0
    db.execute(
        "UPDATE users SET role = ?, active = ?, password_hash = ?, email = ?, scope = ?, "
        "token_version = token_version + ? WHERE id = ?",
        (role, active, password_hash, email, scope, bump, user_id),
    )
    if new_classes is not None:
        set_classes(db, user_id, new_classes)
    db.commit()
    changed = [k for k in ("role", "active", "password", "email", "scope", "classes") if k in body]
    audit("user.update", f"id={user_id} username={row['username']} changed={','.join(changed)}")
    updated = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify(user_dict(updated, classes_by_user(db).get(user_id, ())))


@bp.get("/audit")
@admin_required
def audit_log():
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
    except ValueError:
        raise ValidationError("limit must be an integer", "limit")
    rows = get_db().execute(
        "SELECT id, ts, username, action, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])
