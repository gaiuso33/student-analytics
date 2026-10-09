import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import ApiTestCase  # noqa: E402


class WriteTests(ApiTestCase):
    def post(self, url, body, token=None):
        return self.request("POST", url, token, json=body)

    def new_student(self, name):
        res = self.post("/api/students", {"name": name})
        self.assertEqual(res.status_code, 201, res.get_data(as_text=True))
        return res.get_json()["id"]

    def test_student_lifecycle_and_derived_stats(self):
        before = self.get("/api/analytics")["total_students"]
        sid = self.new_student("  Test   Student ")  # whitespace is tidied
        self.assertEqual(self.get(f"/api/students/{sid}")["name"], "Test Student")

        # A student with no results yet is viewable and not at risk
        detail = self.get(f"/api/students/{sid}")
        self.assertEqual((detail["records"], detail["gpa"], detail["at_risk"]), ([], None, False))

        rec = self.post(f"/api/students/{sid}/records", {"course": "Physics", "semester": "2025-1", "score": 35})
        self.assertEqual(rec.status_code, 201)
        rid = rec.get_json()["id"]
        detail = self.get(f"/api/students/{sid}")
        self.assertEqual((detail["gpa"], detail["at_risk"], detail["failing_courses"]), (0.0, True, 1))
        self.assertEqual(self.get("/api/analytics")["total_students"], before + 1)
        self.assertIn(sid, [r["id"] for r in self.get("/api/at-risk-students")])

        upd = self.request("PUT", f"/api/records/{rid}", json={"score": 95})
        self.assertEqual(upd.status_code, 200)
        self.assertEqual(upd.get_json()["score"], 95)
        detail = self.get(f"/api/students/{sid}")
        self.assertEqual((detail["gpa"], detail["at_risk"]), (4.0, False))

        self.assertEqual(self.request("DELETE", f"/api/records/{rid}").status_code, 204)
        self.assertEqual(self.get(f"/api/students/{sid}")["records"], [])

        ren = self.request("PUT", f"/api/students/{sid}", json={"name": "Renamed Student"})
        self.assertEqual(ren.get_json()["name"], "Renamed Student")

        self.post(f"/api/students/{sid}/records", {"course": "Math", "semester": "2025-1", "score": 70})
        self.assertEqual(self.request("DELETE", f"/api/students/{sid}").status_code, 204)
        self.assertEqual(self.request("GET", f"/api/students/{sid}").status_code, 404)
        self.assertEqual(self.get("/api/analytics")["total_students"], before)  # records cascaded

    def test_validation(self):
        sid = self.new_student("Validation Victim")
        bad_students = [{}, {"name": ""}, {"name": "   "}, {"name": 5}, {"name": "x" * 101}, {"name": "bad\x00name"}]
        for body in bad_students:
            self.assertEqual(self.post("/api/students", body).status_code, 400, body)

        good = {"course": "Math", "semester": "2025-1", "score": 50}
        for patch in [{"score": 101}, {"score": -1}, {"score": True}, {"score": "80"}, {"score": None},
                      {"score": float("nan")}, {"course": ""}, {"course": "x" * 61}, {"semester": ""}]:
            res = self.post(f"/api/students/{sid}/records", {**good, **patch})
            self.assertEqual(res.status_code, 400, patch)
            self.assertEqual(res.get_json()["error"], "validation_error")
        self.assertEqual(self.post(f"/api/students/{sid}/records", {"course": "Math"}).status_code, 400)

        res = self.request("POST", "/api/students", data="not json", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_conflicts_and_not_found(self):
        sid = self.new_student("Conflict Carl")
        self.assertEqual(self.post("/api/students", {"name": "Conflict Carl"}).status_code, 409)

        body = {"course": "Math", "semester": "2025-1", "score": 60}
        first = self.post(f"/api/students/{sid}/records", body)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.post(f"/api/students/{sid}/records", body).status_code, 409)

        other = self.post(f"/api/students/{sid}/records", {**body, "course": "Physics"}).get_json()["id"]
        clash = self.request("PUT", f"/api/records/{other}", json={"course": "Math"})
        self.assertEqual(clash.status_code, 409)

        other_student = self.new_student("Other Olu")
        self.assertEqual(self.request("PUT", f"/api/students/{other_student}", json={"name": "Conflict Carl"}).status_code, 409)

        self.assertEqual(self.post("/api/students/999999/records", body).status_code, 404)
        self.assertEqual(self.request("PUT", "/api/records/999999", json={"score": 1}).status_code, 404)
        self.assertEqual(self.request("DELETE", "/api/records/999999").status_code, 404)
        self.assertEqual(self.request("DELETE", "/api/students/999999").status_code, 404)

    def test_writes_are_audited(self):
        sid = self.new_student("Audited Ada")
        entries = self.get("/api/audit?limit=20")
        match = [e for e in entries if e["action"] == "student.create" and f"id={sid}" in e["detail"]]
        self.assertTrue(match)
        self.assertEqual(match[0]["username"], "admin")
        self.assertEqual(self.request("GET", "/api/audit?limit=abc").status_code, 400)


