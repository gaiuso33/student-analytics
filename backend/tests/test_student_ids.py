import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402
from base import ADMIN, ApiTestCase  # noqa: E402

HEADER = "Student,Student ID,Course,Semester,Score\n"


class IdCase(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    def make(self, name, code=None, **extra):
        body = {"name": name, **({"student_code": code} if code is not None else {}), **extra}
        return self.request("POST", "/api/students", json=body)

    def imp(self, csv_text, **extra):
        res = self.request("POST", "/api/import", json={"csv": csv_text, **extra})
        return res.status_code, res.get_json()

    def everyone(self, search=""):
        return self.get("/api/students" + (f"?search={search}" if search else ""))


class CreateAndReadTests(IdCase):
    def test_a_student_can_have_an_id_which_shows_everywhere(self):
        res = self.make("Ida Idowu", "ADM-001")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["student_code"], "ADM-001")
        sid = res.get_json()["id"]
        self.request("POST", f"/api/students/{sid}/records", json={"course": "Math", "semester": "2025-1", "score": 30})

        self.assertEqual(self.get(f"/api/students/{sid}")["student_code"], "ADM-001")
        self.assertEqual(self.everyone("ida")[0]["student_code"], "ADM-001")
        self.assertEqual(self.get("/api/top-students")[0]["student_code"], "ADM-001")
        self.assertEqual(next(r for r in self.get("/api/at-risk-students") if r["id"] == sid)["student_code"], "ADM-001")

    def test_search_finds_students_by_id(self):
        sid = self.make("Searchable Sam", "SRCH/2025/77").get_json()["id"]
        self.request("POST", f"/api/students/{sid}/records", json={"course": "Math", "semester": "2025-1", "score": 70})
        self.assertEqual([r["name"] for r in self.everyone("srch/2025")], ["Searchable Sam"])

    def test_ids_must_be_unique_ignoring_case(self):
        self.assertEqual(self.make("First One", "UNIQ-1").status_code, 201)
        res = self.make("Second One", "uniq-1")
        self.assertEqual(res.status_code, 409)
        self.assertIn("student ID is already in use", res.get_json()["message"])

    def test_bad_ids_are_refused(self):
        for bad in ("has space", "x" * 31, "bad!id", "-leading", 5, ["x"]):
            res = self.make("Bad Id", bad)
            self.assertEqual(res.status_code, 400, bad)
            self.assertEqual(res.get_json()["field"], "student_code")
        for fine in ("2024/0123", "A.B-C_1".replace("_", "-"), "x" * 30):
            self.assertEqual(self.make(f"Fine {fine[:6]}", fine).status_code, 201, fine)

    def test_blank_id_means_none(self):
        res = self.make("No Id Person", "  ")
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.get_json()["student_code"])


class SameNameTests(IdCase):
    def test_two_students_can_share_a_name_only_if_both_have_ids(self):
        self.assertEqual(self.make("Pat Twin", "TW-1").status_code, 201)
        self.assertEqual(self.make("pat twin", "TW-2").status_code, 201)     # different ID: fine
        clash = self.make("Pat Twin")                                        # no ID: could be either of them
        self.assertEqual(clash.status_code, 409)
        self.assertIn("student ID to tell them apart", clash.get_json()["message"])

    def test_a_student_without_an_id_blocks_a_namesake(self):
        self.assertEqual(self.make("Solo Sue").status_code, 201)
        self.assertEqual(self.make("Solo Sue", "SOLO-1").status_code, 409)   # the existing Sue has no ID to tell them apart
        self.assertEqual(self.make("Solo Sue").status_code, 409)

    def test_renaming_respects_the_same_rules(self):
        a = self.make("Rename A", "REN-A").get_json()["id"]
        b = self.make("Other Name", "REN-B").get_json()["id"]
        ok = self.request("PUT", f"/api/students/{b}", json={"name": "Rename A"})   # both have IDs
        self.assertEqual(ok.status_code, 200)
        # dropping an ID would make two same-named students indistinguishable
        res = self.request("PUT", f"/api/students/{b}", json={"name": "Rename A", "student_code": None})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self.request("PUT", f"/api/students/{a}", json={"name": "Rename A", "student_code": "REN-B"}).status_code, 409)

    def test_update_keeps_or_changes_the_id(self):
        sid = self.make("Keeper Kay", "KEEP-1").get_json()["id"]
        kept = self.request("PUT", f"/api/students/{sid}", json={"name": "Keeper Kay Jr"}).get_json()
        self.assertEqual(kept["student_code"], "KEEP-1")               # key left out: unchanged
        changed = self.request("PUT", f"/api/students/{sid}", json={"name": "Keeper Kay Jr", "student_code": "KEEP-2"}).get_json()
        self.assertEqual(changed["student_code"], "KEEP-2")
        cleared = self.request("PUT", f"/api/students/{sid}", json={"name": "Keeper Kay Jr", "student_code": ""}).get_json()
        self.assertIsNone(cleared["student_code"])

    def test_changes_are_audited(self):
        self.make("Audited Al", "AUD-1")
        entries = self.get("/api/audit?limit=5")
        self.assertTrue(any(e["action"] == "student.create" and "code=AUD-1" in e["detail"] for e in entries))


