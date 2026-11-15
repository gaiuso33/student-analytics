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
| `viewer` | Read all dashboards, student data and follow-ups |
| `staff` | Everything a viewer can, plus record, edit and complete follow-ups |
| `admin` | Everything staff can, plus delete follow-ups, add/edit/delete students and results, import CSV, manage users, read the audit log |

- Passwords: at least 10 characters, stored hashed (scrypt via Werkzeug).
- Sign-in returns a signed bearer token valid for `TOKEN_MAX_AGE` seconds (8 hours default). Changing a
  user's password, role or status immediately signs out their existing sessions.
- 5 failed sign-ins for a username from one address lock it for 60 seconds (counted in memory, per process).
- Admins can't change their own role/status, so at least one admin always remains. Users are deactivated, not deleted.
- Command line: `python manage.py create-user alice --role admin` and `python manage.py set-password alice`.
- First run only: `ADMIN_PASSWORD`, if set, must be at least 10 characters or the server refuses to start. Setting both
  `DEMO_VIEWER_USERNAME` and `DEMO_VIEWER_PASSWORD` also creates a read-only account (useful for demos).
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
| `GET /api/insights` | `{semester, previous_semester, insights[]}`: plain-language findings from the latest two semesters. Each insight is `{id, tone: positive|warning|neutral, text, students?: [{id, name, detail}], link?}` |
| `GET /api/students/<id>/interventions` | Follow-ups for one student, open ones first: `[{id, student_id, student_name, kind, note, status, due_date, created_by, created_at, updated_at, completed_at, overdue}]` |
| `GET /api/interventions` (`?status=open|done|all&overdue=1&limit=`) | Follow-ups across all students; open ones by soonest due date (undated last) |
| `GET /api/reminders` | `{days_ahead, mine: {overdue, due_soon, open, items[]}, team: {overdue, open, unattended_at_risk}}`: follow-ups assigned to the signed-in user that need attention, and team-wide counts |
| `GET /api/gpa-trend` | `[{semester, average_gpa}]` chronological |
| `GET /api/health` | `{status: "ok"}` (public) |

