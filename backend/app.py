import os
import re
import secrets

from flask import Flask, jsonify, request

import auth
import importer
import insights
import interventions
import users
import write
from config import Config
from db import close_db, get_db, init_db
from seed import is_empty, seed
from validation import ValidationError

LOCAL_ORIGIN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

# Cumulative GPA per student (average grade points over all records).
STUDENT_GPA = """
    SELECT s.id, s.name, ROUND(AVG(p.points), 2) AS gpa, COUNT(*) AS records,
           SUM(CASE WHEN p.score < :pass_mark THEN 1 ELSE 0 END) AS failing_courses
    FROM students s
    JOIN record_points p ON p.student_id = s.id
    GROUP BY s.id
"""


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        print("WARNING: SECRET_KEY is not set; using a temporary key. "
              "Everyone will be signed out when the server restarts.")

    init_db(app.config["DATABASE"])
    if app.config["SEED_IF_EMPTY"] and is_empty(app.config["DATABASE"]):
        seed(app.config["DATABASE"])
    auth.ensure_first_admin(app)

    app.teardown_appcontext(close_db)
    app.before_request(auth.authenticate)
    app.register_blueprint(auth.bp)
    app.register_blueprint(write.bp)
    app.register_blueprint(importer.bp)
    app.register_blueprint(insights.bp)
    app.register_blueprint(interventions.bp)
    app.register_blueprint(users.bp)

    # ---------- CORS (no extra dependency) ----------
    @app.after_request
    def add_cors(resp):
        origin = request.headers.get("Origin")
        allowed = origin in app.config["CORS_ORIGINS"] or (
            app.config["CORS_ALLOW_ANY_LOCALHOST"] and LOCAL_ORIGIN.match(origin or "")
        )
        if origin and allowed:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"  # student data must not be cached
        return resp

    # ---------- errors ----------
    @app.errorhandler(ValidationError)
    def invalid(e):
        return jsonify(error="validation_error", message=e.message, field=e.field), 400

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify(error="too_large", message="That file is too large (limit 2 MB)"), 413

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="not_found", message="Resource not found"), 404

    @app.errorhandler(405)
    def not_allowed(_e):
        return jsonify(error="method_not_allowed", message="Method not allowed"), 405

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify(error="server_error", message="Something went wrong on the server"), 500

    def params():
        return {"pass_mark": app.config["PASS_MARK"]}

    # ---------- endpoints ----------
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/students")
    def students():
        """One row per student per course per semester.
        `gpa` is the student's GPA for that semester;
        `at_risk` is whether the student's cumulative GPA is below AT_RISK_GPA."""
        search = request.args.get("search", "").strip().lower()
        course = request.args.get("course")
        semester = request.args.get("semester")

        sql = f"""
            WITH sg AS ({STUDENT_GPA})
            SELECT * FROM (
                SELECT p.id, p.student_id, s.name, p.course, p.score, p.semester,
                       ROUND(AVG(p.points) OVER (PARTITION BY p.student_id, p.semester), 2) AS gpa,
                       (sg.gpa < :threshold) AS at_risk
                FROM record_points p
                JOIN students s ON s.id = p.student_id
                JOIN sg ON sg.id = p.student_id
            ) WHERE 1=1
        """
        args = {**params(), "threshold": app.config["AT_RISK_GPA"]}
        if search:
            sql += " AND (LOWER(name) LIKE :q OR LOWER(course) LIKE :q)"
            args["q"] = f"%{search}%"
        if course:
            sql += " AND course = :course"
            args["course"] = course
        if semester:
            sql += " AND semester = :semester"
            args["semester"] = semester
        if request.args.get("at_risk", "").lower() in ("1", "true"):
            sql += " AND at_risk = 1"
        sql += " ORDER BY name, semester, course"

        rows = get_db().execute(sql, args).fetchall()
        return jsonify([{**dict(r), "at_risk": bool(r["at_risk"])} for r in rows])

    @app.get("/api/analytics")
    def analytics():
        db = get_db()
        gpa = db.execute(
            f"SELECT COUNT(*) AS total, AVG(gpa) AS avg_gpa, MAX(gpa) AS max_gpa FROM ({STUDENT_GPA})",
            params(),
        ).fetchone()
        pr = db.execute(
            "SELECT COUNT(*) AS n, SUM(CASE WHEN score >= :pass_mark THEN 1 ELSE 0 END) AS passed FROM records",
            params(),
        ).fetchone()
        n = pr["n"] or 0
        return jsonify(
            total_students=gpa["total"],
            average_gpa=round(gpa["avg_gpa"], 2) if gpa["avg_gpa"] is not None else None,
            highest_gpa=gpa["max_gpa"],
            pass_rate=round(100 * (pr["passed"] or 0) / n, 1) if n else None,
        )

    @app.get("/api/top-students")
    def top_students():
        try:
            limit = max(1, min(int(request.args.get("limit", 5)), 50))
        except ValueError:
            return jsonify(error="bad_request", message="limit must be an integer"), 400
        rows = get_db().execute(
            f"SELECT id, name, gpa FROM ({STUDENT_GPA}) ORDER BY gpa DESC, name LIMIT :limit",
            {**params(), "limit": limit},
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/course-difficulty")
    def course_difficulty():
        """Courses ordered hardest (lowest average score) first."""
        rows = get_db().execute(
            """
            SELECT course, ROUND(AVG(score), 1) AS average_score,
                   COUNT(DISTINCT student_id) AS students
            FROM records GROUP BY course ORDER BY average_score ASC
            """
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/at-risk-students")
    def at_risk():
        """Students whose cumulative GPA is below AT_RISK_GPA, lowest first,
        with how many follow-ups are still open for each."""
        rows = get_db().execute(
            f"""
            SELECT sg.id, sg.name, sg.gpa, sg.failing_courses,
                   (SELECT COUNT(*) FROM interventions i
                     WHERE i.student_id = sg.id AND i.status = 'open') AS open_interventions,
                   (SELECT MAX(i.created_at) FROM interventions i
                     WHERE i.student_id = sg.id) AS last_intervention
            FROM ({STUDENT_GPA}) AS sg
            WHERE sg.gpa < :threshold ORDER BY sg.gpa ASC, sg.name
            """,
            {**params(), "threshold": app.config["AT_RISK_GPA"]},
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/students/<int:student_id>")
    def student_detail(student_id):
        db = get_db()
        student = db.execute("SELECT id, name FROM students WHERE id = ?", (student_id,)).fetchone()
        if student is None:
            return jsonify(error="not_found", message="Student not found"), 404
        stats = db.execute(
            f"SELECT gpa, failing_courses FROM ({STUDENT_GPA}) WHERE id = :id",
            {**params(), "id": student_id},
        ).fetchone()  # None until the student has at least one result
        gpa = stats["gpa"] if stats else None
        records = db.execute(
            "SELECT id, course, semester, score FROM records "
            "WHERE student_id = ? ORDER BY semester, course",
            (student_id,),
        ).fetchall()
        semesters = db.execute(
            "SELECT semester, ROUND(AVG(points), 2) AS gpa FROM record_points "
            "WHERE student_id = ? GROUP BY semester ORDER BY semester",
            (student_id,),
        ).fetchall()
        return jsonify(
            id=student["id"],
            name=student["name"],
            gpa=gpa,
            failing_courses=stats["failing_courses"] if stats else 0,
            at_risk=gpa is not None and gpa < app.config["AT_RISK_GPA"],
            records=[dict(r) for r in records],
            semester_gpa=[dict(r) for r in semesters],
        )

    @app.get("/api/courses")
    def courses():
        """Per-course summary, hardest (lowest average score) first."""
        rows = get_db().execute(
            """
            SELECT course,
                   ROUND(AVG(score), 1) AS average_score,
                   ROUND(100.0 * SUM(CASE WHEN score >= :pass_mark THEN 1 ELSE 0 END) / COUNT(*), 1) AS pass_rate,
                   COUNT(DISTINCT student_id) AS students
            FROM records GROUP BY course ORDER BY average_score ASC
            """,
            params(),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/api/gpa-trend")
    def gpa_trend():
        rows = get_db().execute(
            """
            SELECT semester, ROUND(AVG(gpa), 2) AS average_gpa FROM (
                SELECT semester, student_id, AVG(points) AS gpa
                FROM record_points GROUP BY semester, student_id
            ) GROUP BY semester ORDER BY semester
            """
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    return app


if __name__ == "__main__":
    # Local development server: debug mode, and any localhost port may call the API.
    # PORT and FLASK_DEBUG=0 are used by the browser tests (frontend/e2e) to run a throwaway copy.
    create_app({"CORS_ALLOW_ANY_LOCALHOST": True}).run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "1") != "0",
    )
