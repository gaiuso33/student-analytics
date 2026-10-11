"""Demo data. Run `python seed.py --reset` to rebuild the database."""
import argparse
import datetime
import os
import random
import sqlite3

from config import Config
from db import init_db

COURSES = {
    # course: difficulty offset applied to every score
    "Mathematics": -8,
    "Physics": -6,
    "Chemistry": -3,
    "Computer Science": 2,
    "Economics": 0,
    "English": 4,
}
SEMESTERS = ["2024-1", "2024-2", "2025-1", "2025-2"]

FIRST = ["Amara", "Tunde", "Chioma", "Ibrahim", "Ngozi", "Seun", "Fatima", "Emeka",
         "Bola", "Zainab", "Kelechi", "Yusuf", "Adaeze", "Femi", "Halima", "Chidi",
         "Temitope", "Aisha", "Obinna", "Funke"]
LAST = ["Okafor", "Adeyemi", "Bello", "Nwosu", "Balogun", "Eze", "Lawal", "Okonkwo",
        "Abubakar", "Afolabi"]


def seed(database_path, rng_seed=42):
    rng = random.Random(rng_seed)
    init_db(database_path)
    conn = sqlite3.connect(database_path)

    names = [f"{f} {l}" for f in FIRST for l in LAST]
    rng.shuffle(names)
    names = names[:40]

    for name in names:
        cur = conn.execute("INSERT INTO students (name) VALUES (?)", (name,))
        student_id = cur.lastrowid
        ability = rng.gauss(79, 9)      # long-run level of this student
        trend = rng.uniform(-1.5, 3)       # per-semester drift
        courses = rng.sample(list(COURSES), 4)
        for i, semester in enumerate(SEMESTERS):
            for course in courses:
                score = ability + trend * i + COURSES[course] + rng.gauss(0, 7)
                score = max(0, min(100, round(score)))
                conn.execute(
                    "INSERT INTO records (student_id, course, semester, score) VALUES (?,?,?,?)",
                    (student_id, course, semester, score),
                )
    seed_interventions(conn, rng)
    conn.commit()
    conn.close()


DEMO_FOLLOW_UPS = [
    ("meeting", "Met to go over recent results. Agreed a weekly study plan and a check-in after the next tests."),
    ("tutoring", "Arranged peer tutoring for the lowest-scoring course, twice a week."),
    ("parent_contact", "Called the guardian to share concerns about results and agree how to support at home."),
    ("counselling", "Referred to the school counsellor to talk through workload and study habits."),
    ("referral", "Referred to the learning-support team for an assessment."),
    ("other", "Added to the mid-semester review list; revisit after the next assessments."),
]


def seed_interventions(conn, rng):
    """Give most (not all) at-risk demo students a follow-up, so the dashboard shows both outcomes."""
    at_risk = conn.execute(
        "SELECT s.id FROM students s JOIN record_points p ON p.student_id = s.id "
        "GROUP BY s.id HAVING ROUND(AVG(p.points), 2) < ? ORDER BY s.id",
        (Config.AT_RISK_GPA,),
    ).fetchall()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for (student_id,) in at_risk:
        if rng.random() < 0.35:
            continue  # nobody following this one up yet
        for _ in range(rng.choice([1, 1, 2])):
            kind, note = rng.choice(DEMO_FOLLOW_UPS)
            created = now - datetime.timedelta(days=rng.randint(1, 30))
            stamp = created.strftime("%Y-%m-%d %H:%M:%S")
            if rng.random() < 0.4:  # finished
                done = (created + datetime.timedelta(days=rng.randint(1, 5))).strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "INSERT INTO interventions (student_id, kind, note, status, created_by, created_at, "
                    "updated_at, completed_at) VALUES (?, ?, ?, 'done', 'demo.staff', ?, ?, ?)",
                    (student_id, kind, note, stamp, done, done),
                )
            else:  # still open, some already overdue
                due = (now + datetime.timedelta(days=rng.randint(-10, 20))).strftime("%Y-%m-%d")
                conn.execute(
                    "INSERT INTO interventions (student_id, kind, note, due_date, created_by, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, 'demo.staff', ?, ?)",
                    (student_id, kind, note, due, stamp, stamp),
                )


def is_empty(database_path):
    conn = sqlite3.connect(database_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete the existing database first")
    args = parser.parse_args()
    path = Config.DATABASE
    if args.reset and os.path.exists(path):
        os.remove(path)
    init_db(path)
    if is_empty(path):
        seed(path)
        print(f"Seeded {path}")
    else:
        print("Database already has data (use --reset to rebuild).")
