import datetime
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reminder_emails  # noqa: E402
from app import create_app  # noqa: E402
from base import ADMIN, ApiTestCase  # noqa: E402

CSV = (
    "Student,Student ID,Class,Course,Semester,Score\n"
    "Ann Seven,A-1,7A,Math,2025-1,30\nAnn Seven,A-1,7A,Math,2025-2,35\n"
    "Ben Seven,A-2,7A,Math,2025-1,90\nBen Seven,A-2,7A,Math,2025-2,40\n"
    "Cy Other,B-1,7B,Math,2025-1,35\nCy Other,B-1,7B,Math,2025-2,30\n"
    "Dee Other,B-2,7B,Math,2025-1,95\nDee Other,B-2,7B,Math,2025-2,92\n"
    "Eve Nowhere,,,Math,2025-1,60\n"
)


def iso(offset=0):
    return (datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=offset)).isoformat()


class ClassCase(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        res = cls.client.post("/api/import", headers=cls.auth(cls.admin_token), json={"csv": CSV})
        assert res.status_code == 200, res.get_data(as_text=True)
        rows = cls.client.get("/api/students", headers=cls.auth(cls.admin_token)).get_json()
        cls.ids = {r["name"]: r["student_id"] for r in rows}
        cls._n = 0

    @classmethod
    def person(cls, role="staff", scope="all", classes=()):
        """A new account with the given access. Returns (username, token, user_id)."""
        cls._n += 1
        name, pw = f"cls{cls._n}", f"class-password-{cls._n}"
        cls.create_user(name, pw, role=role)
        uid = next(u["id"] for u in cls.client.get("/api/users", headers=cls.auth(cls.admin_token)).get_json() if u["username"] == name)
        body = {"scope": scope, "classes": list(classes)}
        res = cls.client.patch(f"/api/users/{uid}", json=body, headers=cls.auth(cls.admin_token))
        assert res.status_code == 200, res.get_data(as_text=True)
        return name, cls.login(name, pw), uid

    def names(self, token, url="/api/students"):
        return sorted({r["name"] for r in self.get(url, token)})


class WhatEachPersonSeesTests(ClassCase):
    def test_a_limited_person_sees_only_their_class_everywhere(self):
        _, t, _ = self.person(scope="classes", classes=["7A"])
        self.assertEqual(self.names(t), ["Ann Seven", "Ben Seven"])
        self.assertEqual(sorted(r["name"] for r in self.get("/api/top-students?limit=50", t)), ["Ann Seven", "Ben Seven"])
        self.assertEqual([r["name"] for r in self.get("/api/at-risk-students", t)], ["Ann Seven"])
        self.assertEqual(self.get("/api/analytics", t)["total_students"], 2)
        self.assertEqual(self.get("/api/courses", t)[0]["students"], 2)
        self.assertEqual(self.get("/api/course-difficulty", t)[0]["students"], 2)
        self.assertEqual([c["name"] for c in self.get("/api/classes", t)], ["7A"])

    def test_their_own_statistics_only_use_their_own_students(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        _, b, _ = self.person(scope="classes", classes=["7B"])
        # 7A: GPAs are Ann 0.0 and Ben 2.0; 7B: Cy 0.0 and Dee 4.0
        self.assertEqual(self.get("/api/analytics", a)["average_gpa"], 1.0)
        self.assertEqual(self.get("/api/analytics", b)["average_gpa"], 2.0)
        self.assertEqual(self.get("/api/analytics", a)["highest_gpa"], 2.0)
        self.assertEqual(self.get("/api/analytics", b)["highest_gpa"], 4.0)

    def test_other_classes_and_unclassed_students_do_not_exist_for_them(self):
        _, t, _ = self.person(scope="classes", classes=["7A"])
        for name in ("Cy Other", "Dee Other", "Eve Nowhere"):
            self.assertEqual(self.request("GET", f"/api/students/{self.ids[name]}", t).status_code, 404, name)
        self.assertEqual(self.request("GET", f"/api/students/{self.ids['Ann Seven']}", t).status_code, 200)
        self.assertEqual(self.get("/api/students?search=cy", t), [])
        self.assertEqual(self.get("/api/students?class=7B", t), [])

    def test_everyone_else_still_sees_everything(self):
        _, all_staff, _ = self.person(scope="all")
        self.assertEqual(len(self.names(all_staff)), 5)
        self.assertEqual(len(self.names(self.admin_token)), 5)
        self.assertEqual(len(self.names(self.viewer_token)), 5)
        self.assertEqual(sorted(c["name"] for c in self.get("/api/classes", all_staff)), ["7A", "7B"])

    def test_viewers_can_be_limited_too(self):
        _, v, _ = self.person(role="viewer", scope="classes", classes=["7B"])
        self.assertEqual(self.names(v), ["Cy Other", "Dee Other"])

    def test_a_limited_person_with_no_classes_sees_nothing(self):
        _, t, _ = self.person(scope="classes", classes=[])
        self.assertEqual(self.get("/api/students", t), [])
        self.assertEqual(self.get("/api/analytics", t)["total_students"], 0)
        self.assertEqual(self.get("/api/classes", t), [])
        self.assertEqual(self.get("/api/insights", t)["insights"], [])

    def test_class_names_match_ignoring_letter_case_and_filters_work(self):
        _, t, _ = self.person(scope="classes", classes=["7a"])
        self.assertEqual(self.names(t), ["Ann Seven", "Ben Seven"])
        self.assertEqual(self.names(self.admin_token, "/api/students?class=7b"), ["Cy Other", "Dee Other"])
        self.assertEqual(self.names(self.admin_token, "/api/students?search=7b"), ["Cy Other", "Dee Other"])

    def test_who_you_are_includes_your_access(self):
        _, t, _ = self.person(scope="classes", classes=["7B", "7A"])
        user = self.get("/api/auth/me", t)["user"]
        self.assertEqual((user["scope"], user["classes"]), ("classes", ["7A", "7B"]))
        self.assertEqual(self.get("/api/auth/me")["user"]["scope"], "all")


class InsightsAndRemindersTests(ClassCase):
    def test_insights_only_describe_my_students(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        texts = {i["id"]: i for i in self.get("/api/insights", a)["insights"]}
        self.assertIn("1 of 1 at-risk student has no open follow-up", texts["unattended-at-risk"]["text"])
        names = [s["name"] for i in texts.values() for s in i.get("students", [])]
        self.assertTrue(names and set(names) <= {"Ann Seven", "Ben Seven"}, names)

    def test_reminder_team_counts_are_scoped(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        before = self.get("/api/reminders", a)["team"]
        self.request("POST", f"/api/students/{self.ids['Cy Other']}/interventions", json={"kind": "meeting", "note": "x", "assigned_to": None, "due_date": iso(-1)})
        after = self.get("/api/reminders", a)["team"]
        self.assertEqual(before, after)                       # a 7B follow-up changes nothing for 7A
        self.assertEqual(after["unattended_at_risk"], 1)      # only Ann


class FollowUpAccessTests(ClassCase):
    def make(self, token, student, **extra):
        return self.request("POST", f"/api/students/{self.ids[student]}/interventions", token,
                            json={"kind": "meeting", "note": "Talk.", **extra})

    def test_cannot_read_or_write_follow_ups_for_other_classes(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        theirs = self.make(self.admin_token, "Cy Other", assigned_to=None).get_json()
        self.assertEqual(self.make(a, "Cy Other").status_code, 404)
        self.assertEqual(self.request("GET", f"/api/students/{self.ids['Cy Other']}/interventions", a).status_code, 404)
        self.assertEqual(self.request("PATCH", f"/api/interventions/{theirs['id']}", a, json={"status": "done"}).status_code, 404)
        self.assertEqual(self.request("DELETE", f"/api/interventions/{theirs['id']}", a).status_code, 403)   # admins only anyway
        self.assertNotIn(theirs["id"], [i["id"] for i in self.get("/api/interventions?status=all", a)])
        self.assertIn(theirs["id"], [i["id"] for i in self.get("/api/interventions?status=all")])
        self.assertEqual(self.make(a, "Ann Seven").status_code, 201)     # their own class: fine

    def test_follow_ups_cannot_be_assigned_to_someone_who_cannot_see_the_student(self):
        a_name, a, _ = self.person(scope="classes", classes=["7A"])
        b_name, _, _ = self.person(scope="classes", classes=["7B"])
        all_name, _, _ = self.person(scope="all")
        res = self.make(self.admin_token, "Cy Other", assigned_to=a_name)
        self.assertEqual(res.status_code, 400)
        self.assertIn("is not assigned to this student's class", res.get_json()["message"])
        self.assertEqual(self.make(self.admin_token, "Cy Other", assigned_to=b_name).status_code, 201)
        self.assertEqual(self.make(self.admin_token, "Cy Other", assigned_to=all_name).status_code, 201)
        mine = self.make(self.admin_token, "Ann Seven", assigned_to=a_name).get_json()
        self.assertEqual(self.request("PATCH", f"/api/interventions/{mine['id']}", json={"assigned_to": b_name}).status_code, 400)

    def test_the_list_of_possible_owners_follows_the_student(self):
        a_name, a, _ = self.person(scope="classes", classes=["7A"])
        b_name, _, _ = self.person(scope="classes", classes=["7B"])
        for_cy = [p["username"] for p in self.get(f"/api/assignees?student={self.ids['Cy Other']}")]
        self.assertIn(b_name, for_cy)
        self.assertIn(ADMIN[0], for_cy)
        self.assertNotIn(a_name, for_cy)
        self.assertEqual(self.request("GET", f"/api/assignees?student={self.ids['Cy Other']}", a).status_code, 404)  # a can't see Cy

    def test_a_limited_person_gets_reminders_only_for_what_they_can_see(self):
        a_name, a, uid = self.person(scope="classes", classes=["7A"])
        item = self.make(self.admin_token, "Ann Seven", assigned_to=a_name, due_date=iso(-1)).get_json()
        self.assertEqual(self.get("/api/reminders", a)["mine"]["overdue"], 1)
        # their access is narrowed afterwards: the follow-up disappears from their view and from the email digest
        self.request("PATCH", f"/api/users/{uid}", json={"classes": ["7B"]})
        self.assertEqual(self.get("/api/reminders", a)["mine"]["overdue"], 0)
        self.assertNotIn(item["id"], [i["id"] for i in self.get("/api/interventions?status=all", a)])
        conn = sqlite3.connect(self.app.config["DATABASE"])
        conn.execute("UPDATE users SET email = 'limited@example.org' WHERE id = ?", (uid,))
        conn.commit()
        self.assertEqual([d["username"] for d in reminder_emails.collect(conn, 2)], [])
        self.request("PATCH", f"/api/users/{uid}", json={"classes": ["7A"]})
        self.assertEqual([d["username"] for d in reminder_emails.collect(conn, 2)], [a_name])
        conn.close()


class ChangingAccessTests(ClassCase):
    def test_changes_apply_immediately_without_signing_in_again(self):
        _, t, uid = self.person(scope="classes", classes=["7A"])
        self.assertEqual(self.request("GET", f"/api/students/{self.ids['Cy Other']}", t).status_code, 404)
        self.request("PATCH", f"/api/users/{uid}", json={"classes": ["7A", "7B"]})
        self.assertEqual(self.request("GET", f"/api/students/{self.ids['Cy Other']}", t).status_code, 200)
        self.request("PATCH", f"/api/users/{uid}", json={"scope": "all"})
        self.assertEqual(len(self.names(t)), 5)
        self.request("PATCH", f"/api/users/{uid}", json={"scope": "classes", "classes": ["7B"]})
        self.assertEqual(self.names(t), ["Cy Other", "Dee Other"])

    def test_moving_a_student_to_another_class_moves_who_can_see_them(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        sid = self.ids["Ben Seven"]
        self.assertEqual(self.request("PUT", f"/api/students/{sid}", json={"name": "Ben Seven", "class_name": "7B"}).status_code, 200)
        self.assertEqual(self.request("GET", f"/api/students/{sid}", a).status_code, 404)
        self.request("PUT", f"/api/students/{sid}", json={"name": "Ben Seven", "class_name": "7A"})
        self.assertEqual(self.request("GET", f"/api/students/{sid}", a).status_code, 200)
        self.request("PUT", f"/api/students/{sid}", json={"name": "Ben Seven", "class_name": ""})   # no class: hidden from limited people
        self.assertEqual(self.request("GET", f"/api/students/{sid}", a).status_code, 404)
        self.request("PUT", f"/api/students/{sid}", json={"name": "Ben Seven", "class_name": "7A"})

    def test_new_students_with_a_class_are_visible_to_that_class(self):
        _, a, _ = self.person(scope="classes", classes=["7A"])
        sid = self.request("POST", "/api/students", json={"name": "New Nia", "class_name": " 7a "}).get_json()["id"]
        self.request("POST", f"/api/students/{sid}/records", json={"course": "Math", "semester": "2025-1", "score": 70})
        self.assertIn("New Nia", self.names(a))

    def test_admins_cannot_be_limited_and_bad_settings_are_refused(self):
        _, _, uid = self.person(scope="classes", classes=["7A"])
        promoted = self.request("PATCH", f"/api/users/{uid}", json={"role": "admin"}).get_json()
        self.assertEqual((promoted["scope"], promoted["classes"]), ("all", []))
        for bad in ({"scope": "everything"}, {"classes": "7A"}, {"classes": [5]}, {"classes": ["x" * 41]}):
            self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json=bad).status_code, 400, bad)

    def test_the_users_list_and_creation_include_access(self):
        res = self.request("POST", "/api/users", json={"username": "madeclass", "password": "long-enough-pw-1", "role": "staff",
                                                       "scope": "classes", "classes": ["7B", "7b", "7A"]})
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.get_json()["scope"], res.get_json()["classes"]), ("classes", ["7A", "7B"]))   # duplicates ignoring case dropped
        listed = next(u for u in self.get("/api/users") if u["username"] == "madeclass")
        self.assertEqual((listed["scope"], listed["classes"]), ("classes", ["7A", "7B"]))
        admin_row = next(u for u in self.get("/api/users") if u["username"] == ADMIN[0])
        self.assertEqual((admin_row["scope"], admin_row["classes"]), ("all", []))
        self.assertTrue(any("scope" in (e["detail"] or "") for e in self.get("/api/audit?limit=10")))

    def test_limited_staff_cannot_use_admin_endpoints(self):
        _, t, _ = self.person(scope="classes", classes=["7A"])
        for method, url in (("POST", "/api/students"), ("GET", "/api/users"), ("POST", "/api/import"), ("GET", "/api/audit")):
            self.assertEqual(self.request(method, url, t, json={}).status_code, 403, url)


class ImportClassTests(ClassCase):
    def imp(self, text, **extra):
        res = self.request("POST", "/api/import", json={"csv": text, **extra})
        return res.status_code, res.get_json()

    def test_the_class_column_sets_and_changes_classes(self):
        code, body = self.imp("Student,Student ID,Section,Course,Semester,Score\nImp Ida,I-1,8A,Math,2025-1,70\n")
        self.assertEqual((code, body["students_created"], body["classes_set"]), (200, 1, 0))
        sid = self.get("/api/students?search=imp%20ida")[0]["student_id"]
        self.assertEqual(self.get(f"/api/students/{sid}")["class_name"], "8A")
        code, preview = self.imp("Student,Student ID,Class,Course,Semester,Score\nImp Ida,I-1,8B,English,2025-1,70\n", dry_run=True)
        self.assertEqual(preview["classes_set"], 1)
        self.assertEqual(self.get(f"/api/students/{sid}")["class_name"], "8A")           # the preview changed nothing
        self.imp("Student,Student ID,Class,Course,Semester,Score\nImp Ida,I-1,8B,English,2025-1,70\n")
        self.assertEqual(self.get(f"/api/students/{sid}")["class_name"], "8B")

    def test_a_row_without_a_class_leaves_the_class_alone(self):
        self.imp("Student,Student ID,Class,Course,Semester,Score\nKeep Kim,K-1,9A,Math,2025-1,70\n")
        code, body = self.imp("Student,Student ID,Course,Semester,Score\nKeep Kim,K-1,English,2025-1,70\n")
        self.assertEqual((code, body["classes_set"]), (200, 0))
        self.assertEqual(self.get("/api/students?search=keep%20kim")[0]["class_name"], "9A")

    def test_two_classes_for_one_student_in_one_file_is_an_error(self):
        code, body = self.imp("Student,Student ID,Class,Course,Semester,Score\nTwo Tia,T-1,9A,Math,2025-1,70\nTwo Tia,T-1,9B,English,2025-1,70\n")
        self.assertEqual(code, 400)
        self.assertIn("appears in two different classes", body["errors"][0]["message"])


class MigrationTests(unittest.TestCase):
    def test_existing_people_keep_seeing_everything_after_the_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
                CREATE TABLE students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, student_code TEXT);
                CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'viewer')),
                    active INTEGER NOT NULL DEFAULT 1, token_version INTEGER NOT NULL DEFAULT 0, email TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')));
                INSERT INTO students (name) VALUES ('Old One'), ('Old Two');
            """)
            from werkzeug.security import generate_password_hash
            old.execute("INSERT INTO users (username, password_hash, role) VALUES ('teacher', ?, 'staff')", (generate_password_hash("teacher-password-1"),))
            old.commit()
            old.close()
            app = create_app({"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False, "ADMIN_PASSWORD": "old-admin-password-1"})
            conn = sqlite3.connect(path)
            self.assertIn("class_name", [r[1] for r in conn.execute("PRAGMA table_info(students)")])
            self.assertIn("scope", [r[1] for r in conn.execute("PRAGMA table_info(users)")])
            self.assertEqual(conn.execute("SELECT scope FROM users WHERE username = 'teacher'").fetchone()[0], "all")
            conn.close()
            client = app.test_client()
            token = client.post("/api/auth/login", json={"username": "teacher", "password": "teacher-password-1"}).get_json()["token"]
            me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).get_json()["user"]
            self.assertEqual((me["scope"], me["classes"]), ("all", []))


class DemoDataTests(ApiTestCase):
    config = {"DEMO_STAFF_USERNAME": "teacher", "DEMO_STAFF_PASSWORD": "teacher-demo-pw-1"}

    def test_the_demo_has_four_classes_of_ten(self):
        classes = self.get("/api/classes")
        self.assertEqual([(c["name"], c["students"]) for c in classes],
                         [("JSS 1A", 10), ("JSS 1B", 10), ("JSS 2A", 10), ("JSS 2B", 10)])

    def test_the_demo_teacher_sees_only_the_first_class(self):
        token = self.login("teacher", "teacher-demo-pw-1")
        me = self.get("/api/auth/me", token)["user"]
        self.assertEqual((me["role"], me["scope"], me["classes"]), ("staff", "classes", ["JSS 1A"]))
        rows = self.get("/api/students", token)
        self.assertEqual(len({r["student_id"] for r in rows}), 10)
        self.assertEqual({r["class_name"] for r in rows}, {"JSS 1A"})
        self.assertEqual(self.get("/api/analytics", token)["total_students"], 10)
        self.assertEqual(self.get("/api/analytics")["total_students"], 40)


if __name__ == "__main__":
    unittest.main()
