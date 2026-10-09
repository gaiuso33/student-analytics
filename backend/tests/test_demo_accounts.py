import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import ApiTestCase  # noqa: E402
from app import create_app  # noqa: E402


class DemoViewerTests(ApiTestCase):
    config = {"DEMO_VIEWER_USERNAME": "demo-viewer", "DEMO_VIEWER_PASSWORD": "demo-viewer-pw-1"}

    def test_demo_viewer_exists_and_is_read_only(self):
        token = self.login("demo-viewer", "demo-viewer-pw-1")
        me = self.client.get("/api/auth/me", headers=self.auth(token)).get_json()["user"]
        self.assertEqual(me["role"], "viewer")
        self.assertTrue(self.get("/api/students", token))
        res = self.request("POST", "/api/students", token, json={"name": "Nope"})
        self.assertEqual(res.status_code, 403)


class DemoViewerSkippedTests(unittest.TestCase):
    def make(self, **config):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = create_app({
            "DATABASE": os.path.join(tmp.name, "t.db"), "SECRET_KEY": "k", "SEED_IF_EMPTY": False,
            "ADMIN_USERNAME": "boss", "ADMIN_PASSWORD": "a-long-admin-pw-1", **config,
        })
        return app.test_client()

    def can_login(self, client, user, pw):
        return client.post("/api/auth/login", json={"username": user, "password": pw}).status_code == 200

    def test_weak_demo_password_is_ignored_but_app_starts(self):
        client = self.make(DEMO_VIEWER_USERNAME="viewer", DEMO_VIEWER_PASSWORD="short")
        self.assertFalse(self.can_login(client, "viewer", "short"))
        self.assertTrue(self.can_login(client, "boss", "a-long-admin-pw-1"))

    def test_demo_username_cannot_clash_with_admin(self):
        client = self.make(DEMO_VIEWER_USERNAME="BOSS", DEMO_VIEWER_PASSWORD="demo-viewer-pw-1")
        self.assertFalse(self.can_login(client, "boss", "demo-viewer-pw-1"))
        self.assertTrue(self.can_login(client, "boss", "a-long-admin-pw-1"))

    def test_no_demo_viewer_unless_both_settings_present(self):
        client = self.make(DEMO_VIEWER_USERNAME="viewer")
        self.assertFalse(self.can_login(client, "viewer", ""))


class AdminPasswordPolicyTests(unittest.TestCase):
    def test_short_admin_password_stops_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                create_app({
                    "DATABASE": os.path.join(tmp, "t.db"), "SECRET_KEY": "k", "SEED_IF_EMPTY": False,
                    "ADMIN_USERNAME": "boss", "ADMIN_PASSWORD": "short",
                })
            self.assertIn("at least", str(ctx.exception))

    def test_generated_password_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_app({"DATABASE": os.path.join(tmp, "t.db"), "SECRET_KEY": "k",
                        "SEED_IF_EMPTY": False, "ADMIN_PASSWORD": None})


if __name__ == "__main__":
    unittest.main()
