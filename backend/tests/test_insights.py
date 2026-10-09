import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import ApiTestCase  # noqa: E402


def load(case, csv_text):
    res = case.client.post("/api/import", json={"csv": csv_text}, headers=case.auth(case.admin_token))
    assert res.status_code == 200, res.get_data(as_text=True)


def by_id(insights):
    return {i["id"]: i for i in insights["insights"]}


class TrendTests(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load(cls, "Student,Course,Semester,Score\n"
                  "Ann,Math,2025-1,90\nAnn,Math,2025-2,50\n"   # GPA 4 -> 0
                  "Ben,Math,2025-1,50\nBen,Math,2025-2,90\n"   # GPA 0 -> 4
                  "Cy,Math,2025-1,70\nCy,Math,2025-2,80\n"     # GPA 2 -> 3
                  "Dee,Math,2025-2,40\n")                      # only in the latest semester

    def test_semesters_and_gpa_trend(self):
        data = self.get("/api/insights")
        self.assertEqual((data["previous_semester"], data["semester"]), ("2025-1", "2025-2"))
        trend = by_id(data)["gpa-trend"]
        self.assertEqual(trend["tone"], "warning")
        # 2025-1 average (4+0+2)/3 = 2.00, 2025-2 average (0+4+3+0)/4 = 1.75
        self.assertIn("fell by 0.25", trend["text"])
        self.assertIn("2.00", trend["text"])
        self.assertIn("1.75", trend["text"])

    def test_pass_rate_change(self):
        rate = by_id(self.get("/api/insights"))["pass-rate"]
        self.assertEqual(rate["tone"], "warning")
        self.assertIn("fell by 16.7%", rate["text"])  # 66.7% -> 50.0%

    def test_declining_and_improving_students(self):
        found = by_id(self.get("/api/insights"))
        declining = found["declining-students"]
        self.assertEqual([s["name"] for s in declining["students"]], ["Ann"])
        self.assertEqual(declining["students"][0]["detail"], "GPA 4.00 to 0.00")
        self.assertIn("1 student dropped", declining["text"])
        improving = found["improving-students"]
        self.assertEqual([s["name"] for s in improving["students"]], ["Ben", "Cy"])  # biggest gain first
        self.assertIn("2 students improved", improving["text"])
        self.assertTrue(all(isinstance(s["id"], int) for s in declining["students"] + improving["students"]))

    def test_single_course_gives_no_course_insight(self):
        self.assertNotIn("hardest-course", by_id(self.get("/api/insights")))

    def test_viewer_can_read_and_anonymous_cannot(self):
        self.assertEqual(self.request("GET", "/api/insights", self.viewer_token).status_code, 200)
        self.assertEqual(self.client.get("/api/insights").status_code, 401)


class RisingTests(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    def test_rise_and_unchanged_wording(self):
        load(self, "Student,Course,Semester,Score\nAnn,Math,2025-1,70\nAnn,Math,2025-2,80\n")
        found = by_id(self.get("/api/insights"))
        self.assertEqual(found["gpa-trend"]["tone"], "positive")
        self.assertIn("rose by 1.00", found["gpa-trend"]["text"])
        self.assertEqual(found["pass-rate"]["tone"], "neutral")
        self.assertIn("unchanged at 100.0%", found["pass-rate"]["text"])

    def test_small_moves_are_not_called_out(self):
        load(self, "Student,Course,Semester,Score\nZed,Art,2026-1,75\nZed,Art,2026-2,79\n")
        # 75 and 79 are both a C: GPA does not move at all
        self.assertNotIn("declining-students", by_id(self.get("/api/insights")))


class CourseTests(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    def test_lowest_pass_rate_course(self):
        load(self, "Student,Course,Semester,Score\n"
                   "A,Math,2025-1,50\nB,Math,2025-1,40\nC,Math,2025-1,70\nD,Math,2025-1,80\n"
                   "A,Physics,2025-1,90\nB,Physics,2025-1,85\nC,Physics,2025-1,95\nD,Physics,2025-1,99\n")
        found = by_id(self.get("/api/insights"))
        course = found["hardest-course"]
        self.assertIn("Math has the lowest pass rate: 50.0% (overall 75.0%)", course["text"])
        self.assertEqual(course["tone"], "warning")
        self.assertEqual(course["link"], "/students?course=Math&max=59")
        self.assertNotIn("gpa-trend", found)  # only one semester of data


class LinkEncodingTests(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    def test_course_names_with_spaces_are_url_encoded(self):
        load(self, "Student,Course,Semester,Score\nA,Computer Science,2025-1,40\nA,Art,2025-1,90\n")
        link = by_id(self.get("/api/insights"))["hardest-course"]["link"]
        self.assertEqual(link, "/students?course=Computer%20Science&max=59")


class EmptyTests(ApiTestCase):
    config = {"SEED_IF_EMPTY": False}

    def test_no_data_returns_empty_list(self):
        data = self.get("/api/insights")
        self.assertEqual((data["semester"], data["previous_semester"], data["insights"]), (None, None, []))


class DemoDataTests(ApiTestCase):
    def test_demo_data_produces_insights(self):
        data = self.get("/api/insights")
        self.assertEqual(data["semester"], "2025-2")
        self.assertEqual(data["previous_semester"], "2025-1")
        ids = set(by_id(data))
        self.assertTrue({"gpa-trend", "pass-rate", "hardest-course"} <= ids, ids)


class CorsLocalhostTests(ApiTestCase):
    config = {"CORS_ALLOW_ANY_LOCALHOST": True}

    def test_any_local_port_allowed_but_not_other_hosts(self):
        for origin in ("http://localhost:5174", "http://127.0.0.1:3000", "http://localhost"):
            res = self.client.get("/api/health", headers={"Origin": origin})
            self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), origin, origin)
        for origin in ("http://evil.example", "http://localhost.evil.example", "http://evil.example:5173"):
            res = self.client.get("/api/health", headers={"Origin": origin})
            self.assertNotIn("Access-Control-Allow-Origin", res.headers, origin)


if __name__ == "__main__":
    unittest.main()
