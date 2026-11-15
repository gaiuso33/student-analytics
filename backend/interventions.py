"""Follow-up tracking for students (meetings, tutoring, parent contact, ...), with owners and reminders.

Permissions: everyone signed in can read; staff and administrators can record and update;
only administrators can delete. Audit entries record who did what, never the note text.

Dates are UTC (the server's idea of "today"). "Due soon" means due within REMINDER_DAYS_AHEAD days.
"""
from flask import Blueprint, current_app, g, jsonify, request

import scope
from auth import admin_required, audit, staff_required
from db import get_db
from validation import (
    INTERVENTION_KINDS, INTERVENTION_STATUSES, ValidationError,
    clean_choice, clean_date, clean_note,
)

bp = Blueprint("interventions", __name__, url_prefix="/api")

FROM = "FROM interventions_v i JOIN students_v s ON s.id = i.student_id"


def days_ahead():
    return max(0, int(current_app.config["REMINDER_DAYS_AHEAD"]))


def columns():
    d = days_ahead()
    return f"""
        i.id, i.student_id, s.name AS student_name, i.kind, i.note, i.status, i.due_date,
        i.assigned_to, i.created_by, i.created_at, i.updated_at, i.completed_at,
        (i.status = 'open' AND i.due_date IS NOT NULL AND i.due_date < date('now')) AS overdue,
        (i.status = 'open' AND i.due_date IS NOT NULL AND i.due_date >= date('now')
            AND i.due_date <= date('now', '+{d} days')) AS due_soon,
        CASE WHEN i.due_date IS NULL THEN NULL
             ELSE CAST(julianday(i.due_date) - julianday(date('now')) AS INTEGER) END AS due_in_days
    """


def attention_sql(alias="i"):
    """Open, dated, and overdue or due within the reminder window."""
    return (f"{alias}.status = 'open' AND {alias}.due_date IS NOT NULL "
            f"AND {alias}.due_date <= date('now', '+{days_ahead()} days')")


def as_dict(row):
    item = dict(row)
    item["overdue"] = bool(item["overdue"])
    item["due_soon"] = bool(item["due_soon"])
    return item


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    return body


def error(status, code, message):
    return jsonify(error=code, message=message), status


def clean_assignee(db, value, student_id):
    """None/'' = unassigned. Otherwise an active staff member or administrator who can see this student."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError("Assigned to must be a username", "assigned_to")
    row = db.execute(
        "SELECT id, username, role, scope FROM users WHERE username = ? AND active = 1 AND role IN ('admin', 'staff')",
        (value.strip(),),
    ).fetchone()
    if row is None:
        raise ValidationError("Choose an active staff member or administrator", "assigned_to")
    if not scope.can_see_student(db, row, student_id):
        raise ValidationError(f"{row['username']} is not assigned to this student's class", "assigned_to")
    return row["username"]


@bp.get("/students/<int:student_id>/interventions")
def list_for_student(student_id):
    db = get_db()
    if db.execute("SELECT 1 FROM students_v WHERE id = ?", (student_id,)).fetchone() is None:
        return error(404, "not_found", "Student not found")
    rows = db.execute(
        f"SELECT {columns()} {FROM} WHERE i.student_id = ? "
        "ORDER BY (i.status = 'open') DESC, i.created_at DESC, i.id DESC",
        (student_id,),
    ).fetchall()
    return jsonify([as_dict(r) for r in rows])


@bp.get("/interventions")
def worklist():
    """Follow-ups across all students.

    ?status=open|done|all (default open)   ?overdue=1   ?attention=1 (overdue or due soon)
    ?assigned=me|unassigned|<username>      ?limit=
    """
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
    if request.args.get("attention", "").lower() in ("1", "true"):
        where.append(attention_sql())
    assigned = request.args.get("assigned", "")
    if assigned == "me":
        where.append("i.assigned_to = ? COLLATE NOCASE")
        args.append(g.user["username"])
    elif assigned == "unassigned":
        where.append("i.assigned_to IS NULL")
    elif assigned:
        where.append("i.assigned_to = ? COLLATE NOCASE")
        args.append(assigned)

    order = (
        "(i.due_date IS NULL), i.due_date ASC, i.id ASC" if status == "open"
        else "i.completed_at DESC, i.id DESC" if status == "done"
        else "(i.status = 'open') DESC, i.created_at DESC, i.id DESC"
    )
    sql = (f"SELECT {columns()} {FROM}" + (" WHERE " + " AND ".join(where) if where else "")
           + f" ORDER BY {order} LIMIT ?")
    rows = get_db().execute(sql, (*args, limit)).fetchall()
    return jsonify([as_dict(r) for r in rows])


@bp.get("/reminders")
def reminders():
    """What needs attention: for the signed-in user (assigned to them) and for the whole team."""
    db = get_db()
    me = g.user["username"]
    d = days_ahead()
    counts = db.execute(
        f"""
        SELECT
          COALESCE(SUM(CASE WHEN assigned_to = :me COLLATE NOCASE AND due_date < date('now') THEN 1 ELSE 0 END), 0) AS my_overdue,
          COALESCE(SUM(CASE WHEN assigned_to = :me COLLATE NOCASE AND due_date >= date('now')
                             AND due_date <= date('now', '+{d} days') THEN 1 ELSE 0 END), 0) AS my_due_soon,
          COALESCE(SUM(CASE WHEN assigned_to = :me COLLATE NOCASE THEN 1 ELSE 0 END), 0) AS my_open,
          COALESCE(SUM(CASE WHEN due_date < date('now') THEN 1 ELSE 0 END), 0) AS team_overdue,
          COUNT(*) AS team_open
        FROM interventions_v WHERE status = 'open'
        """,
        {"me": me},
    ).fetchone()
    items = db.execute(
        f"SELECT {columns()} {FROM} WHERE {attention_sql()} AND i.assigned_to = ? COLLATE NOCASE "
        "ORDER BY i.due_date ASC, i.id ASC LIMIT 5",
        (me,),
    ).fetchall()
    unattended = db.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT s.id FROM students_v s JOIN record_points_v p ON p.student_id = s.id
          GROUP BY s.id
          HAVING ROUND(AVG(p.points), 2) < ?
             AND NOT EXISTS (SELECT 1 FROM interventions_v i WHERE i.student_id = s.id AND i.status = 'open')
        )
        """,
        (current_app.config["AT_RISK_GPA"],),
    ).fetchone()[0]
    return jsonify(
        days_ahead=d,
        mine={
            "overdue": counts["my_overdue"], "due_soon": counts["my_due_soon"], "open": counts["my_open"],
            "items": [as_dict(r) for r in items],
        },
        team={"overdue": counts["team_overdue"], "open": counts["team_open"], "unattended_at_risk": unattended},
    )


