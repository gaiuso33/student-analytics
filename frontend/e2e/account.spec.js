import { test, expect } from "@playwright/test";
import { createUser, signIn, signOut } from "./helpers.js";

test.describe("changing your own password", () => {
  test("mismatched or short passwords are refused, then a real change works", async ({ page, request }) => {
    const user = await createUser(request, { role: "viewer", prefix: "pwuser" });
    const next = "My-new-passphrase-9";
    await signIn(page, user.username, user.password);
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Account" }).click();
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();
    await expect(page.getByRole("main").getByText(user.username, { exact: true })).toBeVisible();

    await page.getByLabel("Current password").fill(user.password);
    await page.getByLabel("New password", { exact: true }).fill("short");
    await page.getByLabel("Repeat new password").fill("short");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("alert")).toHaveText("Password must be at least 10 characters");

    await page.getByLabel("New password", { exact: true }).fill(next);
    await page.getByLabel("Repeat new password").fill("something-else-entirely");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("alert")).toHaveText("The new passwords don't match");

    await page.getByLabel("Current password").fill("not-my-password");
    await page.getByLabel("Repeat new password").fill(next);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("alert")).toHaveText("Current password is incorrect.");

    await page.getByLabel("Current password").fill(user.password);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("status")).toHaveText(/Password changed/);
    // still signed in with the refreshed session
    await page.reload();
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();

    await signOut(page);
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password").fill(user.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Incorrect username or password.");
    // the new password works, and they are taken back to the page they left
    await page.getByLabel("Password").fill(next);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();
  });
});
