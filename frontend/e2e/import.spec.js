import { test, expect } from "@playwright/test";
import { ADMIN, adminToken, authHeaders, API, createUser, signIn, uid } from "./helpers.js";

const file = (name, text) => ({ name, mimeType: "text/csv", buffer: Buffer.from(text) });

test.describe("CSV import (administrator)", () => {
  test("preview, import, then re-import with keep and replace", async ({ page }) => {
    const tag = uid("Imp");
    const [ann, ben] = [`${tag} Ann`, `${tag} Ben`];
    const csv = `Student,Course,Semester,Score\n${ann},Maths,2035-1,88\n${ann},English,2035-1,67\n${ben},Maths,2035-1,41\n`;
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Import data" }).click();
    await expect(page.getByRole("heading", { name: "Import results from CSV" })).toBeVisible();

    await page.getByLabel("CSV file").setInputFiles(file("results.csv", csv));
    await expect(page.getByRole("heading", { name: "Preview: results.csv" })).toBeVisible();
    await expect(page.getByText("3 rows read")).toBeVisible();
    await expect(page.getByText("2 new students to create")).toBeVisible();
    await expect(page.getByText("3 results to add")).toBeVisible();

    await page.getByRole("button", { name: "Import 3 results" }).click();
    await expect(page.getByText(/Import complete: 2 new students, 3 results added/)).toBeVisible();

    await page.goto(`/students?search=${tag}`);
    await expect(page.getByText(/Showing 3 of/)).toBeVisible();

    // The same file again: everything already exists
    await page.goto("/admin/import");
    await page.getByLabel("CSV file").setInputFiles(file("again.csv", csv));
    await expect(page.getByText("0 to update, 3 already there and skipped")).toBeVisible();
    await expect(page.getByText("Nothing new to import.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Import 0 results" })).toBeDisabled();

    // One changed score: kept by default, updated when asked
    const changed = csv.replace(`${ann},Maths,2035-1,88`, `${ann},Maths,2035-1,95`);
    await page.getByLabel("CSV file").setInputFiles(file("changed.csv", changed));
    await expect(page.getByText("0 to update, 3 already there and skipped")).toBeVisible();
    await page.getByLabel("Replace it with the score in the file").check();
    await expect(page.getByText("1 to update, 2 already there and skipped")).toBeVisible();
    await page.getByRole("button", { name: "Import 1 result" }).click();
    await expect(page.getByText(/1 updated, 2 skipped/)).toBeVisible();

    await page.goto(`/students?search=${ann}`);
    await expect(page.locator("tbody tr").filter({ hasText: "Maths" })).toContainText("95");
  });

  test("a file with problems lists them and imports nothing", async ({ page, request }) => {
    const tag = uid("Bad");
    const csv = `Student,Course,Semester,Score\n${tag} Ok,Maths,2035-1,70\n${tag} Bad,Maths,2035-1,abc\n,Maths,2035-1,50\n`;
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/import");
    await page.getByLabel("CSV file").setInputFiles(file("bad.csv", csv));

    await expect(page.getByText("2 rows can't be imported.", { exact: false })).toBeVisible();
    const problems = page.getByRole("table");
    await expect(problems.getByRole("row", { name: /3 .*Score must be a number between 0 and 100/ })).toBeVisible();
    await expect(problems.getByRole("row", { name: /4 .*Student name is required/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Import \d/ })).toHaveCount(0);

    const token = await adminToken(request);
    const res = await request.get(`${API}/api/students?search=${tag}`, { headers: authHeaders(token) });
    expect(await res.json()).toEqual([]);
  });

  test("a file without the right columns is explained", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/import");
    await page.getByLabel("CSV file").setInputFiles(file("wrong.csv", "Name,Course\nSomeone,Maths\n"));
    await expect(page.getByRole("alert")).toContainText("Missing column(s): semester, score");
  });

  test("the import page is for administrators only", async ({ page, request }) => {
    const staff = await createUser(request, { role: "staff", prefix: "staff" });
    await signIn(page, staff.username, staff.password);
    await page.goto("/admin/import");
    await expect(page.getByRole("heading", { name: "No access" })).toBeVisible();
  });
});
