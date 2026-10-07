# Student Analytics API

Flask + SQLite backend for the Student Analytics Dashboard.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

On first start an empty database is filled with demo data (40 students, 6 courses, 4 semesters).
Rebuild it any time with `python seed.py --reset`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Business rules (see config.py)

| Rule | Default | Env var |
|------|---------|---------|
| Record passes when score >= | 60 | `PASS_MARK` |
| Student is at risk when cumulative GPA < | 2.0 | `AT_RISK_GPA` |
| Grade points | A(90+)=4, B(80+)=3, C(70+)=2, D(60+)=1, F=0 | fixed |

Cumulative GPA = average grade points across all of a student's records.

## Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/students` (`?search=&course=&semester=&at_risk=true`) | `[{id, student_id, name, course, score, semester, gpa, at_risk}]` one row per student/course/semester; `gpa` = that semester's GPA, `at_risk` = student's cumulative GPA is below the threshold |
| `GET /api/students/<id>` | `{id, name, gpa, failing_courses, at_risk, records[], semester_gpa[]}` (404 if unknown) |
| `GET /api/courses` | `[{course, average_score, pass_rate, students}]` hardest first |
| `GET /api/analytics` | `{total_students, average_gpa, highest_gpa, pass_rate}` |
| `GET /api/top-students` (`?limit=5`) | `[{id, name, gpa}]` highest cumulative GPA first |
| `GET /api/course-difficulty` | `[{course, average_score, students}]` hardest first |
| `GET /api/at-risk-students` | `[{id, name, gpa, failing_courses}]` lowest GPA first |
| `GET /api/gpa-trend` | `[{semester, average_gpa}]` chronological |
| `GET /api/health` | `{status: "ok"}` |

Errors are JSON: `{error, message}` with the matching HTTP status.

CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` by default; set `CORS_ORIGINS` (comma-separated) for other origins.
