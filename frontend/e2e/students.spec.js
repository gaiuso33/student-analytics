import fs from "node:fs";
import { test, expect } from "@playwright/test";
import { ADMIN, acceptDialogs, importRows, signIn, uid } from "./helpers.js";

test.describe("managing students (administrator)", () => {
  test("add a student and a result, edit it, then delete everything", async ({ page }) => {
    const name = uid("Lifecycle");
    acceptDialogs(page);
    await signIn(page, ADMIN.username, ADMIN.password);

    // Create the student from the Students page
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Students" }).click();
    await page.getByRole("link", { name: "Add student" }).click();
    await page.getByLabel("Student name").fill(name);
    await page.getByRole("button", { name: "Create student" }).click();
    await expect(page.getByRole("heading", { name })).toBeVisible();
    await expect(page.getByText("No results recorded yet.")).toBeVisible();

    // Add a failing result: the student becomes at risk
    await page.getByRole("button", { name: "Add result" }).click();
    await page.getByLabel("Course").fill("Physics");
    await page.getByLabel("Semester").fill("2030-1");
    await page.getByLabel("Score (0-100)").fill("35");
    await page.getByRole("button", { name: "Add result" }).click();
    const row = page.getByRole("row", { name: /Physics/ });
    await expect(row).toContainText("2030-1");
    await expect(row).toContainText("35");
    await expect(page.getByText("At risk", { exact: true })).toBeVisible();
    await expect(page.getByText("This student is at risk and has no open follow-up.")).toBeVisible();

    // Edit the score: now on track
    await page.getByRole("button", { name: "Edit Physics 2030-1" }).click();
    await page.getByLabel("Score (0-100)").fill("90");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("row", { name: /Physics/ })).toContainText("90");
    await expect(page.getByText("On track", { exact: true })).toBeVisible();

    // Delete the result, then the student
    await page.getByRole("button", { name: "Delete Physics 2030-1" }).click();
    await expect(page.getByText("No results recorded yet.")).toBeVisible();
    await page.getByRole("button", { name: "Delete student" }).click();
    await expect(page).toHaveURL(/\/students$/);

    // The audit log remembers who did what
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Audit log" }).click();
    await expect(page.getByRole("cell", { name: "student.create" }).first()).toBeVisible();
    await expect(page.getByRole("cell", { name: "student.delete" }).first()).toBeVisible();
  });

  test("invalid results are rejected with clear messages", async ({ page, request }) => {
    const name = uid("Invalid");
    await importRows(request, [[name, "Math", "2030-1", 70]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${name}`);
    await page.getByRole("link", { name }).click();

    await page.getByRole("button", { name: "Add result" }).click();
    await page.getByRole("button", { name: "Add result" }).click();
    await expect(page.getByText("Course is required")).toBeVisible();
    await expect(page.getByText("Semester is required")).toBeVisible();
    await expect(page.getByText("Score must be a number from 0 to 100")).toBeVisible();

    await page.getByLabel("Course").fill("Math");
    await page.getByLabel("Semester").fill("2030-1");
    await page.getByLabel("Score (0-100)").fill("55");
    await page.getByRole("button", { name: "Add result" }).click();
    await expect(page.getByRole("alert")).toContainText("already has a result for that course and semester");
  });

  test("a student can be renamed", async ({ page, request }) => {
    const name = uid("Before");
    const renamed = uid("After");
    await importRows(request, [[name, "Math", "2030-1", 70]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${name}`);
    await page.getByRole("link", { name }).click();
    await page.getByRole("button", { name: "Rename" }).click();
    await page.getByLabel("Student name").fill(renamed);
    await page.getByRole("button", { name: "Save name" }).click();
    await expect(page.getByRole("heading", { name: renamed })).toBeVisible();
  });
});