@bp.get("/assignees")
@staff_required
def assignees():
    """People a follow-up can be assigned to. With ?student=<id>, only those who can see that student."""
    db = get_db()
    people = db.execute(
        "SELECT id, username, role, scope FROM users WHERE active = 1 AND role IN ('admin', 'staff') "
        "ORDER BY username COLLATE NOCASE"
    ).fetchall()
    student = request.args.get("student", type=int)
    if student is not None:
        if db.execute("SELECT 1 FROM students_v WHERE id = ?", (student,)).fetchone() is None:
            return error(404, "not_found", "Student not found")
        people = [p for p in people if scope.can_see_student(db, p, student)]
    return jsonify([{"username": p["username"], "role": p["role"]} for p in people])


def fetch(db, intervention_id):
    return db.execute(f"SELECT {columns()} {FROM} WHERE i.id = ?", (intervention_id,)).fetchone()


@bp.post("/students/<int:student_id>/interventions")
@staff_required
def create(student_id):
    body = json_body()
    kind = clean_choice(body.get("kind"), INTERVENTION_KINDS, "kind", "Type")
    note = clean_note(body.get("note"))
    due = clean_date(body.get("due_date"))
    db = get_db()
    if db.execute("SELECT 1 FROM students_v WHERE id = ?", (student_id,)).fetchone() is None:
        return error(404, "not_found", "Student not found")
    # Left out = assigned to the person recording it. An explicit null/"" = nobody.
    assigned = clean_assignee(db, body["assigned_to"], student_id) if "assigned_to" in body else g.user["username"]
    cur = db.execute(
        "INSERT INTO interventions (student_id, kind, note, due_date, assigned_to, created_by) VALUES (?, ?, ?, ?, ?, ?)",
        (student_id, kind, note, due, assigned, g.user["username"]),
    )
    db.commit()
    audit("intervention.create", f"id={cur.lastrowid} student={student_id} kind={kind} assigned={assigned or '-'}")
    return jsonify(as_dict(fetch(db, cur.lastrowid))), 201


@bp.patch("/interventions/<int:intervention_id>")
@staff_required
def update(intervention_id):
    body = json_body()
    db = get_db()
    row = db.execute("SELECT * FROM interventions_v WHERE id = ?", (intervention_id,)).fetchone()
    if row is None:
        return error(404, "not_found", "Follow-up not found")

    kind = clean_choice(body["kind"], INTERVENTION_KINDS, "kind", "Type") if "kind" in body else row["kind"]
    note = clean_note(body["note"]) if "note" in body else row["note"]
    due = clean_date(body["due_date"]) if "due_date" in body else row["due_date"]
    assigned = clean_assignee(db, body["assigned_to"], row["student_id"]) if "assigned_to" in body else row["assigned_to"]
    status = (clean_choice(body["status"], INTERVENTION_STATUSES, "status", "Status")
              if "status" in body else row["status"])

    completed_at = row["completed_at"]
    if status == "done" and row["status"] != "done":
        completed_at = db.execute("SELECT datetime('now')").fetchone()[0]
    elif status == "open":
        completed_at = None

    db.execute(
        "UPDATE interventions SET kind = ?, note = ?, due_date = ?, assigned_to = ?, status = ?, "
        "completed_at = ?, updated_at = datetime('now') WHERE id = ?",
        (kind, note, due, assigned, status, completed_at, intervention_id),
    )
    db.commit()
    changed = ",".join(k for k in ("kind", "note", "due_date", "assigned_to", "status") if k in body)
    audit("intervention.update", f"id={intervention_id} student={row['student_id']} changed={changed}")
    return jsonify(as_dict(fetch(db, intervention_id)))


@bp.delete("/interventions/<int:intervention_id>")
@admin_required
def delete(intervention_id):
    db = get_db()
    row = db.execute("SELECT student_id FROM interventions_v WHERE id = ?", (intervention_id,)).fetchone()
    if row is None:
        return error(404, "not_found", "Follow-up not found")
    db.execute("DELETE FROM interventions WHERE id = ?", (intervention_id,))
    db.commit()
    audit("intervention.delete", f"id={intervention_id} student={row['student_id']}")
    return "", 204
