# Student Analytics Dashboard

**Version 1.0.0** · 2026-10-08

A web dashboard for schools and departments to track student performance: grades, GPA trends, course
difficulty and students at risk. Staff sign in with their own accounts; administrators can enter, import and
edit data, while viewers get read-only access.

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Run it locally](#run-it-locally)
- [Configuration](#configuration)
- [Accounts, roles and security](#accounts-roles-and-security)
- [API overview](#api-overview)
- [Testing](#testing)
- [Deployment](#deployment)
- [Release checklist and tagging v1.0.0](#release-checklist-and-tagging-v100)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)
- [Version history](#version-history)

---

## What it does

**Dashboards**
- **Overview:** total students, average and highest GPA, pass rate; **insights** in plain language (how GPA and pass rate moved
  since the previous semester, students who dropped or improved sharply, the course with the lowest pass rate); top students,
  hardest courses, at-risk students;
  charts for average GPA by semester, grade distribution (A to F) and average score per course (with the pass-mark line).
- **Students:** every result as a row. Search by name or course; filter by course, semester, score range and
  "at-risk students only"; sort any column; page through 10/25/50/100 rows. All of this is kept in the page
  address, so a filtered view can be bookmarked or shared. At-risk students carry a badge.
- **Student detail:** cumulative GPA, risk status, GPA per semester chart, and every result with its letter grade.
- **Courses:** average score, pass rate and number of students per course, hardest first.
- **Export:** download the current filtered, sorted list as a CSV (opens in Excel).

**Data entry (administrators)**
- Add, rename and delete students; add, edit and delete individual results (with confirmation on deletes).
- **Bulk import** from CSV: preview first, matching of existing students and courses ignoring capital letters, choice
  of keeping or replacing existing scores, all-or-nothing safety if any row has a problem.
- Manage staff accounts: create users, change roles, deactivate/reactivate, reset passwords.
- **Audit log** of sign-ins, failed sign-ins and every data change.

**Everything else**
- Light and dark theme (follows your system until you choose), phone-friendly layout with a collapsible menu,
  keyboard-accessible tables and forms, loading and error states with retry on every panel.

### Business rules

| Rule | Default | Where to change |
|------|---------|-----------------|
| A result passes when score ≥ | **60** | `PASS_MARK` (backend) and `PASS_MARK` in `frontend/src/utils/grades.js`: keep both equal |
| Grade bands | A 90+, B 80+, C 70+, D 60+, F below 60 | `frontend/src/utils/grades.js` and the SQL view in `backend/db.py` |
| Grade points | A=4, B=3, C=2, D=1, F=0 | `backend/db.py` (view `record_points`) |
| Cumulative GPA | average grade points over all of a student's results | |
| Semester GPA | the same, for one semester | |
| A student is **at risk** when cumulative GPA is below | **2.0** | `AT_RISK_GPA` (backend) |

## How it works

```
Browser ──HTTPS──> Caddy ─┬─ /api/*  ──> Gunicorn + Flask ──> SQLite (volume)
                          └─ everything else: the built React app
```

- **Frontend:** React 19, Vite 7, React Router, Recharts. Talks to the API with a bearer token kept in the browser
  tab (cleared when the tab closes).
- **Backend:** Flask, SQLite (WAL mode), Gunicorn. Passwords hashed with scrypt; login tokens are signed and expire.
- **One address in production:** Caddy serves the site and forwards `/api` to the backend, so there is no CORS setup and
  the backend is never exposed directly. Caddy also gets and renews the HTTPS certificate automatically.

## Repository layout

```
student-analytics/
├── backend/  # Flask + SQLite API
│   ├── tests/  # 58 automated tests  [base.py, test_api.py, test_auth.py, test_import.py, test_insights.py, test_write.py]
│   ├── .dockerignore
│   ├── .env.example
│   ├── .gitignore
│   ├── app.py  # app factory and read endpoints
│   ├── auth.py  # login, tokens, roles, audit helper, throttling
│   ├── config.py  # settings and business rules
│   ├── db.py  # schema and connections
│   ├── Dockerfile
│   ├── importer.py  # bulk CSV import
│   ├── insights.py  # plain-language findings for the Overview page
│   ├── manage.py  # command-line account management
│   ├── README.md
│   ├── requirements.txt
│   ├── seed.py  # demo data
│   ├── users.py  # user management and audit log endpoints
│   ├── validation.py  # input validation rules
│   ├── write.py  # add/edit/delete students and results
│   └── wsgi.py  # production entry point (gunicorn)
├── frontend/  # React + Vite app
│   ├── public/  # static files (theme-init.js, SPA redirects)  [_redirects, theme-init.js]
│   ├── src/
│   │   ├── api/  # API client (adds the login token)  [client.js]
│   │   ├── auth/  # sign-in state and route guards  [AuthProvider.jsx, RequireAdmin.jsx, RequireAuth.jsx, context.js, useAuth.js]
│   │   ├── components/  # shared UI pieces
│   │   │   ├── AsyncCard.jsx
│   │   │   ├── AtRiskStudents.jsx
│   │   │   ├── ChartCard.jsx
│   │   │   ├── Charts.jsx
│   │   │   ├── CourseDifficulty.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   ├── Filters.jsx
│   │   ├── InsightsCard.jsx
│   │   │   ├── Leaderboard.jsx
│   │   │   ├── NameForm.jsx
│   │   │   ├── Pagination.jsx
│   │   │   ├── ResultForm.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── StatsCards.jsx
│   │   │   ├── StudentTable.jsx
│   │   │   └── ThemeToggle.jsx
│   │   ├── hooks/  # useFetch, useTheme  [useFetch.js, useTheme.js]
│   │   ├── pages/  # one file per screen
│   │   │   ├── AccountPage.jsx
│   │   │   ├── AuditPage.jsx
│   │   │   ├── CoursesPage.jsx
│   │   │   ├── ImportPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── NewStudentPage.jsx
│   │   │   ├── NotFoundPage.jsx
│   │   │   ├── OverviewPage.jsx
│   │   │   ├── StudentDetailPage.jsx
│   │   │   ├── StudentsPage.jsx
│   │   │   └── UsersPage.jsx
│   │   ├── styles/  # all CSS, light and dark themes  [dashboard.css]
│   │   ├── utils/  # filtering, sorting, grades, CSV, validation (+ unit tests)  [csv.js, csv.test.js, grades.js, grades.test.js, students.js, students.test.js, validate.js, validate.test.js]
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .dockerignore
│   ├── .env.example
│   ├── .env.production
│   ├── Dockerfile
│   ├── index.html
│   └── README.md
├── .env.example  # production settings template
├── .gitignore
├── backup.sh  # database backup script
├── Caddyfile  # HTTPS, security headers, /api proxy, static site
└── docker-compose.yml  # production stack: web + backend + volumes
```

Your frontend folder also keeps its own `package.json`, `package-lock.json`, `vite.config.js` and `eslint.config.js`.

## Run it locally

You need **Node.js 20.19+ or 22.12+** (check with `node -v`) and **Python 3.10+** (tested on 3.12).

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
python app.py                      # http://127.0.0.1:5000
```

On the first start the database is created, filled with **demo data** (40 fake students, 6 courses, 4 semesters),
and an **admin account** is created. To choose the admin login yourself, export `ADMIN_USERNAME` and
`ADMIN_PASSWORD` (at least 10 characters) before the first start. Otherwise a random password is printed
**once** in the terminal.

Reset to fresh demo data: stop the server, delete `backend/students.db`, start again (this deletes accounts too).
Set `SEED_DEMO_DATA=0` to start with an empty database.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Sign in with the admin account. The dev server calls the API at `http://127.0.0.1:5000` (see `frontend/.env.example`).

> `npm run preview` serves a production build, which expects the API on the same address (`/api`). For day-to-day
> work use `npm run dev`.

## Configuration

### Backend environment variables

Exported in the terminal (or set in `.env` for Docker). The backend does **not** read `.env` files by itself.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | *(random per start)* | Signs login tokens. **Required in production** (`wsgi.py` refuses to start without it). If it changes, everyone is signed out |
| `ADMIN_USERNAME` | `admin` | First-run administrator (only used while there are no users) |
| `ADMIN_PASSWORD` | *(random, printed once)* | First-run administrator password, minimum 10 characters |
| `SEED_DEMO_DATA` | `1` locally, `0` in Docker | Fill an empty database with fake students |
| `DATABASE` | `students.db` | Path of the SQLite file |
| `PASS_MARK` | `60` | Passing score |
| `AT_RISK_GPA` | `2.0` | At-risk threshold |
| `TOKEN_MAX_AGE` | `28800` | Sign-in lifetime in seconds (8 hours) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins (only needed when the site and API are on different addresses). `python app.py` also allows any localhost port automatically |
| `INSIGHT_GPA_CHANGE` | `1.0` | How far a student's semester GPA must move to be listed as improving or declining |
| `LOGIN_MAX_FAILS` / `LOGIN_LOCK_SECONDS` | `5` / `60` | Failed-sign-in lockout |
| `MAX_IMPORT_ROWS` | `5000` | Rows per CSV import (file size limit is 2 MB) |

### Frontend environment variables

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Where the API lives. Dev: `http://127.0.0.1:5000`. Docker build: empty (same address). Split hosting: the API's full URL |

## Accounts, roles and security

| Role | Can do |
|------|--------|
| **Viewer** | See every dashboard and student, export CSV, change own password |
| **Administrator** | Everything a viewer can, plus add/edit/delete students and results, import CSV, manage users, read the audit log |

- Permissions are enforced **on the server**, not just hidden in the interface.
- Passwords: minimum 10 characters, hashed (scrypt). Changing a password, role or status signs that user out everywhere.
- Five wrong passwords for a username locks it for a minute. Messages never reveal whether a username exists.
- Administrators can't change their own role or status, so at least one administrator always remains.
- Accounts are deactivated rather than deleted, so the audit log always makes sense.
- API responses are marked non-cacheable; the production proxy adds HTTPS, HSTS and a strict Content-Security-Policy.
- Command line (inside `backend/`, or `docker compose exec backend ...` in production):
  `python manage.py create-user alice --role admin` and `python manage.py set-password alice`.

**Student records are personal data.** Before real use, decide who may have accounts, make sure the people whose
data you hold are covered by your institution's data-protection rules, keep backups somewhere private, and only
serve the site over HTTPS.

## API overview

All endpoints need `Authorization: Bearer <token>` except `GET /api/health` and `POST /api/auth/login`.
The full reference, with request and response shapes, is in [`backend/README.md`](backend/README.md).

| Area | Endpoints |
|------|-----------|
| Sign-in | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/change-password` |
| Read (anyone signed in) | `GET /api/students`, `/api/students/<id>`, `/api/courses`, `/api/analytics`, `/api/top-students`, `/api/course-difficulty`, `/api/at-risk-students`, `/api/gpa-trend`, `/api/insights` |
| Write (admin) | `POST/PUT/DELETE /api/students…`, `POST /api/students/<id>/records`, `PUT/DELETE /api/records/<id>`, `POST /api/import` |
| Admin | `GET/POST /api/users`, `PATCH /api/users/<id>`, `GET /api/audit` |

Errors are JSON: `{ "error": "...", "message": "..." }` with the matching HTTP status.

### CSV import format

Columns **Student, Course, Semester, Score** (any order; `Name`, `Term`, `Subject`, `Marks` also work; extra columns
are ignored). Comma, semicolon or tab separated. The file from "Export CSV" can be imported again as is.
In the app: **Import data** in the sidebar, which also offers a template download.

## Testing

```bash
# Backend: 58 tests (API, sign-in and roles, writes, user admin, CSV import, insights, CORS)
cd backend && python3 -m unittest discover -s tests -v

# Frontend: unit tests for filtering, sorting, paging, grades, CSV and form validation
cd frontend && npm install -D vitest      # once, if not already installed
npm test                                  # runs "vitest run"
```

> The frontend screens themselves have no automated tests yet. Use the [release checklist](#release-checklist-and-tagging-v100)
> after every change.

## Deployment

### Option A: one server with Docker (recommended)

This runs everything on a single Linux server, with automatic HTTPS and the database kept on a Docker volume.

**You need**
- A small Linux server (1 GB RAM is enough) with [Docker Engine and the Compose plugin](https://docs.docker.com/engine/install/).
- A domain name with an **A record** pointing to the server's IP address, and ports **80 and 443** open to the internet.

**Steps**

```bash
# 1. Put the project on the server (git clone, or copy the folder with scp/rsync)
cd student-analytics

# 2. Create the settings file
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"     # copy the output into SECRET_KEY=
nano .env       # set SECRET_KEY, SITE_ADDRESS=your.domain.example, ADMIN_USERNAME, ADMIN_PASSWORD

# 3. Build and start
docker compose up -d --build
docker compose ps                  # both services should be running/healthy
docker compose logs -f web         # Ctrl+C to stop watching; look for the certificate being obtained
```

Open `https://your.domain.example` and sign in with the admin account from `.env`.
Then change the admin password on the **Account** page and clear `ADMIN_PASSWORD` from `.env`.

**No domain yet?** Use `SITE_ADDRESS=localhost` to try the stack on your own machine (the browser will warn about
the self-signed certificate). `SITE_ADDRESS=:80` serves plain HTTP: fine for a quick test on a private network,
**never** for real use, because sign-in tokens would travel unprotected.

**Everyday operations**

| Task | Command |
|------|---------|
| View logs | `docker compose logs -f backend` or `... web` |
| Update to a new version | `git pull && docker compose up -d --build` (the data volume is kept) |
| Back up the database | `./backup.sh`, which writes `backups/students-<date>.db`. Run it from cron and copy the files off the server |
| Restore a backup | `docker compose stop backend`, then `docker compose cp backups/students-X.db backend:/data/students.db`, then `docker compose start backend` |
| Reset an admin password | `docker compose exec backend python manage.py set-password admin` |
| Add an account | `docker compose exec backend python manage.py create-user alice --role admin` |
| Stop everything | `docker compose down` (add `-v` **only** if you want to delete the database) |

Example nightly backup (edit with `crontab -e`):
`0 2 * * *  cd /path/to/student-analytics && ./backup.sh >> backups/backup.log 2>&1`

> **Keep your `.env` file and backups private.** The `.env` file holds the secret that signs logins; if it is
> ever exposed, set a new `SECRET_KEY` (everyone is signed out) and restart.

### Option B: split hosting

Static frontend on Netlify/Vercel/Cloudflare Pages, API on a server or a platform that offers a **persistent disk**
(SQLite needs one; free tiers with temporary disks will lose your data).

1. Backend: run `gunicorn --workers 1 --threads 8 wsgi:app` (or the Dockerfile in `backend/`) with `SECRET_KEY`,
   `DATABASE` (on the persistent disk), `SEED_DEMO_DATA=0`, `ADMIN_PASSWORD`, and
   `CORS_ORIGINS=https://your-frontend-address`. Serve it over HTTPS.
2. Frontend: build with `VITE_API_BASE_URL=https://your-api-address npm run build`, and publish `dist/`.
   `frontend/public/_redirects` already makes page reloads work on Netlify; on Vercel add a rewrite of all paths to `/index.html`.

### Production notes

- Run **one** Gunicorn worker (as configured). The failed-sign-in counter is kept in memory and SQLite has one writer;
  threads give plenty of concurrency for this workload.
- The backend container has no published port. Only the web container (Caddy) reaches it.
- The Content-Security-Policy in `Caddyfile` is strict. If the page is ever blank after a change, open the browser
  console: a "Refused to ..." message tells you what to allow.
- Docker, Caddy and the deployment files were written and syntax-checked but **have not been run on a real server
  yet**. Treat your first deployment as the test and follow the checklist below.

## Release checklist and tagging v1.0.0

Tick these on the deployed site (or locally) before calling it version 1:

- [ ] Open the site address: you land on the sign-in page; a wrong password shows a clear error.
- [ ] Sign in as admin; the Overview shows numbers, three charts and the three lists (with `SEED_DEMO_DATA=0` they are empty until you add data).
- [ ] **Users** → create a viewer account. Sign in as that viewer in a private window: no Add/Edit/Delete/Import buttons, no Users or Audit log in the menu.
- [ ] **Import data** → download the template, upload it: preview shows 2 rows, import, results appear on **Students**. Import again: results are skipped.
- [ ] Add a student with a score under 50: the at-risk badge and the "at-risk only" filter find them; export CSV opens in Excel.
- [ ] Edit and delete a result; delete the test student.
- [ ] Toggle dark mode; narrow the window below 760 px and use the menu.
- [ ] **Audit log** shows the actions above.
- [ ] Reload a deep link such as `/students?risk=1`: the page loads (not a 404).
- [ ] `./backup.sh` produces a file in `backups/`; restore it on a test copy once.
- [ ] Change the admin password and remove `ADMIN_PASSWORD` from `.env`.

Then record the release:

```bash
git init                                   # skip if already a repository
git add .
git commit -m "Student Analytics Dashboard v1.0.0"
git tag -a v1.0.0 -m "Version 1.0.0"
```

## Known limitations

- **Filtering, sorting and paging happen in the browser** on the full list of results. Comfortable up to a few thousand
  rows; beyond that the server should do it.
- **SQLite on one server.** Good for one institution; there is no clustering or automatic failover. Backups are your safety net.
- A student appears in the Students table only after their first result is recorded.
- Semesters are free text up to 20 characters; charts sort them alphabetically/numerically, so use a consistent
  format such as `2025-1`.
- The failed-sign-in lockout is per process and resets when the server restarts.
- No "forgot password" email: an administrator resets passwords (Users page or `manage.py`).
- No two-factor sign-in, and sign-in uses a token held in the browser tab; anyone who can run script in the page
  (for example through a malicious browser extension) could read it. The strict Content-Security-Policy reduces this risk.
- No UI tests; screens are verified manually with the release checklist.
- Pass mark and grade bands live in two places (frontend and backend) and must be changed together.

## Roadmap

Ideas for later versions, roughly by value:

1. Server-side filtering and paging (needed for large datasets).
2. Automated browser tests for the main journeys (sign-in, import, add student).
3. Per-course and per-semester comparison views, and emailed alerts when a student drops sharply.
4. Student notes and intervention tracking for at-risk students.
5. Email password reset and optional two-factor sign-in.
6. PostgreSQL option for multi-server setups.
7. CI pipeline running both test suites on every change.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `vite: not found` | Run `npm install` in `frontend/`. Check `node -v` is 20.19+ or 22.12+ |
| Blank page, console says `React is not defined` | Config files must be named `vite.config.js` and `eslint.config.js` (dots, not underscores) |
| Page shows "Cannot reach the server" | The backend isn't running or is on another address. Start `python app.py` (local) or check `docker compose ps` |
| Sign-in says "Cannot reach the server" but the backend is running | The browser blocked the request (CORS). Locally, `python app.py` allows any localhost port; check the address bar matches. If another dev server holds port 5173, stop it, or run `npm run dev -- --port 5173 --strictPort`. In production with split hosting, set `CORS_ORIGINS` to the site's address |
| Signed out after every server restart | `SECRET_KEY` isn't set, so a new random key is generated each start. Set it |
| "Please sign in" even after signing in | The token expired (8 hours) or the account was changed/deactivated. Sign in again |
| "Too many failed attempts" | Wait a minute, or an admin can reset the password |
| Forgot the admin password | `python manage.py set-password admin` (or via `docker compose exec backend`) |
| Fake students appear in production | `SEED_DEMO_DATA` was not `0` on the first start. Delete the volume (`docker compose down -v`) **before you have real data** and start again |
| Import says "Missing column(s)" | The first row must contain Student, Course, Semester and Score headings |
| HTTPS certificate not issued | The domain's A record must point at the server and ports 80/443 must be reachable. Check `docker compose logs web` |
| `npm test` fails with "vitest not found" | `npm install -D vitest` |

## Version history

### 1.0.0 (2026-10-08)

First complete release.

- Overview, Students, Student detail and Courses screens with charts, filters, sorting, pagination and CSV export.
- Automated insights on the Overview (semester-over-semester GPA and pass-rate movement, students who dropped or improved, lowest pass-rate course).
- Backend with SQLite, sign-in, viewer/administrator roles, user management and audit log.
- Add, edit, delete and bulk-import of student results.
- Light/dark theme, mobile layout, accessibility work.
- Docker + Caddy production setup with automatic HTTPS, security headers and a backup script.
- 58 backend tests and frontend unit tests.
