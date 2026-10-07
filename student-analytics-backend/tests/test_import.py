import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import ApiTestCase  # noqa: E402

HEADER = "Student,Course,Semester,Score\n"


class ImportTests(ApiTestCase):
    def imp(self, csv_text, token=None, **extra):
        return self.request("POST", "/api/import", token, json={"csv": csv_text, **extra})

    def counts(self):
        return len(self.get("/api/students")), self.get("/api/analytics")["total_students"]

    def test_dry_run_reports_without_writing(self):
        before = self.counts()
        res = self.imp(HEADER + "Imp Dry,Chemistry,2026-1,81\nImp Dry,English,2026-1,90\n", dry_run=True)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual((body["students_created"], body["records_created"], body["imported"]), (1, 2, False))
        self.assertEqual(self.counts(), before)

    def test_commit_creates_students_and_results(self):
        before = self.counts()
        res = self.imp(HEADER + "Imp Real,Chemistry,2026-1,81\nImp Real,English,2026-1,90\nImp Two,Physics,2026-1,40\n")
        body = res.get_json()
        self.assertEqual(res.status_code, 200, body)
        self.assertTrue(body["imported"])
        self.assertEqual((body["students_created"], body["records_created"]), (2, 3))
        self.assertEqual(self.counts(), (before[0] + 3, before[1] + 2))
        sid = next(r["student_id"] for r in self.get("/api/students?search=imp%20two"))
        self.assertTrue(self.get(f"/api/students/{sid}")["at_risk"])
        self.assertTrue(any(e["action"] == "import" for e in self.get("/api/audit?limit=5")))

    def test_matches_existing_student_and_course_ignoring_case(self):
        existing = self.get("/api/students")[0]
        csv_text = HEADER + f"{existing['name'].upper()},{existing['course'].lower()},2099-1,77\n"
        body = self.imp(csv_text).get_json()
        self.assertEqual((body["students_created"], body["records_created"]), (0, 1))
        rows = self.get(f"/api/students?semester=2099-1")
        self.assertEqual(rows[0]["name"], existing["name"])
        self.assertEqual(rows[0]["course"], existing["course"])

    def test_duplicates_skip_or_update(self):
        self.imp(HEADER + "Imp Dup,Math,2027-1,50\n")
        again = self.imp(HEADER + "Imp Dup,Math,2027-1,90\n").get_json()
        self.assertEqual((again["records_created"], again["records_skipped"], again["records_updated"]), (0, 1, 0))
        self.assertEqual(self.get("/api/students?search=imp%20dup")[0]["score"], 50)

        upd = self.imp(HEADER + "Imp Dup,Math,2027-1,90\n", on_duplicate="update").get_json()
        self.assertEqual((upd["records_updated"], upd["records_skipped"]), (1, 0))
        self.assertEqual(self.get("/api/students?search=imp%20dup")[0]["score"], 90)

        same = self.imp(HEADER + "Imp Dup,Math,2027-1,90\n", on_duplicate="update").get_json()
        self.assertEqual((same["records_updated"], same["records_skipped"]), (0, 1))  # unchanged

    def test_row_errors_block_the_whole_import(self):
        before = self.counts()
        text = (HEADER + "Good Gina,Math,2028-1,70\n,Math,2028-1,70\nBad Bob,Math,2028-1,abc\n"
                "Bad Bea,Math,2028-1,101\nDup Dan,Math,2028-1,50\ndup dan,math,2028-1,60\n")
        dry = self.imp(text, dry_run=True).get_json()
        self.assertEqual(dry["error_count"], 4)
        self.assertEqual([e["row"] for e in dry["errors"]], [3, 4, 5, 7])
        self.assertIn("Duplicate of row 6", dry["errors"][3]["message"])

        res = self.imp(text)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"], "import_failed")
        self.assertEqual(self.counts(), before)  # nothing written, not even the good row

    def test_flexible_formats(self):
        # BOM, semicolons, decimal commas, aliases, extra columns, blank lines, quoted cells
        text = "\ufeffstudent name;TERM;Subject;Marks;Notes\nFlex Fred;2029-1;\"Art; Design\";85,5;hello\n\n"
        body = self.imp(text).get_json()
        self.assertEqual((body["records_created"], body["error_count"]), (1, 0), body)
        row = self.get("/api/students?search=flex%20fred")[0]
        self.assertEqual((row["course"], row["score"], row["semester"]), ("Art; Design", 85.5, "2029-1"))

    def test_roundtrip_with_dashboard_export_format(self):
        text = "Student,Course,Semester,Score,Grade,GPA,At risk\r\nRound Rita,Math,2030-1,91,A,4,No\r\n"
        body = self.imp(text).get_json()
        self.assertEqual((body["records_created"], body["error_count"]), (1, 0))

    def test_file_level_problems(self):
        for text, fragment in [
            ("", "empty"),
            (HEADER, "no data rows"),
            ("Student,Course\nA,B\n", "Missing column"),
        ]:
            res = self.imp(text)
            self.assertEqual(res.status_code, 400, text)
            self.assertIn(fragment, res.get_json()["message"])

    def test_row_limit(self):
        self.app.config["MAX_IMPORT_ROWS"] = 2
        try:
            res = self.imp(HEADER + "A,M,1,1\nB,M,1,1\nC,M,1,1\n")
            self.assertEqual(res.status_code, 400)
            self.assertIn("Too many rows", res.get_json()["message"])
        finally:
            self.app.config["MAX_IMPORT_ROWS"] = 5000

    def test_bad_requests_and_permissions(self):
        self.assertEqual(self.request("POST", "/api/import", json={"nope": 1}).status_code, 400)
        self.assertEqual(self.imp(HEADER + "A,B,C,1\n", on_duplicate="explode").status_code, 400)
        self.assertEqual(self.imp(HEADER + "A,B,C,1\n", token=self.viewer_token).status_code, 403)
        self.assertEqual(self.client.post("/api/import", json={"csv": HEADER}).status_code, 401)

    def test_oversized_request_rejected(self):
        res = self.imp("x" * (2 * 1024 * 1024 + 10))
        self.assertEqual(res.status_code, 413)
        self.assertEqual(res.get_json()["error"], "too_large")


if __name__ == "__main__":
    unittest.main()
