import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest

from base import ApiTestCase


class ApiTests(ApiTestCase):
    def test_students_shape(self):
        rows = self.get("/api/students")
        self.assertGreater(len(rows), 0)
        self.assertEqual(set(rows[0]), {"id", "student_id", "name", "course", "score", "semester", "gpa", "at_risk"})
        self.assertEqual(len({r["id"] for r in rows}), len(rows))  # unique ids
        self.assertTrue(all(0 <= r["score"] <= 100 for r in rows))
        self.assertTrue(all(0 <= r["gpa"] <= 4 for r in rows))

    def test_students_filters(self):
        course = self.get("/api/students")[0]["course"]
        rows = self.get(f"/api/students?course={course}")
        self.assertTrue(rows and all(r["course"] == course for r in rows))
        self.assertEqual(self.get("/api/students?search=zzzzzz"), [])

    def test_analytics_consistent_with_students(self):
        a = self.get("/api/analytics")
        self.assertEqual(a["total_students"], 40)
        rows = self.get("/api/students")
        expected = round(100 * sum(r["score"] >= 60 for r in rows) / len(rows), 1)
        self.assertEqual(a["pass_rate"], expected)
        self.assertLessEqual(a["average_gpa"], a["highest_gpa"])

    def test_top_students_sorted_and_limited(self):
        top = self.get("/api/top-students?limit=3")
        self.assertEqual(len(top), 3)
        gpas = [t["gpa"] for t in top]
        self.assertEqual(gpas, sorted(gpas, reverse=True))
        self.assertEqual(top[0]["gpa"], self.get("/api/analytics")["highest_gpa"])

    def test_top_students_bad_limit(self):
        res = self.request("GET", "/api/top-students?limit=abc")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"], "bad_request")

    def test_course_difficulty_hardest_first(self):
        courses = self.get("/api/course-difficulty")
        avgs = [c["average_score"] for c in courses]
        self.assertEqual(avgs, sorted(avgs))

    def test_at_risk_below_threshold(self):
        threshold = self.app.config["AT_RISK_GPA"]
        rows = self.get("/api/at-risk-students")
        self.assertTrue(all(r["gpa"] < threshold for r in rows))

    def test_gpa_trend_chronological(self):
        trend = self.get("/api/gpa-trend")
        sems = [t["semester"] for t in trend]
        self.assertEqual(sems, sorted(sems))

    def test_at_risk_flag_matches_endpoint(self):
        rows = self.get("/api/students")
        flagged = {r["student_id"] for r in rows if r["at_risk"]}
        expected = {r["id"] for r in self.get("/api/at-risk-students")}
        self.assertEqual(flagged, expected)
        self.assertTrue(flagged)  # demo data includes at-risk students

    def test_at_risk_filter(self):
        rows = self.get("/api/students?at_risk=true")
        self.assertTrue(rows and all(r["at_risk"] for r in rows))
        everything = self.get("/api/students")
        self.assertLess(len(rows), len(everything))
        combined = self.get("/api/students?at_risk=1&course=" + rows[0]["course"])
        self.assertTrue(all(r["at_risk"] and r["course"] == rows[0]["course"] for r in combined))

    def test_student_detail(self):
        sid = self.get("/api/students")[0]["student_id"]
        d = self.get(f"/api/students/{sid}")
        self.assertEqual(d["id"], sid)
        self.assertTrue(d["records"])
        self.assertTrue(d["semester_gpa"])
        self.assertEqual(d["at_risk"], d["gpa"] < self.app.config["AT_RISK_GPA"])

    def test_student_detail_404(self):
        res = self.request("GET", "/api/students/999999")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()["error"], "not_found")

    def test_courses_summary(self):
        courses = self.get("/api/courses")
        self.assertEqual(
            [c["average_score"] for c in courses],
            sorted(c["average_score"] for c in courses),
        )
        self.assertTrue(all(0 <= c["pass_rate"] <= 100 for c in courses))
        self.assertEqual(
            {c["course"] for c in courses},
            {c["course"] for c in self.get("/api/course-difficulty")},
        )

    def test_cors_only_for_allowed_origin(self):
        ok = self.client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(ok.headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")
        bad = self.client.get("/api/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", bad.headers)

    def test_json_404(self):
        res = self.request("GET", "/api/nope")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
