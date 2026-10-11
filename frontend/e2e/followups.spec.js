import { test, expect } from "@playwright/test";
import {
  ADMIN, API, acceptDialogs, adminToken, authHeaders, createUser, importRows, signIn, signOut, studentId, uid,
} from "./helpers.js";

const nav = (page) => page.getByRole("navigation", { name: "Main" });
const card = (page, title) => page.locator("section", { has: page.getByRole("heading", { name: title }) });

/** An at-risk student (a failing score) with no follow-ups yet. */
async function atRiskStudent(request) {
  const name = uid("Risky");
  await importRows(request, [[name, "Math", "2036-1", 30]]);
  return name;
}

test.describe("recording follow-ups (staff)", () => {
  test("from the to-do list to a recorded, completed and edited follow-up", async ({ page, request }) => {
    const name = await atRiskStudent(request);
    const staff = await createUser(request, { role: "staff", prefix: "staff" });
    await signIn(page, staff.username, staff.password);

    // The student is on the "no open follow-up" to-do list
    await nav(page).getByRole("link", { name: "Follow-ups" }).click();
    await expect(page.getByRole("heading", { name: "Follow-ups", exact: true, level: 1 })).toBeVisible();
    const todo = card(page, /^At-risk students with no open follow-up/);
    await expect(todo.getByRole("link", { name })).toBeVisible();
    await todo.getByRole("link", { name }).click();

    // Record a follow-up that is already overdue
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
    await expect(page.getByText("This student is at risk and has no open follow-up.")).toBeVisible();
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await page.getByLabel("Type").selectOption({ label: "Tutoring" });
    await page.getByLabel("Due date (optional)").fill("2020-01-01");
    await page.getByLabel("What was done or is planned").fill("Arranged peer tutoring twice a week.");
    await page.getByRole("button", { name: "Add follow-up" }).click();

    await expect(page.getByRole("heading", { name: "Open (1)" })).toBeVisible();
    await expect(page.getByText("Arranged peer tutoring twice a week.")).toBeVisible();
    await expect(page.getByText("Tutoring", { exact: true })).toBeVisible();
    await expect(page.getByText("Overdue, was due 1 Jan 2020")).toBeVisible();
    await expect(page.getByText(`Added by ${staff.username}`)).toBeVisible();
    await expect(page.getByText("This student is at risk and has no open follow-up.")).toHaveCount(0);

    // The to-do list no longer has them; the open list does, flagged overdue
    await nav(page).getByRole("link", { name: "Follow-ups" }).click();
    await expect(card(page, /^At-risk students with no open follow-up/).getByRole("link", { name })).toHaveCount(0);
    const open = card(page, /^Open follow-ups/);
    await expect(open.locator("tbody tr").filter({ hasText: name })).toContainText("Overdue");
    await page.getByLabel(/Overdue only/).check();
    await expect(open.locator("tbody tr").filter({ hasText: name })).toBeVisible();
    await open.getByRole("link", { name }).click();

    // Edit the note
    await page.getByRole("button", { name: "Edit", exact: true }).click();
    await page.getByLabel("What was done or is planned").fill("Tutoring started; reviewing in two weeks.");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Tutoring started; reviewing in two weeks.")).toBeVisible();

    // Mark done, then reopen
    await page.getByRole("button", { name: "Mark done" }).click();
    await expect(page.getByRole("heading", { name: "Done (1)" })).toBeVisible();
    await expect(page.getByText(/^Done \d/)).toBeVisible();
    await expect(page.getByText("This student is at risk and has no open follow-up.")).toBeVisible();
    await page.getByRole("button", { name: "Reopen" }).click();
    await expect(page.getByRole("heading", { name: "Open (1)" })).toBeVisible();

    // Staff cannot delete
    await expect(page.getByRole("button", { name: "Delete", exact: true })).toHaveCount(0);
  });

  test("an empty note is rejected", async ({ page, request }) => {
    const name = await atRiskStudent(request);
    const staff = await createUser(request, { role: "staff", prefix: "staff" });
    await signIn(page, staff.username, staff.password);
    await page.goto(`/students?search=${name}`);
    await page.getByRole("link", { name }).click();
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await expect(page.getByText("Write a short note about what was done or is planned")).toBeVisible();
  });
});

test.describe("who can do what with follow-ups", () => {
  test("viewers can read follow-ups but not change them", async ({ page, request }) => {
    const name = await atRiskStudent(request);
    const token = await adminToken(request);
    const id = await studentId(request, name);
    const made = await request.post(`${API}/api/students/${id}/interventions`, {
      headers: authHeaders(token),
      data: { kind: "meeting", note: "Met the student on Monday." },
    });
    expect(made.status()).toBe(201);

    const viewer = await createUser(request, { role: "viewer", prefix: "viewer" });
    await signIn(page, viewer.username, viewer.password);
    await page.goto(`/students/${id}`);
    await expect(page.getByText("Met the student on Monday.")).toBeVisible();
    for (const hidden of ["Add follow-up", "Mark done", "Edit", "Delete"]) {
      await expect(page.getByRole("button", { name: hidden, exact: true })).toHaveCount(0);
    }
  });

  test("administrators can delete a follow-up", async ({ page, request }) => {
    const name = await atRiskStudent(request);
    const token = await adminToken(request);
    const id = await studentId(request, name);
    await request.post(`${API}/api/students/${id}/interventions`, {
      headers: authHeaders(token),
      data: { kind: "referral", note: "Referred to learning support." },
    });
    acceptDialogs(page);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students/${id}`);
    await expect(page.getByText("Referred to learning support.")).toBeVisible();
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await expect(page.getByText("No follow-ups recorded yet.")).toBeVisible();
  });

  test("a staff member cannot reach the administrator pages", async ({ page, request }) => {
    const staff = await createUser(request, { role: "staff", prefix: "staff" });
    await signIn(page, staff.username, staff.password);
    await expect(nav(page).getByRole("link", { name: "Users" })).toHaveCount(0);
    await expect(page.getByText("Staff", { exact: true })).toBeVisible();
    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: "No access" })).toBeVisible();
    await signOut(page);
  });
});
