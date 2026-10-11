import { test, expect } from "@playwright/test";
import { ADMIN, createUser, signIn, signOut } from "./helpers.js";

test.describe("signing in", () => {
  test("visitors are sent to the sign-in page", async ({ page }) => {
    await page.goto("/students");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Student analytics" })).toBeVisible();
  });

  test("a wrong password shows a clear error and stays on the page", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Username").fill(ADMIN.username);
    await page.getByLabel("Password").fill("definitely-wrong");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Incorrect username or password.");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("an empty form asks for both fields", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Enter your username and password.");
  });

  test("admin signs in, survives a reload, and signs out", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    await expect(page.getByText("Administrator", { exact: true })).toBeVisible();

    await page.reload();
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

    await signOut(page);
    await page.goto("/students");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("after signing in you land on the page you asked for, filters included", async ({ page }) => {
    await page.goto("/students?risk=1");
    await expect(page).toHaveURL(/\/login$/);
    await page.getByLabel("Username").fill(ADMIN.username);
    await page.getByLabel("Password").fill(ADMIN.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Students", level: 1, exact: true })).toBeVisible();
    await expect(page).toHaveURL(/\/students\?risk=1/);
    await expect(page.getByLabel("At-risk students only")).toBeChecked();
  });

  test("unknown pages show a not-found message once signed in", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/no-such-page");
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  });
});

test.describe("viewer permissions", () => {
  test("a viewer sees no admin menu items, buttons or pages", async ({ page, request }) => {
    const viewer = await createUser(request, { role: "viewer", prefix: "viewer" });
    await signIn(page, viewer.username, viewer.password);

    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: "Students" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Follow-ups" })).toBeVisible();
    for (const hidden of ["Users", "Audit log", "Import data"]) {
      await expect(nav.getByRole("link", { name: hidden })).toHaveCount(0);
    }
    await expect(page.getByText("Viewer", { exact: true })).toBeVisible();

    await page.getByRole("link", { name: "Students" }).first().click();
    await expect(page.getByRole("heading", { name: "Students", level: 1, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Add student" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Import CSV" })).toHaveCount(0);

    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: "No access" })).toBeVisible();
  });
});
