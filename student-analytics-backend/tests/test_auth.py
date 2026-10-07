import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import ADMIN, VIEWER, ApiTestCase  # noqa: E402


class AuthTests(ApiTestCase):
    def test_health_is_public_everything_else_needs_a_token(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        for url in ("/api/students", "/api/analytics", "/api/courses", "/api/users", "/api/nope"):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 401, url)
            self.assertEqual(res.get_json()["error"], "unauthorized")

    def test_bad_logins_look_identical(self):
        wrong = self.client.post("/api/auth/login", json={"username": ADMIN[0], "password": "nope"})
        unknown = self.client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.get_json(), unknown.get_json())

    def test_login_missing_fields_and_bad_body(self):
        self.assertEqual(self.client.post("/api/auth/login", json={"username": "x"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", data="not json").status_code, 400)

    def test_me_and_bad_tokens(self):
        me = self.get("/api/auth/me")
        self.assertEqual(me["user"]["username"], ADMIN[0])
        self.assertEqual(me["user"]["role"], "admin")
        self.assertNotIn("password_hash", str(me))
        for bad in ("garbage", self.admin_token + "x", ""):
            res = self.client.get("/api/auth/me", headers=self.auth(bad))
            self.assertEqual(res.status_code, 401)

    def test_expired_token_rejected(self):
        self.app.config["TOKEN_MAX_AGE"] = -1
        try:
            res = self.client.get("/api/auth/me", headers=self.auth(self.admin_token))
            self.assertEqual(res.status_code, 401)
        finally:
            self.app.config["TOKEN_MAX_AGE"] = 8 * 3600

    def test_username_is_case_insensitive(self):
        res = self.client.post("/api/auth/login", json={"username": ADMIN[0].upper(), "password": ADMIN[1]})
        self.assertEqual(res.status_code, 200)

    def test_viewer_can_read_but_not_write(self):
        self.assertTrue(self.get("/api/students", self.viewer_token))
        for method, url, body in [
            ("POST", "/api/students", {"name": "Nope"}),
            ("PUT", "/api/students/1", {"name": "Nope"}),
            ("DELETE", "/api/students/1", None),
            ("POST", "/api/students/1/records", {"course": "X", "semester": "2024-1", "score": 50}),
            ("PUT", "/api/records/1", {"score": 10}),
            ("DELETE", "/api/records/1", None),
            ("GET", "/api/users", None),
            ("POST", "/api/users", {"username": "evil", "password": "long-enough-pw", "role": "admin"}),
            ("GET", "/api/audit", None),
        ]:
            res = self.request(method, url, self.viewer_token, json=body)
            self.assertEqual(res.status_code, 403, f"{method} {url}")

    def test_cors_preflight_allows_authorization_header(self):
        res = self.client.options("/api/students", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        self.assertLess(res.status_code, 300)
        self.assertIn("Authorization", res.headers["Access-Control-Allow-Headers"])
        self.assertIn("POST", res.headers["Access-Control-Allow-Methods"])

    def test_api_responses_are_not_cacheable(self):
        res = self.request("GET", "/api/students")
        self.assertEqual(res.headers.get("Cache-Control"), "no-store")


class ChangePasswordTests(ApiTestCase):
    def test_change_password_signs_out_other_sessions(self):
        self.create_user("changer", "original-password-1")
        old = self.login("changer", "original-password-1")
        other = self.login("changer", "original-password-1")

        bad = self.client.post("/api/auth/change-password", headers=self.auth(old),
                               json={"current_password": "wrong", "new_password": "a-new-password-1"})
        self.assertEqual(bad.status_code, 400)
        weak = self.client.post("/api/auth/change-password", headers=self.auth(old),
                                json={"current_password": "original-password-1", "new_password": "short"})
        self.assertEqual(weak.status_code, 400)

        ok = self.client.post("/api/auth/change-password", headers=self.auth(old),
                              json={"current_password": "original-password-1", "new_password": "a-new-password-1"})
        self.assertEqual(ok.status_code, 200)
        fresh = ok.get_json()["token"]

        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(old)).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(other)).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(fresh)).status_code, 200)
        self.login("changer", "a-new-password-1")


class ThrottleTests(ApiTestCase):
    config = {"LOGIN_MAX_FAILS": 3, "LOGIN_LOCK_SECONDS": 60}

    def test_repeated_failures_lock_the_account_temporarily(self):
        self.create_user("locktest", "correct-horse-battery")
        for _ in range(3):
            res = self.client.post("/api/auth/login", json={"username": "locktest", "password": "bad"})
            self.assertEqual(res.status_code, 401)
        res = self.client.post("/api/auth/login", json={"username": "locktest", "password": "correct-horse-battery"})
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)
        # other users are unaffected
        self.assertEqual(
            self.client.post("/api/auth/login", json={"username": ADMIN[0], "password": ADMIN[1]}).status_code, 200
        )

    def test_success_resets_the_counter(self):
        self.create_user("resetter", "correct-horse-battery")
        for _ in range(2):
            self.client.post("/api/auth/login", json={"username": "resetter", "password": "bad"})
        self.login("resetter", "correct-horse-battery")
        for _ in range(2):
            self.client.post("/api/auth/login", json={"username": "resetter", "password": "bad"})
        self.login("resetter", "correct-horse-battery")


if __name__ == "__main__":
    unittest.main()