class ImportTests(IdCase):
    def test_ids_keep_namesakes_apart(self):
        code, body = self.imp(HEADER + "Sam Lee,SL-1,Math,2025-1,80\nSam Lee,SL-2,Math,2025-1,40\n")
        self.assertEqual((code, body["students_created"], body["records_created"]), (200, 2, 2))
        rows = self.everyone("sam lee")
        self.assertEqual(len({r["student_id"] for r in rows}), 2)
        self.assertEqual({r["student_code"]: r["score"] for r in rows}, {"SL-1": 80, "SL-2": 40})

    def test_a_row_for_an_existing_id_finds_that_student(self):
        self.make("Ines Existing", "EX-1")
        code, body = self.imp(HEADER + "Ines Existing,EX-1,Math,2025-1,66\n")
        self.assertEqual((code, body["students_created"], body["records_created"]), (200, 0, 1))
        self.assertEqual(len([s for s in self.everyone("ines")]), 1)

    def test_an_id_that_belongs_to_someone_else_is_an_error(self):
        self.make("Owner Olu", "OWN-1")
        code, body = self.imp(HEADER + "Someone Else,OWN-1,Math,2025-1,50\n")
        self.assertEqual(code, 400)
        self.assertIn("Student ID OWN-1 already belongs to Owner Olu, not Someone Else", body["errors"][0]["message"])
        self.assertEqual(self.everyone("someone"), [])   # nothing was imported

    def test_a_name_that_could_be_two_people_is_not_guessed(self):
        self.make("Twin Tia", "TT-1")
        self.make("Twin Tia", "TT-2")
        code, body = self.imp("Student,Course,Semester,Score\nTwin Tia,Math,2025-1,70\n")
        self.assertEqual(code, 400)
        self.assertIn("Several students are called Twin Tia", body["errors"][0]["message"])

    def test_name_only_rows_still_match_when_the_name_is_unique(self):
        self.make("Unique Uma", "UU-1")
        code, body = self.imp("Student,Course,Semester,Score\nunique uma,Math,2025-1,70\n")
        self.assertEqual((code, body["students_created"], body["records_created"]), (200, 0, 1))

    def test_ids_are_added_to_existing_students_found_by_name(self):
        lola = self.make("Late Lola").get_json()["id"]            # recorded before the school had IDs
        code, preview = self.imp(HEADER + "Late Lola,LL-9,Math,2025-1,70\n", dry_run=True)
        self.assertEqual((preview["student_ids_added"], preview["students_created"]), (1, 0))
        self.assertIsNone(self.get(f"/api/students/{lola}")["student_code"])   # the preview wrote nothing
        code, body = self.imp(HEADER + "Late Lola,LL-9,Math,2025-1,70\n")
        self.assertEqual((code, body["student_ids_added"], body["students_created"]), (200, 1, 0))
        self.assertEqual(self.everyone("late lola")[0]["student_code"], "LL-9")
        again = self.imp(HEADER + "Late Lola,LL-9,Physics,2025-1,55\n")[1]
        self.assertEqual((again["student_ids_added"], again["students_created"]), (0, 0))

    def test_header_names_for_the_id_column(self):
        for i, header in enumerate(("Admission Number", "ID", "student_id", "Reg No", "Admission No.")):
            csv_text = f"Name,{header},Course,Semester,Score\nAlias Al{i},AL-{i},Math,2025-1,70\n"
            code, body = self.imp(csv_text)
            self.assertEqual((code, body["students_created"]), (200, 1), header)
            self.assertEqual(self.everyone(f"alias al{i}")[0]["student_code"], f"AL-{i}")

    def test_file_level_id_problems(self):
        code, body = self.imp(HEADER + "A Person,BAD ID!,Math,2025-1,70\n")
        self.assertEqual(code, 400)
        self.assertIn("Student ID can use letters", body["errors"][0]["message"])
        # the same ID for two different people inside one file
        code, body = self.imp(HEADER + "First Fay,DUP-1,Math,2025-1,70\nSecond Sid,DUP-1,Math,2025-1,60\n")
        self.assertEqual(code, 400)
        self.assertIn("already belongs to First Fay", body["errors"][0]["message"])
        # the same person on several rows is fine
        code, body = self.imp(HEADER + "Same Sal,SS-1,Math,2025-1,70\nSame Sal,SS-1,English,2025-1,60\n")
        self.assertEqual((code, body["students_created"], body["records_created"]), (200, 1, 2))

    def test_the_dashboard_export_can_be_imported_again(self):
        text = "Student,Student ID,Course,Semester,Score,Grade,GPA,At risk\r\nRound Rita,RR-1,Math,2030-1,91,A,4,No\r\n"
        code, body = self.imp(text)
        self.assertEqual((code, body["students_created"], body["error_count"]), (200, 1, 0))
        self.assertEqual(self.everyone("round rita")[0]["student_code"], "RR-1")

    def test_old_students_without_ids_that_share_a_name_must_be_given_ids_first(self):
        conn = sqlite3.connect(self.app.config["DATABASE"])
        conn.execute("INSERT INTO students (name) VALUES ('Legacy Lee'), ('legacy lee')")
        conn.commit()
        conn.close()
        code, body = self.imp(HEADER + "Legacy Lee,LG-1,Math,2025-1,70\n")
        self.assertEqual(code, 400)
        self.assertIn("Several students without an ID are called Legacy Lee", body["errors"][0]["message"])


