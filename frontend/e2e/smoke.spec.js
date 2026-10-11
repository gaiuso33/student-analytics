import { test, expect } from "@playwright/test";
import { ADMIN, importRows, signIn, uid } from "./helpers.js";

test("every page opens without JavaScript errors", async ({ page, request }) => {
  // Two semesters of results so the insights, charts and lists have something to show
  const tag = uid("Smoke");
  await importRows(request, [
    [`${tag} One`, "Biology", "2041-1", 90], [`${tag} One`, "Biology", "2041-2", 40],
    [`${tag} Two`, "Biology", "2041-1", 45], [`${tag} Two`, "Biology", "2041-2", 85],
    [`${tag} Three`, "History", "2041-1", 70], [`${tag} Three`, "History", "2041-2", 75],
  ]);

  const problems = [];
  page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !/Failed to load resource/.test(message.text())) {
      problems.push(`console: ${message.text()}`);
    }
  });

  await signIn(page, ADMIN.username, ADMIN.password);
  const pages = [
    ["/", "Overview"],
    ["/students", "Students"],
    ["/courses", "Courses"],
    ["/interventions", "Follow-ups"],
    ["/admin/import", "Import results from CSV"],
    ["/admin/users", "Users"],
    ["/admin/audit", "Audit log"],
    ["/account", "Account"],
  ];
  for (const [path, heading] of pages) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
    await expect(page.getByText("Loading…")).toHaveCount(0);
  }
  expect(problems).toEqual([]);
});

test("the overview shows insights once there are two semesters of results", async ({ page, request }) => {
  const tag = uid("Ins");
  await importRows(request, [
    [`${tag} A`, "Geography", "2042-1", 90], [`${tag} A`, "Geography", "2042-2", 30],
  ]);
  await signIn(page, ADMIN.username, ADMIN.password);
  await expect(page.getByRole("heading", { name: "Insights" })).toBeVisible();
  await expect(page.locator(".insight").first()).toBeVisible();
  await expect(page.getByText(/Average GPA (rose|fell) by/)).toBeVisible();
  await expect(page.getByRole("link", { name: "View all student records" })).toBeVisible();
});

test("the API is unreachable: the app says so instead of showing a blank page", async ({ page }) => {
  await signIn(page, ADMIN.username, ADMIN.password);
  await page.route("**/api/students**", (route) => route.abort());
  await page.goto("/students");
  await expect(page.getByRole("alert")).toContainText("Cannot reach the server");
  await page.unroute("**/api/students**");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByLabel("Search")).toBeVisible();
});
