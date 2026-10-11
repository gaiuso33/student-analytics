"""Follow-up tracking for students (meetings, tutoring, parent contact, ...).

Permissions: everyone signed in can read; staff and administrators can record and update;
only administrators can delete. Audit entries record who did what, never the note text.
"""
from flask import Blueprint, g, jsonify, request

from auth import admin_required, audit, staff_required
from db import get_db
from validation import (
    INTERVENTION_KINDS, INTERVENTION_STATUSES, ValidationError,
    clean_choice, clean_date, clean_note,
)

bp = Blueprint("interventions", __name__, url_prefix="/api")

COLUMNS = """
    i.id, i.student_id, s.name AS student_name, i.kind, i.note, i.status, i.due_date,
    i.created_by, i.created_at, i.updated_at, i.completed_at,
    (i.status = 'open' AND i.due_date IS NOT NULL AND i.due_date < date('now')) AS overdue
"""
FROM = "FROM interventions i JOIN students s ON s.id = i.student_id"


def as_dict(row):
    item = dict(row)
    item["overdue"] = bool(item["overdue"])
    return item


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    return body


def error(status, code, message):
    return jsonify(error=code, message=message), status


@bp.get("/students/<int:student_id>/interventions")
def list_for_student(student_id):
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        return error(404, "not_found", "Student not found")
    rows = db.execute(
        f"SELECT {COLUMNS} {FROM} WHERE i.student_id = ? "
        "ORDER BY (i.status = 'open') DESC, i.created_at DESC, i.id DESC",
        (student_id,),
    ).fetchall()
    return jsonify([as_dict(r) for r in rows])


@bp.get("/interventions")
def worklist():
    """Follow-ups across all students. ?status=open|done|all (default open), ?overdue=1, ?limit=."""
    status = request.args.get("status", "open")
    if status not in ("open", "done", "all"):
        raise ValidationError("status must be open, done or all", "status")
    try:
        limit = max(1, min(int(request.args.get("limit", 200)), 500))
    except ValueError:
        raise ValidationError("limit must be an integer", "limit")

    where, args = [], []
    if status != "all":
        where.append("i.status = ?")
        args.append(status)
    if request.args.get("overdue", "").lower() in ("1", "true"):
        where.append("i.status = 'open' AND i.due_date IS NOT NULL AND i.due_date < date('now')")
    order = (
        "(i.due_date IS NULL), i.due_date ASC, i.id ASC" if status == "open"
        else "i.completed_at DESC, i.id DESC" if status == "done"
        else "(i.status = 'open') DESC, i.created_at DESC, i.id DESC"
    )
    sql = f"SELECT {COLUMNS} {FROM}" + (" WHERE " + " AND ".join(where) if where else "") + f" ORDER BY {order} LIMIT ?"
    rows = get_db().execute(sql, (*args, limit)).fetchall()
    return jsonify([as_dict(r) for r in rows])


def fetch(db, intervention_id):
    return db.execute(f"SELECT {COLUMNS} {FROM} WHERE i.id = ?", (intervention_id,)).fetchone()


@bp.post("/students/<int:student_id>/interventions")
@staff_required
def create(student_id):
    body = json_body()
    kind = clean_choice(body.get("kind"), INTERVENTION_KINDS, "kind", "Type")
    note = clean_note(body.get("note"))
    due = clean_date(body.get("due_date"))
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        return error(404, "not_found", "Student not found")
    cur = db.execute(
        "INSERT INTO interventions (student_id, kind, note, due_date, created_by) VALUES (?, ?, ?, ?, ?)",
        (student_id, kind, note, due, g.user["username"]),
    )
    db.commit()
    audit("intervention.create", f"id={cur.lastrowid} student={student_id} kind={kind}")
    return jsonify(as_dict(fetch(db, cur.lastrowid))), 201


@bp.patch("/interventions/<int:intervention_id>")
@staff_required
def update(intervention_id):
    body = json_body()
    db = get_db()
    row = db.execute("SELECT * FROM interventions WHERE id = ?", (intervention_id,)).fetchone()
    if row is None:
        return error(404, "not_found", "Follow-up not found")

    kind = clean_choice(body["kind"], INTERVENTION_KINDS, "kind", "Type") if "kind" in body else row["kind"]
    note = clean_note(body["note"]) if "note" in body else row["note"]
    due = clean_date(body["due_date"]) if "due_date" in body else row["due_date"]
    status = (clean_choice(body["status"], INTERVENTION_STATUSES, "status", "Status")
              if "status" in body else row["status"])

    completed_at = row["completed_at"]
    if status == "done" and row["status"] != "done":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]
    elif status == "open":
        completed_at = None

    db.execute(
        "UPDATE interventions SET kind = ?, note = ?, due_date = ?, status = ?, completed_at = ?, "
        "updated_at = datetime('now') WHERE id = ?",
        (kind, note, due, status, completed_at, intervention_id),
    )
    db.commit()
    changed = ",".join(k for k in ("kind", "note", "due_date", "status") if k in body)
    audit("intervention.update", f"id={intervention_id} student={row['student_id']} changed={changed}")
    return jsonify(as_dict(fetch(db, intervention_id)))


@bp.delete("/interventions/<int:intervention_id>")
@admin_required
def delete(intervention_id):
    db = get_db()
    row = db.execute("SELECT student_id FROM interventions WHERE id = ?", (intervention_id,)).fetchone()
    if row is None:
        return error(404, "not_found", "Follow-up not found")
    db.execute("DELETE FROM interventions WHERE id = ?", (intervention_id,))
    db.commit()
    audit("intervention.delete", f"id={intervention_id} student={row['student_id']}")
    return "", 204
