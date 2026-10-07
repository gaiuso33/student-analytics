"""Demo data. Run `python seed.py --reset` to rebuild the database."""
import argparse
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
    conn.commit()
    conn.close()


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