### Account

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/login` `{username, password}` | `{token, expires_in, user}` (public) |
| `GET /api/auth/me` | `{user}` |
| `POST /api/auth/change-password` `{current_password, new_password}` | `{token, user}`; other sessions are signed out |

### Student IDs and classes

- `student_code` (a student ID / admission number: letters, digits, `.` `-` `/`, up to 30) is optional and unique ignoring case; `class_name`
  (up to 40 characters) is optional. Both come back on student rows, `GET /api/students/<id>`, top and at-risk lists.
- Names are **not** unique. Two students may share a name only if both have an ID (409 otherwise: "Give each of them a student ID").
- `POST /api/students` and `PUT /api/students/<id>` accept `student_code` and `class_name`; leave a field out to keep it, send `null` or `""` to remove it.
- `GET /api/students?class=7A` filters by class; `?search=` also matches IDs and classes. `GET /api/classes` lists the classes you can see, with student counts.
- **Import:** optional `Student ID` (aliases: `Admission Number`, `Admission No`, `Reg No`, `ID`, ...) and `Class` (aliases `Section`, `Form`, `Group`) columns.
  A row finds its student by ID; without an ID by name, but only if exactly one student has that name (otherwise a row error asks for IDs).
  A row whose ID is new but whose name matches one existing student without an ID adds the ID to that student. An ID that belongs to a
  different name is a row error. The summary reports `student_ids_added` and `classes_set`.

### Class-level access

Every user has `scope` (`all` or `classes`) and, for `classes`, a list of classes. Administrators always see everyone. A limited user sees only
students whose class matches one of theirs (ignoring case), and those students' results and follow-ups; students with no class are hidden from them.

- Enforced centrally: `scope.py` creates per-request views (`students_v`, `records_v`, `record_points_v`, `interventions_v`) and every read query uses them,
  so statistics, insights, lists, reminders and emails all respect it. A student from another class is a 404, indistinguishable from one that doesn't exist.
- Set with `POST /api/users` or `PATCH /api/users/<id>`: `{"scope": "classes", "classes": ["7A", "7B"]}`. Changes apply on the next request; nobody is signed out.
- A follow-up can only be assigned to someone who can see the student (400 otherwise); `GET /api/assignees?student=<id>` lists who can.
- `GET /api/auth/me` includes `scope` and `classes`.

### Follow-up owners and reminders

Every follow-up has `assigned_to` (a username or `null` for nobody), plus computed flags `overdue`, `due_soon` (due within
`REMINDER_DAYS_AHEAD` days, default 2) and `due_in_days`. Dates are UTC.

- `POST /api/students/<id>/interventions`: leave `assigned_to` out to assign it to yourself, send `null` or `""` for nobody, or a username.
  The assignee must be an **active staff member or administrator** (400 otherwise).
- `GET /api/interventions` also accepts `?assigned=me|unassigned|<username>` and `?attention=1` (overdue or due soon).
- `GET /api/assignees` (staff or admin): who can be chosen as an owner.
- `PATCH /api/auth/me` `{email}`: set or clear your own reminder email (`null`/`""` clears it). Admins can also set `email` when creating a
  user or via `PATCH /api/users/<id>` (an email change does not sign anyone out).

### Backups

`./backup.sh` (in the project root) writes a consistent copy of the database while the app is running. `./restore.sh <file>` verifies the backup
(`python verify_backup.py <file>`: opens read-only, integrity check, required tables, at least one user), saves the current data, stops the app,
swaps the file in, removes the old write-ahead log, and restarts. Practise a restore on a test copy before you need one.

### Reminder emails

```bash
python manage.py send-reminders --dry-run    # print what would be sent
python manage.py send-reminders              # send (needs SMTP_HOST); exits non-zero if any email failed
python manage.py send-reminders --days 7     # include follow-ups due within 7 days
```

One email per active staff member or administrator who has an address and has follow-ups assigned to them that are overdue or due soon:
counts and a link only. **Notes are never included, and student names only if `REMINDER_INCLUDE_NAMES=1`.** Settings: `SMTP_HOST`,
`SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SECURITY` (`starttls`, `ssl` or `none`), `MAIL_FROM`, `SITE_URL`,
`REMINDER_DAYS_AHEAD`. Run it daily from cron (see the main README).

### Follow-ups (staff or admin to write)

| Endpoint | Body |
|----------|------|
| `POST /api/students/<id>/interventions` | `{kind, note, due_date?, assigned_to?}` -> 201. `kind`: `meeting`, `tutoring`, `counselling`, `parent_contact`, `referral`, `other`. `note`: 1 to 1000 characters, line breaks allowed. `due_date`: `YYYY-MM-DD` or empty |
| `PATCH /api/interventions/<id>` | any of `{kind, note, due_date, assigned_to, status}`; `status` is `open` or `done` (completing sets `completed_at`, reopening clears it). `due_date: null` removes the date |
| `DELETE /api/interventions/<id>` | admin only -> 204 |

The audit log records who created, changed or deleted a follow-up but never the note text. `GET /api/at-risk-students` also returns
`open_interventions` and `last_intervention` for each student.

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
`python app.py` (the local development server) additionally allows **any** `localhost` / `127.0.0.1` port, so a Vite dev server that
moved to another port still works. Production (`wsgi.py`) never does.

## Insights

`GET /api/insights` compares the two most recent semesters (by semester label, sorted as text) and returns, when there is enough data:
the change in average GPA, the change in pass rate, students whose semester GPA fell or rose by at least `INSIGHT_GPA_CHANGE`
(default 1.0 GPA point; only students with results in both semesters), and the course with the lowest pass rate (needs two or more courses).
With fewer than two semesters of results the list is empty.

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