test.describe("the students list", () => {
  test("search, score range, at-risk filter, sorting and URL state", async ({ page, request }) => {
    const tag = uid("Fil");
    const [alpha, beta, gamma] = [`${tag} Alpha`, `${tag} Beta`, `${tag} Gamma`];
    await importRows(request, [
      [alpha, "Chemistry", "2031-1", 95],
      [beta, "Chemistry", "2031-1", 72],
      [gamma, "Chemistry", "2031-1", 35],
    ]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/students");

    await page.getByLabel("Search").fill(tag);
    await expect(page.getByText(/Showing 3 of \d+/)).toBeVisible();
    for (const n of [alpha, beta, gamma]) await expect(page.getByRole("link", { name: n })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(tag));

    // Minimum score hides the failing student
    await page.getByLabel("Min score").fill("60");
    await expect(page.getByText(/Showing 2 of \d+/)).toBeVisible();
    await expect(page.getByRole("link", { name: gamma })).toHaveCount(0);

    // Maximum score keeps only the failing student
    await page.getByLabel("Min score").fill("");
    await page.getByLabel("Max score").fill("60");
    await expect(page.getByText(/Showing 1 of \d+/)).toBeVisible();
    await expect(page.getByRole("link", { name: gamma })).toBeVisible();

    // At-risk only, with the badge in the row
    await page.getByLabel("Max score").fill("");
    await page.getByLabel("At-risk students only").check();
    await expect(page.getByRole("link", { name: gamma })).toBeVisible();
    await expect(page.getByRole("link", { name: alpha })).toHaveCount(0);
    await expect(page.locator("tbody tr").filter({ hasText: gamma })).toContainText("At risk");

    // Clearing the filters brings everything back
    await page.getByLabel("At-risk students only").uncheck();
    await expect(page.getByText(/Showing 3 of \d+/)).toBeVisible();

    // Sorting by score, both directions
    await page.getByRole("button", { name: "Score" }).click();
    await expect(page.locator("tbody tr").first()).toContainText(gamma);
    await page.getByRole("button", { name: "Score" }).click();
    await expect(page.locator("tbody tr").first()).toContainText(alpha);

    // The whole view survives a reload
    await page.reload();
    await expect(page.getByLabel("Search")).toHaveValue(tag);
    await expect(page.locator("tbody tr").first()).toContainText(alpha);

    // Nothing matches: friendly empty state
    await page.getByLabel("Search").fill(`${tag}-nothing-here`);
    await expect(page.getByText("No records match these filters.", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByLabel("Search")).toHaveValue("");
  });

  test("typing in the search box keeps every character, and the checkboxes respond at once", async ({ page, request }) => {
    const tag = uid("Typed");
    await importRows(request, [[`${tag} Anna`, "Math", "2031-1", 20], [`${tag} Ben`, "Math", "2031-1", 90]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/students");

    // Key by key, as a person types: nothing may be dropped or reordered
    const search = page.getByLabel("Search");
    await search.pressSequentially(`${tag} An`, { delay: 5 });
    await expect(search).toHaveValue(`${tag} An`);
    await expect(page.getByRole("link", { name: `${tag} Anna` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Ben` })).toHaveCount(0);

    // check() and uncheck() fail if the box does not change state straight away
    await search.fill(tag);
    await page.getByLabel("At-risk students only").check();
    await expect(page.getByRole("link", { name: `${tag} Anna` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Ben` })).toHaveCount(0);
    await page.getByLabel("At-risk students only").uncheck();
    await expect(page.getByRole("link", { name: `${tag} Ben` })).toBeVisible();
    await expect(page).not.toHaveURL(/risk=1/);
  });

  test("links that point at this page change the filters; the sidebar link clears them", async ({ page, request }) => {
    const tag = uid("Nav");
    await importRows(request, [[`${tag} Low`, "Algebra", "2031-1", 20], [`${tag} High`, "Algebra", "2031-1", 95]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${tag}&max=59`);
    await expect(page.getByRole("link", { name: `${tag} Low` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} High` })).toHaveCount(0);
    await expect(page.getByLabel("Max score")).toHaveValue("59");

    // Clicking "Students" in the menu while on the page starts again from a clean list
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Students" }).click();
    await expect(page.getByLabel("Search")).toHaveValue("");
    await expect(page.getByLabel("Max score")).toHaveValue("");
    await expect(page).toHaveURL(/\/students$/);

    // Back to a filtered view, then use the browser's own reload: the address restores it
    await page.getByLabel("Search").fill(tag);
    await page.getByLabel("Min score").fill("60");
    await page.reload();
    await expect(page.getByLabel("Search")).toHaveValue(tag);
    await expect(page.getByLabel("Min score")).toHaveValue("60");
    await expect(page.getByRole("link", { name: `${tag} High` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Low` })).toHaveCount(0);
  });

  test("pagination: page size, next and previous, and the page lives in the URL", async ({ page, request }) => {
    const tag = uid("Pg");
    const rows = Array.from({ length: 25 }, (_, i) => [`${tag}n${String(i).padStart(2, "0")}`, "Math", "2032-1", 80]);
    await importRows(request, rows);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${tag}`);

    await expect(page.getByText("1–25 of 25")).toBeVisible();
    await page.getByLabel("Rows per page").selectOption("10");
    await expect(page.getByText("Page 1 of 3")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(10);
    await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();

    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Page 2 of 3")).toBeVisible();
    await expect(page).toHaveURL(/page=2/);
    await page.reload();
    await expect(page.getByText("Page 2 of 3")).toBeVisible();

    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("Page 3 of 3")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(5);
    await expect(page.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  test("export downloads the filtered list as CSV", async ({ page, request }) => {
    const tag = uid("Exp");
    const [good, weak] = [`${tag} Good`, `${tag} Weak`];
    await importRows(request, [[good, "Math", "2033-1", 92], [weak, "Math", "2033-1", 20]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${tag}`);
    await expect(page.getByText(/Showing 2 of/)).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /Export CSV \(2\)/ }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^student-records-\d{4}-\d{2}-\d{2}\.csv$/);
    const text = fs.readFileSync(await download.path(), "utf8");
    expect(text).toContain("Student,Course,Semester,Score,Grade,GPA,At risk");
    expect(text).toMatch(new RegExp(`${good},Math,2033-1,92,A,4,No`));
    expect(text).toMatch(new RegExp(`${weak},Math,2033-1,20,F,0,Yes`));
  });

  test("a student's row links to their page", async ({ page, request }) => {
    const name = uid("Link");
    await importRows(request, [[name, "Math", "2033-1", 77], [name, "English", "2033-1", 83]]);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${name}`);
    await page.getByRole("link", { name }).first().click();
    await expect(page.getByRole("heading", { name })).toBeVisible();
    await expect(page.getByText("Cumulative GPA")).toBeVisible();
    await expect(page.getByRole("row", { name: /Math/ })).toContainText("C");
    await expect(page.getByRole("row", { name: /English/ })).toContainText("B");
  });
});
