import { test, expect } from "@playwright/test";
import { ADMIN, signIn } from "./helpers.js";

test.describe("appearance", () => {
  test("dark mode toggles, is remembered across reloads, and can be switched back", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "light");

    await page.getByRole("button", { name: "Dark mode" }).click();
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(page.getByRole("button", { name: "Light mode" })).toBeVisible();

    await page.getByRole("button", { name: "Light mode" }).click();
    await expect(html).toHaveAttribute("data-theme", "light");
  });

  test("the sign-in page follows the saved theme too", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("theme", "dark"));
    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 800 } });

  test("the menu is collapsed until you open it, and closes after you pick a page", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    const students = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Students" });
    await expect(students).toBeHidden();

    await page.getByRole("button", { name: "Menu" }).click();
    await expect(students).toBeVisible();
    await expect(page.getByRole("button", { name: "Close" })).toHaveAttribute("aria-expanded", "true");

    await page.keyboard.press("Escape");
    await expect(students).toBeHidden();

    await page.getByRole("button", { name: "Menu" }).click();
    await students.click();
    await expect(page).toHaveURL(/\/students$/);
    await expect(page.getByRole("heading", { name: "Students", level: 1 })).toBeVisible();
    await expect(students).toBeHidden();
  });

  test("pages do not scroll sideways", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    for (const path of ["/", "/students", "/courses", "/interventions"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(1);
    }
  });
});
