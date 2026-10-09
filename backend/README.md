# Student Analytics API

Flask + SQLite backend for the Student Analytics Dashboard. Every endpoint except
`/api/health` and `/api/auth/login` requires a signed-in user.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"   # recommended
python app.py            # http://127.0.0.1:5000
```

On first start an empty database is filled with demo data (40 students, 6 courses, 4 semesters)
and an **admin account is created**. Set `ADMIN_USERNAME` / `ADMIN_PASSWORD` beforehand, or the
server prints a random password **once** in the terminal. Sign in and change it from the account page.

Rebuild demo data with `python seed.py --reset` (accounts are kept unless you delete the database file).

## Accounts and roles

| Role | Can do |
|------|--------|
| `viewer` | Read all dashboards and student data |
| `admin` | Everything a viewer can, plus add/edit/delete students and results, manage users, read the audit log |

- Passwords: at least 10 characters, stored hashed (scrypt via Werkzeug).
- Sign-in returns a signed bearer token valid for `TOKEN_MAX_AGE` seconds (8 hours default). Changing a
  user's password, role or status immediately signs out their existing sessions.
- 5 failed sign-ins for a username from one address lock it for 60 seconds (counted in memory, per process).
- Admins can't change their own role/status, so at least one admin always remains. Users are deactivated, not deleted.
- Command line: `python manage.py create-user alice --role admin` and `python manage.py set-password alice`.
- Every sign-in, failed sign-in and data change is written to an audit log (`GET /api/audit`).

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

Send `Authorization: Bearer <token>` on everything except health and login.

### Read (any signed-in user)

| Endpoint | Returns |
|----------|---------|
| `GET /api/students` (`?search=&course=&semester=&at_risk=true`) | `[{id, student_id, name, course, score, semester, gpa, at_risk}]` one row per student/course/semester; `gpa` = that semester's GPA, `at_risk` = student's cumulative GPA is below the threshold. Students with no results yet don't appear here |
| `GET /api/students/<id>` | `{id, name, gpa, failing_courses, at_risk, records[], semester_gpa[]}`; `gpa` is `null` until the student has a result (404 if unknown) |
| `GET /api/courses` | `[{course, average_score, pass_rate, students}]` hardest first |
| `GET /api/analytics` | `{total_students, average_gpa, highest_gpa, pass_rate}` |
| `GET /api/top-students` (`?limit=5`) | `[{id, name, gpa}]` highest cumulative GPA first |
| `GET /api/course-difficulty` | `[{course, average_score, students}]` hardest first |
| `GET /api/at-risk-students` | `[{id, name, gpa, failing_courses}]` lowest GPA first |
| `GET /api/gpa-trend` | `[{semester, average_gpa}]` chronological |
| `GET /api/health` | `{status: "ok"}` (public) |

### Account

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/login` `{username, password}` | `{token, expires_in, user}` (public) |
| `GET /api/auth/me` | `{user}` |
| `POST /api/auth/change-password` `{current_password, new_password}` | `{token, user}`; other sessions are signed out |

### Write (admin only)

| Endpoint | Body |
|----------|------|
| `POST /api/students` | `{name}` -> 201 |
| `PUT /api/students/<id>` | `{name}` |
| `DELETE /api/students/<id>` | removes the student and their results -> 204 |
| `POST /api/students/<id>/records` | `{course, semester, score}` -> 201 |
| `PUT /api/records/<id>` | any of `{course, semester, score}` |
| `DELETE /api/records/<id>` | -> 204 |
| `POST /api/import` | `{csv, dry_run?, on_duplicate?}` bulk-import results from CSV text (see below) |
| `GET /api/users`, `POST /api/users` | `{username, password, role}` |
| `PATCH /api/users/<id>` | any of `{role, active, password}` |
| `GET /api/audit` (`?limit=100`) | newest entries first |

Limits: name 100 characters, course 60, semester 20, score a number from 0 to 100. A student can have one
result per course per semester (409 otherwise).

Errors are JSON `{error, message}` (validation errors also include `field`) with the matching HTTP status.
CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` by default; set `CORS_ORIGINS` for others.

## Bulk import

`POST /api/import` (admin) takes `{"csv": "<file text>", "dry_run": true|false, "on_duplicate": "skip"|"update"}`.

- Columns (any order, case-insensitive, extra columns ignored): `Student` (or `Name`), `Course`, `Semester`, `Score`.
  The file produced by the dashboard's "Export CSV" can be imported again as is.
- Comma, semicolon or tab separated; UTF-8 with or without BOM; with semicolons a decimal comma (`85,5`) is accepted.
- Students are matched by name and courses/semesters by their existing spelling, ignoring letter case, so
  `ada eze,math` lands on the existing `Ada Eze` / `Math`. Unknown students are created.
- A result that already exists (same student, course, semester) is skipped, or its score is updated with `on_duplicate: "update"`.
- **All or nothing:** if any row is invalid (blank name, score outside 0-100, duplicate rows in the file, ...) nothing is
  imported and the response lists the first 50 problems with their row numbers. Use `dry_run: true` to preview
  the counts and errors without writing anything.
- Limits: 5000 rows (`MAX_IMPORT_ROWS`) and 2 MB per file.

## Before going to production

- Set a real `SECRET_KEY` and serve over HTTPS (tokens are bearer credentials).
- Run with a production server (e.g. `gunicorn "app:create_app()"`), not `python app.py` (debug mode).
- With several worker processes the failed-sign-in counter is per process; use a shared store if that matters to you.