class UserAdminTests(ApiTestCase):
    def test_create_list_validation(self):
        res = self.request("POST", "/api/users", json={"username": "newbie", "password": "long-enough-pw", "role": "viewer"})
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("password", str(res.get_json()))
        self.assertIn("newbie", [u["username"] for u in self.get("/api/users")])

        def create(**kw):
            body = {"username": "someone", "password": "long-enough-pw", "role": "viewer", **kw}
            return self.request("POST", "/api/users", json=body).status_code

        self.assertEqual(create(username="NEWBIE"), 409)  # case-insensitive duplicate
        self.assertEqual(create(password="short"), 400)
        self.assertEqual(create(username="a b"), 400)
        self.assertEqual(create(username="ab"), 400)
        self.assertEqual(create(role="superuser"), 400)

    def test_role_change_deactivate_and_reset_revoke_sessions(self):
        self.create_user("target", "target-password-1")
        uid = next(u["id"] for u in self.get("/api/users") if u["username"] == "target")
        token = self.login("target", "target-password-1")
        self.assertEqual(self.request("POST", "/api/students", token, json={"name": "Nope"}).status_code, 403)

        # promote: old token stops working (token_version bumped), new login can write
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"role": "admin"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(token)).status_code, 401)
        token = self.login("target", "target-password-1")
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(token)).get_json()["user"]["role"], "admin")

        # deactivate: token and login both refused
        self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json={"active": False}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(token)).status_code, 401)
        res = self.client.post("/api/auth/login", json={"username": "target", "password": "target-password-1"})
        self.assertEqual(res.status_code, 401)

        # reactivate and reset password
        self.request("PATCH", f"/api/users/{uid}", json={"active": True, "password": "brand-new-password"})
        self.assertEqual(self.client.post("/api/auth/login", json={"username": "target", "password": "target-password-1"}).status_code, 401)
        self.login("target", "brand-new-password")

    def test_admin_cannot_modify_themselves(self):
        me = self.get("/api/auth/me")["user"]["id"]
        for body in ({"role": "viewer"}, {"active": False}, {"password": "another-long-password"}):
            self.assertEqual(self.request("PATCH", f"/api/users/{me}", json=body).status_code, 400, body)
        self.assertEqual(self.client.get("/api/auth/me", headers=self.auth(self.admin_token)).status_code, 200)

    def test_patch_validation_and_404(self):
        self.create_user("patchme", "patchme-password-1")
        uid = next(u["id"] for u in self.get("/api/users") if u["username"] == "patchme")
        for body in ({"role": "root"}, {"active": "yes"}, {"password": "short"}):
            self.assertEqual(self.request("PATCH", f"/api/users/{uid}", json=body).status_code, 400, body)
        self.assertEqual(self.request("PATCH", "/api/users/999999", json={"role": "viewer"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
