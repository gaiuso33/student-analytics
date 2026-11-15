import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402
from base import ADMIN  # noqa: E402
from verify_backup import verify  # noqa: E402

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_app(path):
    return create_app({"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False,
                       "ADMIN_USERNAME": ADMIN[0], "ADMIN_PASSWORD": ADMIN[1]})


def token(client):
    return client.post("/api/auth/login", json={"username": ADMIN[0], "password": ADMIN[1]}).get_json()["token"]


def backup(src_path, dst_path):
    """Exactly what backup.sh does: SQLite's online backup API, safe while the app is running."""
    src, dst = sqlite3.connect(src_path), sqlite3.connect(dst_path)
    src.backup(dst)
    dst.close()
    src.close()


def restore(backup_path, live_path):
    """Exactly what restore.sh does: replace the file, and remove the write-ahead log of the old database."""
    shutil.copyfile(backup_path, live_path)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(live_path + suffix):
            os.remove(live_path + suffix)


class BackupRestoreDrill(unittest.TestCase):
    def test_a_backup_taken_while_running_brings_everything_back_after_a_disaster(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, saved = os.path.join(tmp, "live.db"), os.path.join(tmp, "backup.db")
            app = make_app(live)
            client = app.test_client()
            h = {"Authorization": f"Bearer {token(client)}"}
            client.post("/api/import", headers=h, json={"csv": "Student,Student ID,Class,Course,Semester,Score\n"
                                                              "Ann One,A-1,7A,Math,2025-1,30\nBen Two,B-1,7B,Math,2025-1,90\n"})
            made = client.post("/api/students/1/interventions", headers=h, json={"kind": "meeting", "note": "Keep this."})
            self.assertEqual(made.status_code, 201)
            client.post("/api/users", headers=h, json={"username": "teacher1", "password": "teacher-password-1", "role": "staff",
                                                       "scope": "classes", "classes": ["7A"]})

            backup(live, saved)                       # taken while the app is still using the database
            self.assertEqual(verify(saved), {"records": 2, "students": 2, "users": 2})

            # Disaster: someone deletes data
            client.delete("/api/students/1", headers=h)
            client.delete("/api/students/2", headers=h)
            self.assertEqual(client.get("/api/students", headers=h).get_json(), [])

            restore(saved, live)
            app2 = make_app(live)                      # the server starts again on the restored file
            client2 = app2.test_client()
            h2 = {"Authorization": f"Bearer {token(client2)}"}
            students = client2.get("/api/students", headers=h2).get_json()
            self.assertEqual(sorted((r["name"], r["student_code"], r["class_name"]) for r in students),
                             [("Ann One", "A-1", "7A"), ("Ben Two", "B-1", "7B")])
            followups = client2.get("/api/students/1/interventions", headers=h2).get_json()
            self.assertEqual([f["note"] for f in followups], ["Keep this."])

            # accounts and their access come back too, and they can still sign in
            teacher = client2.post("/api/auth/login", json={"username": "teacher1", "password": "teacher-password-1"}).get_json()
            self.assertEqual((teacher["user"]["scope"], teacher["user"]["classes"]), ("classes", ["7A"]))
            visible = client2.get("/api/students", headers={"Authorization": f"Bearer {teacher['token']}"}).get_json()
            self.assertEqual([r["name"] for r in visible], ["Ann One"])

    def test_restoring_over_a_database_with_a_write_ahead_log_does_not_mix_old_and_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, saved = os.path.join(tmp, "live.db"), os.path.join(tmp, "backup.db")
            app = make_app(live)
            client = app.test_client()
            h = {"Authorization": f"Bearer {token(client)}"}
            client.post("/api/students", headers=h, json={"name": "Before Backup"})
            backup(live, saved)
            client.post("/api/students", headers=h, json={"name": "After Backup"})   # lives in the -wal file, not yet merged
            restore(saved, live)
            conn = sqlite3.connect(live)
            names = [r[0] for r in conn.execute("SELECT name FROM students ORDER BY name")]
            conn.close()
            self.assertEqual(names, ["Before Backup"])


class VerifyBackupTests(unittest.TestCase):
    def test_bad_files_are_rejected_with_a_plain_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            garbage = os.path.join(tmp, "garbage.db")
            with open(garbage, "wb") as f:
                f.write(b"this is not a database at all" * 50)
            with self.assertRaises(ValueError) as ctx:
                verify(garbage)
            self.assertIn("not a readable SQLite database", str(ctx.exception))

            other = os.path.join(tmp, "other.db")
            c = sqlite3.connect(other)
            c.execute("CREATE TABLE something_else (x)")
            c.commit()
            c.close()
            with self.assertRaises(ValueError) as ctx:
                verify(other)
            self.assertIn("not a backup of the student database", str(ctx.exception))

            self.assertRaises(ValueError, verify, os.path.join(tmp, "does-not-exist.db"))

    def test_a_truncated_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            live, saved, cut = (os.path.join(tmp, n) for n in ("live.db", "backup.db", "cut.db"))
            make_app(live)
            backup(live, saved)
            with open(saved, "rb") as f:
                data = f.read()
            with open(cut, "wb") as f:
                f.write(data[: len(data) // 2])
            with self.assertRaises(ValueError):
                verify(cut)

    def test_a_backup_without_accounts_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "live.db")
            make_app(live)
            conn = sqlite3.connect(live)
            conn.execute("DELETE FROM users")
            conn.commit()
            conn.close()
            with self.assertRaises(ValueError) as ctx:
                verify(live)
            self.assertIn("no user accounts", str(ctx.exception))

    def test_the_command_line_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "live.db")
            make_app(live)
            ok = subprocess.run([sys.executable, "verify_backup.py", live], cwd=BACKEND, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("Backup looks valid", ok.stdout)
            bad = subprocess.run([sys.executable, "verify_backup.py", os.path.join(tmp, "nope.db")], cwd=BACKEND, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("Backup rejected", bad.stderr)


if __name__ == "__main__":
    unittest.main()
