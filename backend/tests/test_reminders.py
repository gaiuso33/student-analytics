import datetime
import os
import smtplib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reminder_emails  # noqa: E402
from app import create_app  # noqa: E402
from base import ADMIN, ApiTestCase  # noqa: E402

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def iso(offset=0):
    return (datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=offset)).isoformat()


class ReminderCase(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        res = cls.client.post("/api/import", headers=cls.auth(cls.admin_token), json={"csv":
            "Student,Course,Semester,Score\nRem Ann,Math,2025-1,30\nRem Ben,Math,2025-1,35\nRem Cy,Math,2025-1,95\n"})
        assert res.status_code == 200
        rows = cls.client.get("/api/students", headers=cls.auth(cls.admin_token)).get_json()
        cls.ids = {r["name"]: r["student_id"] for r in rows}
        cls._n = 0

    @classmethod
    def new_staff(cls, role="staff"):
        cls._n += 1
        name, password = f"person{cls._n}", f"person-password-{cls._n}"
        cls.create_user(name, password, role=role)
        return name, cls.login(name, password)

    def add(self, token, student="Rem Ann", **body):
        body = {"kind": "meeting", "note": "Talked.", **body}
        res = self.request("POST", f"/api/students/{self.ids[student]}/interventions", token, json=body)
        self.assertEqual(res.status_code, 201, res.get_data(as_text=True))
        return res.get_json()


class AssignmentTests(ReminderCase):
    def test_default_is_the_person_recording_it_and_null_means_nobody(self):
        a, ta = self.new_staff()
        b, _ = self.new_staff()
        self.assertEqual(self.add(ta)["assigned_to"], a)
        self.assertEqual(self.add(ta, assigned_to=b)["assigned_to"], b)
        self.assertIsNone(self.add(ta, assigned_to=None)["assigned_to"])
        self.assertIsNone(self.add(ta, assigned_to="")["assigned_to"])
        self.assertEqual(self.add(ta, assigned_to=ADMIN[0])["assigned_to"], ADMIN[0])  # admins can own follow-ups

    def test_assignee_names_are_matched_without_regard_to_case(self):
        a, ta = self.new_staff()
        self.assertEqual(self.add(ta, assigned_to=a.upper())["assigned_to"], a)

    def test_only_active_staff_or_admins_can_be_assigned(self):
        _, ta = self.new_staff()
        inactive, _ = self.new_staff()
        uid = next(u["id"] for u in self.get("/api/users") if u["username"] == inactive)
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"active": False}).status_code, 200)
        for bad in ("viewer1", "nobody-here", inactive, 5, ["x"]):
            res = self.request("POST", f"/api/students/{self.ids['Rem Ann']}/interventions", ta,
                               json={"kind": "meeting", "note": "x", "assigned_to": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertEqual(res.get_json()["field"], "assigned_to")

    def test_reassign_and_unassign(self):
        a, ta = self.new_staff()
        b, tb = self.new_staff()
        made = self.add(ta)
        moved = self.request("PATCH", f"/api/interventions/{made['id']}", tb, json={"assigned_to": b}).get_json()
        self.assertEqual(moved["assigned_to"], b)
        cleared = self.request("PATCH", f"/api/interventions/{made['id']}", ta, json={"assigned_to": None}).get_json()
        self.assertIsNone(cleared["assigned_to"])
        self.assertEqual(self.request("PATCH", f"/api/interventions/{made['id']}", ta, json={"assigned_to": "viewer1"}).status_code, 400)
        # other edits leave the owner alone
        self.request("PATCH", f"/api/interventions/{made['id']}", ta, json={"assigned_to": a})
        kept = self.request("PATCH", f"/api/interventions/{made['id']}", tb, json={"note": "Edited"}).get_json()
        self.assertEqual(kept["assigned_to"], a)

    def test_assignee_shows_in_the_audit_log_without_the_note(self):
        _, ta = self.new_staff()
        made = self.add(ta, note="private-note-text")
        entries = self.get("/api/audit?limit=30")
        mine = [e for e in entries if f"id={made['id']} " in (e["detail"] or "") and e["action"] == "intervention.create"]
        self.assertIn("assigned=", mine[0]["detail"])
        self.assertNotIn("private-note-text", str(entries))

    def test_assignees_endpoint(self):
        a, ta = self.new_staff()
        names = [p["username"] for p in self.get("/api/assignees", ta)]
        self.assertIn(a, names)
        self.assertIn(ADMIN[0], names)
        self.assertNotIn("viewer1", names)
        self.assertEqual(self.request("GET", "/api/assignees", self.viewer_token).status_code, 403)


class DueFlagTests(ReminderCase):
    def test_flags_and_days(self):
        _, t = self.new_staff()
        cases = {-3: (True, False, -3), 0: (False, True, 0), 2: (False, True, 2), 3: (False, False, 3), 30: (False, False, 30)}
        for offset, (overdue, soon, days) in cases.items():
            item = self.add(t, due_date=iso(offset))
            self.assertEqual((item["overdue"], item["due_soon"], item["due_in_days"]), (overdue, soon, days), offset)
        undated = self.add(t)
        self.assertEqual((undated["overdue"], undated["due_soon"], undated["due_in_days"]), (False, False, None))

    def test_finished_items_are_never_flagged(self):
        _, t = self.new_staff()
        item = self.add(t, due_date=iso(-2))
        done = self.request("PATCH", f"/api/interventions/{item['id']}", t, json={"status": "done"}).get_json()
        self.assertEqual((done["overdue"], done["due_soon"]), (False, False))


class WindowConfigTests(ReminderCase):
    config = {"SEED_IF_EMPTY": False, "REMINDER_DAYS_AHEAD": 5}

    def test_window_follows_the_setting(self):
        _, t = self.new_staff()
        self.assertTrue(self.add(t, due_date=iso(5))["due_soon"])
        self.assertFalse(self.add(t, due_date=iso(6))["due_soon"])
        self.assertEqual(self.get("/api/reminders", t)["days_ahead"], 5)


class WorklistFilterTests(ReminderCase):
    def test_assigned_and_attention_filters(self):
        a, ta = self.new_staff()
        b, tb = self.new_staff()
        mine_late = self.add(ta, due_date=iso(-1))["id"]
        mine_far = self.add(ta, due_date=iso(20))["id"]
        theirs_soon = self.add(ta, assigned_to=b, due_date=iso(1))["id"]
        nobody = self.add(ta, assigned_to=None, due_date=iso(-5))["id"]
        done = self.add(ta, due_date=iso(-9))["id"]
        self.request("PATCH", f"/api/interventions/{done}", ta, json={"status": "done"})

        ids = lambda q, token=ta: [i["id"] for i in self.get("/api/interventions" + q, token)]  # noqa: E731
        self.assertEqual(set(ids("?assigned=me")) & {mine_late, mine_far, theirs_soon, nobody, done}, {mine_late, mine_far})
        self.assertEqual(set(ids("?assigned=me", tb)) & {mine_late, theirs_soon}, {theirs_soon})
        self.assertIn(nobody, ids("?assigned=unassigned"))
        self.assertNotIn(mine_late, ids("?assigned=unassigned"))
        self.assertEqual(set(ids(f"?assigned={a.upper()}")) & {mine_late, mine_far, theirs_soon}, {mine_late, mine_far})

        attention = set(ids("?attention=1"))
        self.assertTrue({mine_late, theirs_soon, nobody} <= attention)
        self.assertNotIn(mine_far, attention)
        self.assertNotIn(done, attention)
        mine_attention = set(ids("?attention=1&assigned=me")) & {mine_late, mine_far, theirs_soon, nobody}
        self.assertEqual(mine_attention, {mine_late})


class SummaryTests(ReminderCase):
    def test_counts_for_the_signed_in_person(self):
        _, t = self.new_staff()
        far = self.add(t, due_date=iso(10))
        self.add(t, due_date=iso(-3))
        self.add(t, due_date=iso(0))
        self.add(t, due_date=iso(2))
        self.add(t)  # no date
        finished = self.add(t, due_date=iso(-8))
        self.request("PATCH", f"/api/interventions/{finished['id']}", t, json={"status": "done"})

        summary = self.get("/api/reminders", t)
        mine = summary["mine"]
        self.assertEqual((mine["overdue"], mine["due_soon"], mine["open"]), (1, 2, 5))
        self.assertEqual([i["due_in_days"] for i in mine["items"]], [-3, 0, 2])  # soonest first, attention items only
        self.assertNotIn(far["id"], [i["id"] for i in mine["items"]])
        self.assertGreaterEqual(summary["team"]["open"], 5)
        self.assertGreaterEqual(summary["team"]["overdue"], 1)

    def test_students_without_a_follow_up_are_counted(self):
        _, t = self.new_staff()
        at_risk = self.get("/api/at-risk-students", t)
        expected = len([r for r in at_risk if r["open_interventions"] == 0])
        self.assertEqual(self.get("/api/reminders", t)["team"]["unattended_at_risk"], expected)

    def test_viewers_can_read_it_but_have_nothing_assigned(self):
        summary = self.get("/api/reminders", self.viewer_token)
        self.assertEqual((summary["mine"]["overdue"], summary["mine"]["due_soon"], summary["mine"]["open"]), (0, 0, 0))
        self.assertEqual(summary["mine"]["items"], [])
        self.assertEqual(self.client.get("/api/reminders").status_code, 401)


class EmailAddressTests(ReminderCase):
    def test_set_change_and_clear_your_own_address(self):
        _, t = self.new_staff()
        res = self.request("PATCH", "/api/auth/me", t, json={"email": "  Mixed.Case@School.ORG "})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["user"]["email"], "mixed.case@school.org")
        self.assertEqual(self.get("/api/auth/me", t)["user"]["email"], "mixed.case@school.org")
        self.assertIsNone(self.request("PATCH", "/api/auth/me", t, json={"email": ""}).get_json()["user"]["email"])
        self.request("PATCH", "/api/auth/me", t, json={"email": "a@b.co"})
        self.assertIsNone(self.request("PATCH", "/api/auth/me", t, json={"email": None}).get_json()["user"]["email"])
        self.assertTrue(any(e["action"] == "profile.update" for e in self.get("/api/audit?limit=20")))

    def test_bad_addresses_are_refused(self):
        _, t = self.new_staff()
        for bad in ("not-an-email", "a@b", "two@@signs.com", "has space@x.com", "x" * 250 + "@x.com", 5, ["a@b.co"]):
            res = self.request("PATCH", "/api/auth/me", t, json={"email": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertEqual(res.get_json()["field"], "email")
        self.assertEqual(self.request("PATCH", "/api/auth/me", t, json={}).status_code, 400)

    def test_an_administrator_can_set_addresses_without_signing_people_out(self):
        res = self.request("POST", "/api/users", json={"username": "withmail", "password": "long-enough-pw-1", "role": "staff", "email": "With@Mail.org"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["email"], "with@mail.org")
        uid = res.get_json()["id"]
        token = self.login("withmail", "long-enough-pw-1")
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"email": "new@mail.org"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(token)).status_code, 200)  # still signed in
        self.assertEqual(next(u for u in self.get("/api/users") if u["id"] == uid)["email"], "new@mail.org")
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"email": "bad"}).status_code, 400)
        self.assertEqual(self.request("POST", "/api/users", json={"username": "bademail", "password": "long-enough-pw-1", "email": "nope"}).status_code, 400)


