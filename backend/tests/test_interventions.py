import datetime
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from base import ADMIN, ApiTestCase  # noqa: E402

STAFF = ("staff1", "staff-password-1")


def day(offset):
    return (datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=offset)).isoformat()


class InterventionCase(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.create_user(*STAFF, role="staff")
        cls.staff_token = cls.login(*STAFF)
        # Two low scorers (at risk) and one good student
        res = cls.client.post("/api/import", headers=cls.auth(cls.admin_token), json={"csv":
            "Student,Course,Semester,Score\nLow Lola,Math,2025-1,40\nLow Lee,Math,2025-1,30\nGood Gabe,Math,2025-1,95\n"})
        assert res.status_code == 200
        students = cls.client.get("/api/students", headers=cls.auth(cls.admin_token)).get_json()
        cls.ids = {r["name"]: r["student_id"] for r in students}

    def add(self, name, token=None, **body):
        body = {"kind": "meeting", "note": "Talked it over.", **body}
        return self.request("POST", f"/api/students/{self.ids[name]}/interventions", token, json=body)

    def worklist(self, query="", token=None):
        return self.get("/api/interventions" + query, token)


class PermissionTests(InterventionCase):
    def test_roles(self):
        sid = self.ids["Low Lola"]
        url = f"/api/students/{sid}/interventions"
        body = {"kind": "tutoring", "note": "Peer tutoring arranged."}

        # viewers read, but cannot change anything
        self.assertEqual(self.request("GET", url, self.viewer_token).status_code, 200)
        self.assertEqual(self.request("GET", "/api/interventions", self.viewer_token).status_code, 200)
        self.assertEqual(self.request("POST", url, self.viewer_token, json=body).status_code, 403)

        # staff create and update, but cannot delete
        made = self.request("POST", url, self.staff_token, json=body)
        self.assertEqual(made.status_code, 201)
        iid = made.get_json()["id"]
        self.assertEqual(made.get_json()["created_by"], STAFF[0])
        self.assertEqual(self.request("PATCH", f"/api/interventions/{iid}", self.viewer_token, json={"status": "done"}).status_code, 403)
        self.assertEqual(self.request("PATCH", f"/api/interventions/{iid}", self.staff_token, json={"status": "done"}).status_code, 200)
        self.assertEqual(self.request("DELETE", f"/api/interventions/{iid}", self.staff_token).status_code, 403)

        # admin can delete
        self.assertEqual(self.request("DELETE", f"/api/interventions/{iid}").status_code, 204)
        self.assertEqual(self.request("DELETE", f"/api/interventions/{iid}").status_code, 404)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.get("/api/interventions").status_code, 401)
        self.assertEqual(self.client.post(f"/api/students/{self.ids['Low Lola']}/interventions", json={}).status_code, 401)

    def test_staff_cannot_use_admin_endpoints(self):
        self.assertEqual(self.request("GET", "/api/users", self.staff_token).status_code, 403)
        self.assertEqual(self.request("POST", "/api/students", self.staff_token, json={"name": "X"}).status_code, 403)
        self.assertEqual(self.request("POST", "/api/import", self.staff_token, json={"csv": "a"}).status_code, 403)


class ValidationTests(InterventionCase):
    def test_bad_input_is_rejected(self):
        bad = [
            {"kind": "party"}, {"kind": None}, {"note": ""}, {"note": "   "}, {"note": 5},
            {"note": "x" * 1001}, {"note": "bad\x00char"},
            {"due_date": "tomorrow"}, {"due_date": "2025-13-40"}, {"due_date": "20251001"}, {"due_date": 5},
        ]
        for patch in bad:
            res = self.add("Low Lola", **patch)
            self.assertEqual(res.status_code, 400, patch)
            self.assertEqual(res.get_json()["error"], "validation_error")
        self.assertEqual(self.request("POST", f"/api/students/{self.ids['Low Lola']}/interventions",
                                      data="nope", content_type="application/json").status_code, 400)

    def test_unknown_student(self):
        self.assertEqual(self.request("POST", "/api/students/999999/interventions",
                                      json={"kind": "meeting", "note": "x"}).status_code, 404)
        self.assertEqual(self.request("GET", "/api/students/999999/interventions").status_code, 404)
        self.assertEqual(self.request("PATCH", "/api/interventions/999999", json={"note": "x"}).status_code, 404)

    def test_note_keeps_line_breaks_and_limits_are_inclusive(self):
        note = "Line one\r\nLine two\tindented"
        made = self.add("Good Gabe", note=note).get_json()
        self.assertEqual(made["note"], "Line one\nLine two\tindented")
        self.assertEqual(self.add("Good Gabe", note="y" * 1000).status_code, 201)
        self.assertEqual(self.add("Good Gabe", due_date="").get_json()["due_date"], None)


