"""Bulk import of results from CSV (admin only).

Expected columns (case-insensitive, any order, extra columns ignored):
    Student (or Name), Course, Semester, Score
The file written by "Export CSV" in the dashboard can be re-imported as is.
"""
import csv
import io
from itertools import islice

from flask import Blueprint, current_app, jsonify, request

from auth import admin_required, audit
from db import get_db
from validation import ValidationError, clean_score, clean_text

bp = Blueprint("importer", __name__, url_prefix="/api")

REQUIRED = ("name", "course", "semester", "score")
ALIASES = {
    "name": "name", "student": "name", "student name": "name", "student_name": "name",
    "course": "course", "subject": "course",
    "semester": "semester", "term": "semester",
    "score": "score", "mark": "score", "marks": "score",
}
MAX_REPORTED_ERRORS = 50


def parse_rows(text, max_rows):
    """Return (rows, delimiter) where rows is a list of (row_number, {field: raw_text})."""
    text = text.lstrip("\ufeff")
    if not text.strip():
        raise ValidationError("The file is empty", "csv")
    first_line = text.splitlines()[0]
    delimiter = max((",", ";", "\t"), key=first_line.count)
    try:
        raw = list(islice(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter), max_rows + 2))
    except csv.Error as exc:
        raise ValidationError(f"Could not read the file as CSV: {exc}", "csv")

    header = {}
    for idx, cell in enumerate(raw[0]):
        field = ALIASES.get(cell.strip().lower())
        if field and field not in header:
            header[field] = idx
    missing = [f for f in REQUIRED if f not in header]
    if missing:
        raise ValidationError(
            "Missing column(s): " + ", ".join(missing) + ". Expected: Student, Course, Semester, Score", "csv"
        )

    rows = []
    for number, cells in enumerate(raw[1:], start=2):
        if not any(c.strip() for c in cells):
            continue  # blank line
        rows.append((number, {f: (cells[i] if i < len(cells) else "") for f, i in header.items()}))
    if len(rows) > max_rows:
        raise ValidationError(f"Too many rows: the limit is {max_rows} per file", "csv")
    return rows, delimiter


def parse_score(text, delimiter):
    cleaned = text.strip()
    if delimiter == ";":
        cleaned = cleaned.replace(",", ".")  # decimal comma in semicolon-separated files
    try:
        value = float(cleaned)
    except ValueError:
        raise ValidationError("Score must be a number between 0 and 100", "score")
    return clean_score(value)


def build_plan(db, rows, delimiter, on_duplicate):
    errors = []
    existing_students = {r["name"].lower(): r["id"] for r in db.execute("SELECT id, name FROM students")}
    courses = {r[0].lower(): r[0] for r in db.execute("SELECT DISTINCT course FROM records")}
    semesters = {r[0].lower(): r[0] for r in db.execute("SELECT DISTINCT semester FROM records")}
    existing_records = {
        (r["student_id"], r["course"], r["semester"]): (r["id"], r["score"])
        for r in db.execute("SELECT id, student_id, course, semester, score FROM records")
    }

    new_students = {}  # lowercase name -> display name (first spelling wins)
    seen = {}
    ops = []
    counts = {"created": 0, "updated": 0, "skipped": 0}

    for number, cells in rows:
        try:
            name = clean_text(cells["name"], "name", 100, "Student name")
            course = clean_text(cells["course"], "course", 60, "Course")
            semester = clean_text(cells["semester"], "semester", 20, "Semester")
            score = parse_score(cells["score"], delimiter)
        except ValidationError as exc:
            errors.append({"row": number, "message": exc.message})
            continue

        # Match existing spellings regardless of letter case so "math" doesn't become a second course.
        course = courses.setdefault(course.lower(), course)
        semester = semesters.setdefault(semester.lower(), semester)

        key = (name.lower(), course, semester)
        if key in seen:
            errors.append({"row": number, "message": f"Duplicate of row {seen[key]} (same student, course and semester)"})
            continue
        seen[key] = number

        student_id = existing_students.get(name.lower())
        if student_id is None:
            new_students.setdefault(name.lower(), name)
        current = existing_records.get((student_id, course, semester)) if student_id else None

        if current is None:
            ops.append(("create", name.lower(), student_id, course, semester, score, None))
            counts["created"] += 1
        elif on_duplicate == "update" and current[1] != score:
            ops.append(("update", name.lower(), student_id, course, semester, score, current[0]))
            counts["updated"] += 1
        else:
            counts["skipped"] += 1

    return {"errors": errors, "new_students": new_students, "ops": ops, "counts": counts}


def apply_plan(db, plan):
    try:
        ids = {}
        for lower, name in plan["new_students"].items():
            ids[lower] = db.execute("INSERT INTO students (name) VALUES (?)", (name,)).lastrowid
        for action, lower, student_id, course, semester, score, record_id in plan["ops"]:
            if action == "create":
                db.execute(
                    "INSERT INTO records (student_id, course, semester, score) VALUES (?, ?, ?, ?)",
                    (student_id or ids[lower], course, semester, score),
                )
            else:
                db.execute("UPDATE records SET score = ? WHERE id = ?", (score, record_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


@bp.post("/import")
@admin_required
def import_csv():
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("csv"), str):
        raise ValidationError("Expected a JSON object with a 'csv' text field")
    dry_run = bool(body.get("dry_run", False))
    on_duplicate = body.get("on_duplicate", "skip")
    if on_duplicate not in ("skip", "update"):
        raise ValidationError("on_duplicate must be 'skip' or 'update'", "on_duplicate")

    rows, delimiter = parse_rows(body["csv"], current_app.config["MAX_IMPORT_ROWS"])
    if not rows:
        raise ValidationError("The file has a header but no data rows", "csv")

    db = get_db()
    plan = build_plan(db, rows, delimiter, on_duplicate)
    summary = {
        "dry_run": dry_run,
        "total_rows": len(rows),
        "students_created": len(plan["new_students"]),
        "records_created": plan["counts"]["created"],
        "records_updated": plan["counts"]["updated"],
        "records_skipped": plan["counts"]["skipped"],
        "error_count": len(plan["errors"]),
        "errors": plan["errors"][:MAX_REPORTED_ERRORS],
    }

    if plan["errors"]:
        if dry_run:
            return jsonify(**summary, imported=False)
        # All-or-nothing: never leave a half-imported file behind.
        resp = jsonify(
            error="import_failed",
            message="Some rows have problems. Nothing was imported; fix the file and upload it again.",
            **summary, imported=False,
        )
        resp.status_code = 400
        return resp

    if dry_run:
        return jsonify(**summary, imported=False)

    apply_plan(db, plan)
    audit(
        "import",
        f"rows={summary['total_rows']} students_created={summary['students_created']} "
        f"created={summary['records_created']} updated={summary['records_updated']} "
        f"skipped={summary['records_skipped']} on_duplicate={on_duplicate}",
    )
    return jsonify(**summary, imported=True)
