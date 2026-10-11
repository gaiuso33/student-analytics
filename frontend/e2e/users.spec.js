import { test, expect } from "@playwright/test";
import { ADMIN, signIn, uid } from "./helpers.js";

const nav = (page) => page.getByRole("navigation", { name: "Main" });

test.describe("user management (administrator)", () => {
  test("create a staff account, sign in as them, then deactivate them", async ({ page, browser }) => {
    const username = uid("newstaff");
    const password = "a-long-password-1";
    await signIn(page, ADMIN.username, ADMIN.password);
    await nav(page).getByRole("link", { name: "Users" }).click();

    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Temporary password").fill(password);
    await page.getByLabel("Role", { exact: true }).selectOption({ label: "Staff (can record follow-ups)" });
    await page.getByRole("button", { name: "Create user" }).click();
    const row = page.getByRole("row", { name: new RegExp(username) });
    await expect(row).toContainText("Active");
    await expect(page.getByLabel(`Role for ${username}`)).toHaveValue("staff");

    // The new person can sign in and sees the staff menu
    const other = await browser.newContext();
    const staffPage = await other.newPage();
    await signIn(staffPage, username, password);
    await expect(staffPage.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Follow-ups" })).toBeVisible();
    await expect(staffPage.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Users" })).toHaveCount(0);

    // Deactivating signs them out straight away and blocks new sign-ins
    await row.getByRole("button", { name: "Deactivate" }).click();
    await expect(row).toContainText("Deactivated");
    await staffPage.goto("/students");
    await expect(staffPage).toHaveURL(/\/login$/);
    await staffPage.getByLabel("Username").fill(username);
    await staffPage.getByLabel("Password").fill(password);
    await staffPage.getByRole("button", { name: "Sign in" }).click();
    await expect(staffPage.getByRole("alert")).toHaveText("Incorrect username or password.");

    // Reactivate and they can come back
    await row.getByRole("button", { name: "Reactivate" }).click();
    await expect(row).toContainText("Active");
    await staffPage.getByRole("button", { name: "Sign in" }).click();
    // they were sent to the login page from /students, so that is where they land
    await expect(staffPage.getByRole("heading", { name: "Students", level: 1 })).toBeVisible();
    await other.close();
  });

  test("a changed role takes effect and the admin row has no controls", async ({ page, request, browser }) => {
    const username = uid("roleuser");
    const password = "a-long-password-2";
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Temporary password").fill(password);
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByLabel(`Role for ${username}`)).toHaveValue("viewer");

    await page.getByLabel(`Role for ${username}`).selectOption("admin");
    await expect(page.getByLabel(`Role for ${username}`)).toHaveValue("admin");

    const adminRow = page.getByRole("row", { name: new RegExp(`^${ADMIN.username}\\b`) });
    await expect(adminRow).toContainText("You");
    await expect(adminRow.getByRole("button")).toHaveCount(0);

    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await signIn(p, username, password);
    await expect(p.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Users" })).toBeVisible();
    await ctx.close();
  });

  test("weak passwords and taken usernames are refused", async ({ page }) => {
    const username = uid("dup");
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");

    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Temporary password").fill("short");
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByText("Password must be at least 10 characters")).toBeVisible();

    await page.getByLabel("Temporary password").fill("long-enough-pw-1");
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByRole("row", { name: new RegExp(username) })).toBeVisible();

    await page.getByLabel("Username").fill(username.toUpperCase());
    await page.getByLabel("Temporary password").fill("long-enough-pw-1");
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByText("That username is already taken")).toBeVisible();
  });

  test("an administrator can reset someone's password", async ({ page, browser }) => {
    const username = uid("resetme");
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Temporary password").fill("original-password-1");
    await page.getByRole("button", { name: "Create user" }).click();
    const row = page.getByRole("row", { name: new RegExp(username) });
    await row.getByRole("button", { name: "Reset password" }).click();
    await page.getByLabel(`New password for ${username}`).fill("brand-new-password-1");
    await page.getByRole("button", { name: "Set password", exact: true }).click();
    await expect(page.getByLabel(`New password for ${username}`)).toHaveCount(0);

    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await signIn(p, username, "brand-new-password-1");
    await ctx.close();
  });
});