class LifecycleTests(InterventionCase):
    def test_complete_reopen_edit_and_clear_due_date(self):
        made = self.add("Low Lee", due_date=day(5), note="Original").get_json()
        iid = made["id"]
        self.assertEqual((made["status"], made["completed_at"], made["overdue"]), ("open", None, False))
        self.assertEqual(made["student_name"], "Low Lee")

        done = self.request("PATCH", f"/api/interventions/{iid}", json={"status": "done"}).get_json()
        self.assertEqual(done["status"], "done")
        self.assertIsNotNone(done["completed_at"])
        self.assertNotIn(iid, [i["id"] for i in self.worklist()])
        self.assertIn(iid, [i["id"] for i in self.worklist("?status=done")])

        again = self.request("PATCH", f"/api/interventions/{iid}", json={"status": "open"}).get_json()
        self.assertEqual((again["status"], again["completed_at"]), ("open", None))

        edited = self.request("PATCH", f"/api/interventions/{iid}",
                              json={"note": "Edited", "kind": "tutoring", "due_date": None}).get_json()
        self.assertEqual((edited["note"], edited["kind"], edited["due_date"]), ("Edited", "tutoring", None))
        self.assertEqual(self.request("PATCH", f"/api/interventions/{iid}", json={"status": "later"}).status_code, 400)

    def test_overdue_flag_and_filter(self):
        late = self.add("Low Lola", due_date=day(-3), note="late one").get_json()
        future = self.add("Low Lola", due_date=day(10), note="future one").get_json()
        self.assertTrue(late["overdue"])
        self.assertFalse(future["overdue"])
        overdue_ids = [i["id"] for i in self.worklist("?overdue=1")]
        self.assertIn(late["id"], overdue_ids)
        self.assertNotIn(future["id"], overdue_ids)
        # finishing an overdue item clears the flag
        done = self.request("PATCH", f"/api/interventions/{late['id']}", json={"status": "done"}).get_json()
        self.assertFalse(done["overdue"])

    def test_worklist_order_and_status_filters(self):
        a = self.add("Good Gabe", due_date=day(30), note="order-late").get_json()["id"]
        b = self.add("Good Gabe", due_date=day(1), note="order-soon").get_json()["id"]
        c = self.add("Good Gabe", note="order-nodate").get_json()["id"]
        order = [i["id"] for i in self.worklist() if i["id"] in (a, b, c)]
        self.assertEqual(order, [b, a, c])  # soonest first, undated last
        self.assertEqual(self.request("GET", "/api/interventions?status=bogus").status_code, 400)
        self.assertEqual(self.request("GET", "/api/interventions?limit=abc").status_code, 400)
        self.assertTrue(all(i["status"] == "open" for i in self.worklist("?status=open")))
        statuses = {i["status"] for i in self.worklist("?status=all")}
        self.assertEqual(statuses, {"open", "done"})

    def test_student_list_shows_open_first(self):
        sid = self.ids["Low Lee"]
        first = self.add("Low Lee", note="s1").get_json()["id"]
        self.request("PATCH", f"/api/interventions/{first}", json={"status": "done"})
        second = self.add("Low Lee", note="s2").get_json()["id"]
        items = self.get(f"/api/students/{sid}/interventions")
        statuses = [i["status"] for i in items]
        self.assertEqual(statuses, sorted(statuses, key=lambda s: s != "open"))
        self.assertEqual(items[0]["id"], second)

    def test_audit_log_records_actions_but_not_note_text(self):
        secret = "very-private-note-text"
        made = self.add("Low Lola", note=secret).get_json()
        self.request("PATCH", f"/api/interventions/{made['id']}", json={"note": secret + " edited"})
        entries = self.get("/api/audit?limit=50")
        actions = [e["action"] for e in entries if f"id={made['id']}" in (e["detail"] or "")]
        self.assertIn("intervention.create", actions)
        self.assertIn("intervention.update", actions)
        self.assertNotIn(secret, str(entries))


