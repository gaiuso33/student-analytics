"""Plain-language findings for the Overview page, computed from the latest two semesters."""
from urllib.parse import quote

from flask import Blueprint, current_app, jsonify

from db import get_db

bp = Blueprint("insights", __name__, url_prefix="/api")

MAX_STUDENTS = 5


def _change_text(label, previous, latest, prev_name, last_name, unit="", dp=2):
    delta = round(latest - previous, dp)
    if abs(delta) < 10 ** -dp:
        return "neutral", f"{label} is unchanged at {latest:.{dp}f}{unit} ({prev_name} to {last_name})."
    verb, tone = ("rose", "positive") if delta > 0 else ("fell", "warning")
    return tone, (f"{label} {verb} by {abs(delta):.{dp}f}{unit}, from {previous:.{dp}f}{unit} "
                  f"in {prev_name} to {latest:.{dp}f}{unit} in {last_name}.")


def _student_list(items):
    return [{"id": i["id"], "name": i["name"], "detail": i["detail"]} for i in items[:MAX_STUDENTS]]


@bp.get("/insights")
def get_insights():
    db = get_db()
    pass_mark = current_app.config["PASS_MARK"]
    threshold = current_app.config["INSIGHT_GPA_CHANGE"]
    out = []

    semesters = [r[0] for r in db.execute("SELECT DISTINCT semester FROM records ORDER BY semester")]
    latest = semesters[-1] if semesters else None
    previous = semesters[-2] if len(semesters) >= 2 else None

    if previous:
        # Average of student GPAs and pass rate, per semester
        gpa_rows = db.execute(
            """
            SELECT p.student_id, s.name, p.semester, AVG(p.points) AS gpa
            FROM record_points p JOIN students s ON s.id = p.student_id
            WHERE p.semester IN (?, ?) GROUP BY p.student_id, p.semester
            """,
            (previous, latest),
        ).fetchall()
        by_sem = {previous: {}, latest: {}}
        names = {}
        for r in gpa_rows:
            by_sem[r["semester"]][r["student_id"]] = r["gpa"]
            names[r["student_id"]] = r["name"]

        avg = {sem: sum(v.values()) / len(v) for sem, v in by_sem.items() if v}
        if len(avg) == 2:
            tone, text = _change_text("Average GPA", avg[previous], avg[latest], previous, latest)
            out.append({"id": "gpa-trend", "tone": tone, "text": text})

        rates = {
            r["semester"]: r["rate"]
            for r in db.execute(
                "SELECT semester, 100.0 * SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) / COUNT(*) AS rate "
                "FROM records WHERE semester IN (?, ?) GROUP BY semester",
                (pass_mark, previous, latest),
            )
        }
        if len(rates) == 2:
            tone, text = _change_text("The pass rate", rates[previous], rates[latest], previous, latest, unit="%", dp=1)
            out.append({"id": "pass-rate", "tone": tone, "text": text})

        # Per-student movement, only for students with results in both semesters
        moves = []
        for sid, now in by_sem[latest].items():
            before = by_sem[previous].get(sid)
            if before is not None:
                moves.append({"id": sid, "name": names[sid], "delta": now - before,
                              "detail": f"GPA {before:.2f} to {now:.2f}"})
        declining = sorted((m for m in moves if m["delta"] <= -threshold), key=lambda m: (m["delta"], m["name"]))
        improving = sorted((m for m in moves if m["delta"] >= threshold), key=lambda m: (-m["delta"], m["name"]))
        if declining:
            n = len(declining)
            out.append({
                "id": "declining-students", "tone": "warning",
                "text": f"{n} {'student' if n == 1 else 'students'} dropped by {threshold:g} GPA point"
                        f"{'' if threshold == 1 else 's'} or more since {previous}.",
                "students": _student_list(declining),
            })
        if improving:
            n = len(improving)
            out.append({
                "id": "improving-students", "tone": "positive",
                "text": f"{n} {'student' if n == 1 else 'students'} improved by {threshold:g} GPA point"
                        f"{'' if threshold == 1 else 's'} or more since {previous}.",
                "students": _student_list(improving),
            })

    # Course with the lowest pass rate overall (needs at least two courses to be a comparison)
    courses = db.execute(
        "SELECT course, 100.0 * SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) / COUNT(*) AS rate "
        "FROM records GROUP BY course ORDER BY rate ASC, course ASC",
        (pass_mark,),
    ).fetchall()
    if len(courses) >= 2:
        overall = db.execute(
            "SELECT 100.0 * SUM(CASE WHEN score >= ? THEN 1 ELSE 0 END) / COUNT(*) FROM records", (pass_mark,)
        ).fetchone()[0]
        worst = courses[0]
        if worst["rate"] < 100 and worst["rate"] < courses[-1]["rate"]:
            out.append({
                "id": "hardest-course",
                "tone": "warning" if worst["rate"] <= overall - 10 else "neutral",
                "text": f"{worst['course']} has the lowest pass rate: {worst['rate']:.1f}% "
                        f"(overall {overall:.1f}%).",
                "link": f"/students?course={quote(worst['course'])}&max={int(pass_mark) - 1}",
            })

    return jsonify(semester=latest, previous_semester=previous, insights=out)
