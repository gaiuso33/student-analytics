"""Who may see which students.

Administrators, and staff or viewers whose access is "all students", see everything. A person whose access is
"only these classes" sees only students whose class matches one of theirs (ignoring letter case), plus those
students' results and follow-ups. Students with no class are invisible to them.

Every read query uses the per-request views created here (students_v, records_v, record_points_v, interventions_v)
instead of the real tables, so no endpoint can forget to apply the rule.
"""


def is_limited(user):
    return user["role"] != "admin" and user["scope"] == "classes"


def install(db, user):
    """Create the temporary per-request views. The connection (and so the views) lasts one request."""
    if is_limited(user):
        condition = (
            "class_name COLLATE NOCASE IN "
            f"(SELECT class_name FROM main.user_classes WHERE user_id = {int(user['id'])})"
        )
        students = f"SELECT * FROM main.students WHERE {condition}"
        others = "WHERE student_id IN (SELECT id FROM students_v)"
    else:
        students = "SELECT * FROM main.students"
        others = ""
    db.execute(f"CREATE TEMP VIEW students_v AS {students}")
    db.execute(f"CREATE TEMP VIEW records_v AS SELECT * FROM main.records {others}")
    db.execute(f"CREATE TEMP VIEW record_points_v AS SELECT * FROM main.record_points {others}")
    db.execute(f"CREATE TEMP VIEW interventions_v AS SELECT * FROM main.interventions {others}")


def can_see_student(db, username_row, student_id):
    """Could this (other) user see this student? Used before assigning a follow-up to them."""
    if not is_limited(username_row):
        return True
    return db.execute(
        "SELECT 1 FROM main.students s JOIN main.user_classes uc ON uc.user_id = ? "
        "AND uc.class_name = s.class_name COLLATE NOCASE WHERE s.id = ?",
        (username_row["id"], student_id),
    ).fetchone() is not None