class StudentAndInsightTests(InterventionCase):
    def test_at_risk_endpoint_counts_open_followups(self):
        def row(name):
            return next(r for r in self.get("/api/at-risk-students") if r["id"] == self.ids[name])

        self.assertEqual(row("Low Lee")["open_interventions"], 0)
        self.assertIsNone(row("Low Lee")["last_intervention"])
        item = self.add("Low Lee").get_json()
        self.assertEqual(row("Low Lee")["open_interventions"], 1)
        self.assertIsNotNone(row("Low Lee")["last_intervention"])
        self.request("PATCH", f"/api/interventions/{item['id']}", json={"status": "done"})
        after = row("Low Lee")
        self.assertEqual(after["open_interventions"], 0)
        self.assertIsNotNone(after["last_intervention"])  # history is kept

    def test_unattended_insight_changes_as_followups_are_added(self):
        def insight():
            return next(i for i in self.get("/api/insights")["insights"] if i["id"] == "unattended-at-risk")

        before = insight()
        self.assertEqual(before["tone"], "warning")
        names = [s["name"] for s in before["students"]]
        self.assertIn("Low Lola", names)
        self.assertIn("Low Lee", names)
        self.assertNotIn("Good Gabe", names)  # not at risk

        for name in ("Low Lola", "Low Lee"):
            self.add(name)
        after = insight()
        self.assertEqual(after["tone"], "positive")
        self.assertIn("All 2 at-risk students have an open follow-up", after["text"])

    def test_deleting_a_student_removes_their_followups(self):
        sid = self.request("POST", "/api/students", json={"name": "Doomed Dee"}).get_json()["id"]
        made = self.request("POST", f"/api/students/{sid}/interventions", json={"kind": "other", "note": "bye"}).get_json()
        self.assertIn(made["id"], [i["id"] for i in self.worklist()])
        self.assertEqual(self.request("DELETE", f"/api/students/{sid}").status_code, 204)
        self.assertNotIn(made["id"], [i["id"] for i in self.worklist()])


class StaffRoleTests(ApiTestCase):
    def test_admin_can_create_and_promote_staff(self):
        res = self.request("POST", "/api/users", json={"username": "newstaff", "password": "long-enough-pw", "role": "staff"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["role"], "staff")
        uid = res.get_json()["id"]
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"role": "viewer"}).status_code, 200)
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"role": "staff"}).status_code, 200)
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"role": "teacher"}).status_code, 400)


class MigrationTests(unittest.TestCase):
    def test_old_database_gets_the_staff_role_without_losing_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'viewer')),
                    active INTEGER NOT NULL DEFAULT 1,
                    token_version INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)
            old.execute("INSERT INTO users (id, username, password_hash, role, token_version) VALUES "
                        "(7, 'oldadmin', ?, 'admin', 3), (9, 'oldviewer', ?, 'viewer', 0)",
                        (generate_password_hash("old-admin-password-1"), generate_password_hash("old-viewer-pw-1")))
            old.commit()
            old.close()

            app = create_app({"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False})
            client = app.test_client()
            login = client.post("/api/auth/login", json={"username": "oldadmin", "password": "old-admin-password-1"})
            self.assertEqual(login.status_code, 200)
            self.assertEqual(login.get_json()["user"]["id"], 7)
            headers = {"Authorization": f"Bearer {login.get_json()['token']}"}

            users = client.get("/api/users", headers=headers).get_json()
            self.assertEqual({u["username"] for u in users}, {"oldadmin", "oldviewer"})

            made = client.post("/api/users", headers=headers,
                               json={"username": "newstaff", "password": "long-enough-pw", "role": "staff"})
            self.assertEqual(made.status_code, 201)
            self.assertGreater(made.get_json()["id"], 9)  # ids keep counting up

            # running init again is a no-op
            create_app({"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False})
            self.assertEqual(len(client.get("/api/users", headers=headers).get_json()), 3)


class DemoDataTests(ApiTestCase):
    def test_demo_database_has_a_mix_of_attended_and_unattended_at_risk_students(self):
        at_risk = self.get("/api/at-risk-students")
        counts = [r["open_interventions"] for r in at_risk]
        self.assertTrue(any(c > 0 for c in counts), counts)
        self.assertTrue(any(c == 0 for c in counts), counts)
        done = self.get("/api/interventions?status=done")
        self.assertTrue(done)
        self.assertTrue(any(i["overdue"] for i in self.get("/api/interventions")))


if __name__ == "__main__":
    unittest.main()
