import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course     TEXT NOT NULL,
    semester   TEXT NOT NULL,
    score      REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
    UNIQUE (student_id, course, semester)
);

CREATE INDEX IF NOT EXISTS idx_records_student ON records(student_id);
CREATE INDEX IF NOT EXISTS idx_records_course ON records(course);
CREATE INDEX IF NOT EXISTS idx_records_semester ON records(semester);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'viewer')),
    active        INTEGER NOT NULL DEFAULT 1,
    -- bumped on password/role/status changes so old login tokens stop working
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL DEFAULT (datetime('now')),
    username TEXT,
    action   TEXT NOT NULL,
    detail   TEXT
);

-- Follow-up actions for students (meetings, tutoring, ...). Notes can be sensitive: they are
-- never copied into the audit log.
CREATE TABLE IF NOT EXISTS interventions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN
                     ('meeting', 'tutoring', 'counselling', 'parent_contact', 'referral', 'other')),
    note         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    due_date     TEXT,
    created_by   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_interventions_student ON interventions(student_id);
CREATE INDEX IF NOT EXISTS idx_interventions_status ON interventions(status, due_date);

-- Grade points on a 4.0 scale (A=4 ... F=0), matching the frontend grade bands.
CREATE VIEW IF NOT EXISTS record_points AS
SELECT
    r.id, r.student_id, r.course, r.semester, r.score,
    CASE
        WHEN r.score >= 90 THEN 4.0
        WHEN r.score >= 80 THEN 3.0
        WHEN r.score >= 70 THEN 2.0
        WHEN r.score >= 60 THEN 1.0
        ELSE 0.0
    END AS points
FROM records r;
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate_user_roles(conn):
    """Databases created before the 'staff' role existed have a CHECK constraint that rejects it.
    SQLite can't alter a constraint, so rebuild the table (keeping every row, id and password)."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()
    if row is None or "'staff'" in row[0]:
        return
    conn.executescript("""
        BEGIN;
        CREATE TABLE users_new (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'viewer')),
            active        INTEGER NOT NULL DEFAULT 1,
            token_version INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users_new (id, username, password_hash, role, active, token_version, created_at)
            SELECT id, username, password_hash, role, active, token_version, created_at FROM users;
        DROP TABLE users;
        ALTER TABLE users_new RENAME TO users;
        COMMIT;
    """)


def init_db(database_path):
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
    conn.executescript(SCHEMA)
    _migrate_user_roles(conn)
    conn.commit()
    conn.close()