class MigrationTests(unittest.TestCase):
    def test_old_database_drops_the_unique_name_rule_and_keeps_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
                CREATE TABLE students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
                CREATE TABLE records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    course TEXT NOT NULL, semester TEXT NOT NULL,
                    score REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
                    UNIQUE (student_id, course, semester));
                INSERT INTO students (id, name) VALUES (3, 'Old Ann'), (9, 'Old Bob');
                INSERT INTO records (student_id, course, semester, score) VALUES (3, 'Math', '2025-1', 80), (9, 'Math', '2025-1', 40);
            """)
            old.commit()
            old.close()

            cfg = {"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False, "ADMIN_USERNAME": ADMIN[0], "ADMIN_PASSWORD": ADMIN[1]}
            app = create_app(cfg)
            client = app.test_client()
            token = client.post("/api/auth/login", json={"username": ADMIN[0], "password": ADMIN[1]}).get_json()["token"]
            headers = {"Authorization": f"Bearer {token}"}

            rows = client.get("/api/students", headers=headers).get_json()
            self.assertEqual({(r["student_id"], r["name"], r["student_code"], r["score"]) for r in rows},
                             {(3, "Old Ann", None, 80), (9, "Old Bob", None, 40)})

            # names are no longer unique, IDs are
            self.assertEqual(client.post("/api/students", headers=headers, json={"name": "Old Ann", "student_code": "NEW-1"}).status_code, 409)  # old Ann has no ID
            client.put("/api/students/3", headers=headers, json={"name": "Old Ann", "student_code": "OA-1"})
            self.assertEqual(client.post("/api/students", headers=headers, json={"name": "Old Ann", "student_code": "OA-2"}).status_code, 201)
            self.assertEqual(client.post("/api/students", headers=headers, json={"name": "Dup", "student_code": "oa-1"}).status_code, 409)

            # the rebuilt table is still the target of the foreign keys: deleting a student removes their results
            client.post("/api/students/3/interventions", headers=headers, json={"kind": "meeting", "note": "x"})
            self.assertEqual(client.delete("/api/students/3", headers=headers).status_code, 204)
            conn = sqlite3.connect(path)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM records WHERE student_id = 3").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM interventions WHERE student_id = 3").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM records WHERE student_id = 9").fetchone()[0], 1)
            conn.close()

            create_app({**cfg, "ADMIN_PASSWORD": None})     # starting again changes nothing
            # (the list only shows students who have results: Old Bob is the one left)
            remaining = client.get("/api/students", headers=headers).get_json()
            self.assertEqual([(r["student_id"], r["name"]) for r in remaining], [(9, "Old Bob")])


class DemoDataTests(ApiTestCase):
    def test_every_demo_student_has_a_unique_admission_number(self):
        rows = self.get("/api/students")
        codes = {r["student_id"]: r["student_code"] for r in rows}
        self.assertEqual(len(codes), 40)
        self.assertTrue(all(c and c.startswith("ADM-") for c in codes.values()))
        self.assertEqual(len(set(codes.values())), 40)


if __name__ == "__main__":
    unittest.main()
