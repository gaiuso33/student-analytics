import sqlite3

from flask import Blueprint, jsonify, request

from auth import admin_required, audit
from db import get_db
from validation import ValidationError, clean_class_name, clean_score, clean_student_code, clean_text

bp = Blueprint("write", __name__, url_prefix="/api")


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("Expected a JSON object body")
    return body


def conflict(message):
    return jsonify(error="conflict", message=message), 409


def not_found(what):
    return jsonify(error="not_found", message=f"{what} not found"), 404


def record_dict(row):
    return {k: row[k] for k in ("id", "student_id", "course", "semester", "score")}


SAME_NAME = "A student with that name already exists. Give each of them a student ID to tell them apart."


def name_clash(db, name, code, exclude_id=-1):
    """Two students may share a name only if both have (different) student IDs."""
    return db.execute(
        "SELECT 1 FROM students WHERE name = ? COLLATE NOCASE AND id <> ? AND (student_code IS NULL OR ? IS NULL) LIMIT 1",
        (name, exclude_id, code),
    ).fetchone() is not None


@bp.post("/students")
@admin_required
def create_student():
    body = json_body()
    name = clean_text(body.get("name"), "name", 100, "Name")
    code = clean_student_code(body.get("student_code"))
    class_name = clean_class_name(body.get("class_name"))
    db = get_db()
    if name_clash(db, name, code):
        return conflict(SAME_NAME)
    try:
        cur = db.execute("INSERT INTO students (name, student_code, class_name) VALUES (?, ?, ?)", (name, code, class_name))
    except sqlite3.IntegrityError:
        return conflict("That student ID is already in use")
    db.commit()
    audit("student.create", f"id={cur.lastrowid} name={name} code={code or '-'} class={class_name or '-'}")
    return jsonify(id=cur.lastrowid, name=name, student_code=code, class_name=class_name), 201


@bp.put("/students/<int:student_id>")
@admin_required
def rename_student(student_id):
    """Change a student's name, student ID and/or class. Leave a field out to keep it; null or "" removes the ID or class."""
    body = json_body()
    name = clean_text(body.get("name"), "name", 100, "Name")
    db = get_db()
    row = db.execute("SELECT student_code, class_name FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        return not_found("Student")
    code = clean_student_code(body["student_code"]) if "student_code" in body else row["student_code"]
    class_name = clean_class_name(body["class_name"]) if "class_name" in body else row["class_name"]
    if name_clash(db, name, code, student_id):
        return conflict(SAME_NAME)
    try:
        db.execute("UPDATE students SET name = ?, student_code = ?, class_name = ? WHERE id = ?", (name, code, class_name, student_id))
    except sqlite3.IntegrityError:
        return conflict("That student ID is already in use")
    db.commit()
    audit("student.rename", f"id={student_id} name={name} code={code or '-'} class={class_name or '-'}")
    return jsonify(id=student_id, name=name, student_code=code, class_name=class_name)


@bp.delete("/students/<int:student_id>")
@admin_required
def delete_student(student_id):
    db = get_db()
    row = db.execute("SELECT name FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        return not_found("Student")
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))  # records cascade
    db.commit()
    audit("student.delete", f"id={student_id} name={row['name']}")
    return "", 204


@bp.post("/students/<int:student_id>/records")
@admin_required
def create_record(student_id):
    body = json_body()
    course = clean_text(body.get("course"), "course", 60, "Course")
    semester = clean_text(body.get("semester"), "semester", 20, "Semester")
    score = clean_score(body.get("score"))
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        return not_found("Student")
    try:
        cur = db.execute(
            "INSERT INTO records (student_id, course, semester, score) VALUES (?, ?, ?, ?)",
            (student_id, course, semester, score),
        )
    except sqlite3.IntegrityError:
        return conflict("This student already has a result for that course and semester")
    db.commit()
    audit("record.create", f"id={cur.lastrowid} student={student_id} {course} {semester} {score}")
    return jsonify(id=cur.lastrowid, student_id=student_id, course=course, semester=semester, score=score), 201


@bp.put("/records/<int:record_id>")
@admin_required
def update_record(record_id):
    body = json_body()
    db = get_db()
    row = db.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        return not_found("Result")
    course = clean_text(body["course"], "course", 60, "Course") if "course" in body else row["course"]
    semester = clean_text(body["semester"], "semester", 20, "Semester") if "semester" in body else row["semester"]
    score = clean_score(body["score"]) if "score" in body else row["score"]
    try:
        db.execute(
            "UPDATE records SET course = ?, semester = ?, score = ? WHERE id = ?",
            (course, semester, score, record_id),
        )
    except sqlite3.IntegrityError:
        return conflict("This student already has a result for that course and semester")
    db.commit()
    audit("record.update", f"id={record_id} {course} {semester} {score}")
    return jsonify(id=record_id, student_id=row["student_id"], course=course, semester=semester, score=score)


@bp.delete("/records/<int:record_id>")
@admin_required
def delete_record(record_id):
    db = get_db()
    row = db.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        return not_found("Result")
    db.execute("DELETE FROM records WHERE id = ?", (record_id,))
    db.commit()
    audit("record.delete", f"id={record_id} student={row['student_id']} {row['course']} {row['semester']}")
    return "", 204