CONFIG = SimpleNamespace(
    REMINDER_DAYS_AHEAD=2, SMTP_HOST="smtp.test", SMTP_PORT=587, SMTP_USER="mailer", SMTP_PASSWORD="secret",
    SMTP_SECURITY="starttls", MAIL_FROM="noreply@school.test", SITE_URL="https://dash.test", REMINDER_INCLUDE_NAMES=False,
)


class DigestTests(ReminderCase):
    NOTE = "very-private-counselling-note"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db_path = cls.app.config["DATABASE"]

        def person(name, role, email=None):
            cls.create_user(name, f"{name}-password-1", role=role)
            if email:
                token = cls.login(name, f"{name}-password-1")
                cls.client.patch("/api/auth/me", json={"email": email}, headers=cls.auth(token))

        person("mailstaff", "staff", "mailstaff@example.org")
        person("mailsecond", "staff", "second@example.org")
        person("mailviewer", "viewer", "viewer@example.org")
        person("mailinactive", "staff", "inactive@example.org")
        person("nomail", "staff")
        token = cls.login("mailstaff", "mailstaff-password-1")

        def add(assigned, offset, student="Rem Ann"):
            r = cls.client.post(f"/api/students/{cls.ids[student]}/interventions", headers=cls.auth(token),
                                json={"kind": "tutoring", "note": cls.NOTE, "due_date": iso(offset), "assigned_to": assigned})
            assert r.status_code == 201, r.get_data(as_text=True)

        add("mailstaff", -2)             # overdue
        add("mailstaff", 1, "Rem Ben")   # due soon
        add("mailstaff", 30)             # far away: not included
        add("mailsecond", 0)
        add("nomail", -1)                # no address: skipped
        add("mailinactive", -1)          # deactivated below: skipped
        for u in cls.client.get("/api/users", headers=cls.auth(cls.admin_token)).get_json():
            if u["username"] == "mailinactive":
                cls.client.patch(f"/api/users/{u['id']}", json={"active": False}, headers=cls.auth(cls.admin_token))

    def conn(self):
        return sqlite3.connect(self.db_path)

    def test_only_the_right_people_get_a_digest(self):
        digests = reminder_emails.collect(self.conn(), 2)
        self.assertEqual([d["username"] for d in digests], ["mailsecond", "mailstaff"])
        staff = next(d for d in digests if d["username"] == "mailstaff")
        self.assertEqual((len(staff["overdue"]), len(staff["due_soon"])), (1, 1))
        self.assertEqual(staff["email"], "mailstaff@example.org")

    def test_email_content_hides_names_and_never_shows_notes(self):
        digest = next(d for d in reminder_emails.collect(self.conn(), 2) if d["username"] == "mailstaff")
        message = reminder_emails.compose(digest, CONFIG, 2)
        body = message.get_content()
        self.assertEqual(message["Subject"], "Student follow-ups: 1 overdue, 1 due soon")
        self.assertEqual((message["To"], message["From"]), ("mailstaff@example.org", "noreply@school.test"))
        self.assertIn("1 overdue", body)
        self.assertIn("https://dash.test/interventions", body)
        self.assertIn("stop these emails", body)
        for secret in ("Rem Ann", "Rem Ben", self.NOTE):
            self.assertNotIn(secret, body)

        with_names = reminder_emails.compose(digest, SimpleNamespace(**{**vars(CONFIG), "REMINDER_INCLUDE_NAMES": True}), 2).get_content()
        self.assertIn("Rem Ann: Tutoring, due", with_names)
        self.assertIn("Rem Ben", with_names)
        self.assertNotIn(self.NOTE, with_names)

    def test_dry_run_prints_and_sends_nothing(self):
        printed = []
        with mock.patch("reminder_emails.smtplib.SMTP") as smtp:
            result = reminder_emails.run(CONFIG, self.conn(), dry_run=True, out=printed.append)
        smtp.assert_not_called()
        self.assertEqual(result, {"recipients": 2, "sent": 0, "failed": 0})
        self.assertIn("To: mailstaff@example.org", "\n".join(printed))

    def test_sending_uses_starttls_login_and_one_message_per_person(self):
        with mock.patch("reminder_emails.smtplib.SMTP") as smtp:
            conn = self.conn()
            result = reminder_emails.run(CONFIG, conn, out=lambda *_: None)
            server = smtp.return_value
            smtp.assert_called_once_with("smtp.test", 587, timeout=20)
            server.starttls.assert_called_once()
            server.login.assert_called_once_with("mailer", "secret")
            self.assertEqual([c.args[0]["To"] for c in server.send_message.call_args_list],
                             ["second@example.org", "mailstaff@example.org"])
            server.quit.assert_called_once()
        self.assertEqual(result, {"recipients": 2, "sent": 2, "failed": 0})
        logged = conn.execute("SELECT detail FROM audit_log WHERE action = 'reminders.sent' ORDER BY id DESC").fetchone()
        self.assertEqual(logged[0], "sent=2 failed=0")

    def test_one_failure_does_not_stop_the_others(self):
        with mock.patch("reminder_emails.smtplib.SMTP") as smtp:
            smtp.return_value.send_message.side_effect = [smtplib.SMTPRecipientsRefused({}), None]
            result = reminder_emails.run(CONFIG, self.conn(), out=lambda *_: None)
        self.assertEqual((result["sent"], result["failed"]), (1, 1))

    def test_ssl_mode_and_no_login(self):
        config = SimpleNamespace(**{**vars(CONFIG), "SMTP_SECURITY": "ssl", "SMTP_USER": None, "SMTP_PORT": 465})
        with mock.patch("reminder_emails.smtplib.SMTP_SSL") as ssl, mock.patch("reminder_emails.smtplib.SMTP") as plain:
            reminder_emails.run(config, self.conn(), out=lambda *_: None)
        ssl.assert_called_once_with("smtp.test", 465, timeout=20)
        plain.assert_not_called()
        ssl.return_value.login.assert_not_called()

    def test_setup_problems_give_clear_errors(self):
        with self.assertRaises(reminder_emails.ReminderError) as ctx:
            reminder_emails.run(SimpleNamespace(**{**vars(CONFIG), "SMTP_HOST": None}), self.conn(), out=lambda *_: None)
        self.assertIn("SMTP_HOST", str(ctx.exception))
        with mock.patch("reminder_emails.smtplib.SMTP", side_effect=OSError("connection refused")):
            with self.assertRaises(reminder_emails.ReminderError) as ctx:
                reminder_emails.run(CONFIG, self.conn(), out=lambda *_: None)
        self.assertIn("Could not connect to the mail server", str(ctx.exception))

    def test_nothing_due_means_nothing_sent(self):
        printed = []
        result = reminder_emails.run(CONFIG, self.conn(), days=-100, out=printed.append)
        self.assertEqual(result["recipients"], 0)
        self.assertEqual(printed, ["No reminders to send."])

    def test_the_command_line_wires_it_together(self):
        env = {**os.environ, "DATABASE": self.db_path, "SMTP_HOST": ""}
        run = lambda *args: subprocess.run([sys.executable, "manage.py", "send-reminders", *args],  # noqa: E731
                                          cwd=BACKEND, env=env, capture_output=True, text=True)
        dry = run("--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("Subject: Student follow-ups: 1 overdue, 1 due soon", dry.stdout)
        unsent = run()
        self.assertNotEqual(unsent.returncode, 0)
        self.assertIn("SMTP_HOST is not set", unsent.stderr)


class MigrationTests(unittest.TestCase):
    def test_old_database_gains_the_new_columns_and_keeps_its_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
                CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'viewer')),
                    active INTEGER NOT NULL DEFAULT 1, token_version INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')));
                CREATE TABLE students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
                CREATE TABLE interventions (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', due_date TEXT,
                    created_by TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')), completed_at TEXT);
                INSERT INTO students (name) VALUES ('Old Student');
                INSERT INTO interventions (student_id, kind, note, created_by) VALUES (1, 'meeting', 'old note', 'oldstaff');
            """)
            old.commit()
            old.close()

            cfg = {"DATABASE": path, "SECRET_KEY": "k", "SEED_IF_EMPTY": False, "ADMIN_PASSWORD": "old-admin-password-1"}
            create_app(cfg)
            conn = sqlite3.connect(path)
            self.assertIn("email", [r[1] for r in conn.execute("PRAGMA table_info(users)")])
            self.assertIn("assigned_to", [r[1] for r in conn.execute("PRAGMA table_info(interventions)")])
            self.assertEqual(conn.execute("SELECT note, assigned_to FROM interventions").fetchone(), ("old note", "oldstaff"))

            # Deliberately leaving one unassigned must survive later restarts (no second backfill)
            conn.execute("UPDATE interventions SET assigned_to = NULL")
            conn.commit()
            conn.close()
            create_app({**cfg, "ADMIN_PASSWORD": None})
            self.assertIsNone(sqlite3.connect(path).execute("SELECT assigned_to FROM interventions").fetchone()[0])


class DemoDataTests(ApiTestCase):
    def test_the_demo_administrator_has_reminders(self):
        summary = self.get("/api/reminders")
        self.assertGreater(summary["mine"]["open"], 0)
        self.assertGreaterEqual(summary["mine"]["overdue"] + summary["mine"]["due_soon"], 1)
        self.assertTrue(summary["mine"]["items"])


if __name__ == "__main__":
    unittest.main()
