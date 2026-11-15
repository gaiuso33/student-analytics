import { test, expect } from "@playwright/test";
import { ADMIN, addFollowUp, createUser, importRows, isoDay, signIn, studentId, uid } from "./helpers.js";

const nav = (page) => page.getByRole("navigation", { name: "Main" });

async function atRiskStudent(request) {
  const name = uid("Rem");
  await importRows(request, [[name, "Math", "2038-1", 30]]);
  return { name, id: await studentId(request, name) };
}

test.describe("what needs my attention", () => {
  test("the overview card, the menu badge and the 'assigned to me' view agree", async ({ page, request }) => {
    const { name, id } = await atRiskStudent(request);
    const staff = await createUser(request, { role: "staff", prefix: "staff" });
    await addFollowUp(request, id, { assigned_to: staff.username, due_date: isoDay(-3) });   // overdue
    await addFollowUp(request, id, { assigned_to: staff.username, due_date: isoDay(0) });    // due today
    await addFollowUp(request, id, { assigned_to: staff.username, due_date: isoDay(10) });   // later: not urgent

    await signIn(page, staff.username, staff.password);
    const card = page.locator("section", { has: page.getByRole("heading", { name: "Your follow-ups" }) });
    await expect(card.locator(".reminder-counts")).toContainText("1 overdue");
    await expect(card.locator(".reminder-counts")).toContainText("1 due soon");
    await expect(card.getByRole("link", { name }).first()).toBeVisible();
    await expect(card.getByText(/Overdue, was due/)).toBeVisible();
    await expect(card.getByText(/Due today/)).toBeVisible();
    await expect(nav(page).getByRole("link", { name: /Follow-ups.*2 need your attention/ })).toBeVisible();

    await card.getByRole("link", { name: "See all my follow-ups" }).click();
    await expect(page.getByLabel("Show")).toHaveValue("mine");
    const rows = page.locator("tbody tr").filter({ hasText: name });
    await expect(rows).toHaveCount(3);
    await expect(rows.filter({ hasText: "Overdue" })).toHaveCount(1);
    await expect(rows.filter({ hasText: "Due soon" })).toHaveCount(1);

    await page.getByLabel("Show").selectOption("attention");
    await expect(page.locator("tbody tr").filter({ hasText: name })).toHaveCount(2);
    await page.getByLabel("Show").selectOption("all");
    await expect(page.locator("tbody tr").filter({ hasText: name })).toHaveCount(3);
  });

  test("with nothing urgent, the card says so and there is no badge", async ({ page, request }) => {
    const { id } = await atRiskStudent(request);
    const staff = await createUser(request, { role: "staff", prefix: "calm" });
    await addFollowUp(request, id, { assigned_to: staff.username, due_date: isoDay(30) });

    await signIn(page, staff.username, staff.password);
    await expect(page.getByText(/Nothing of yours is overdue or due in the next 2 days/)).toBeVisible();
    await expect(page.getByText("You have 1 open in total.")).toBeVisible();
    await expect(nav(page).getByRole("link", { name: /need your attention/ })).toHaveCount(0);
  });

  test("the 'assigned to me' view only lists my follow-ups", async ({ page, request }) => {
    const { name, id } = await atRiskStudent(request);
    const mine = await createUser(request, { role: "staff", prefix: "mine" });
    const other = await createUser(request, { role: "staff", prefix: "other" });
    await addFollowUp(request, id, { assigned_to: mine.username, note: "Mine to do." });
    await addFollowUp(request, id, { assigned_to: other.username, note: "Theirs to do." });
    await addFollowUp(request, id, { assigned_to: null, note: "Nobody has this." });

    await signIn(page, mine.username, mine.password);
    await page.goto("/interventions");
    const rows = page.locator("tbody tr").filter({ hasText: name });
    await expect(rows).toHaveCount(3);
    await page.getByLabel("Show").selectOption("mine");
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toContainText(mine.username);
    await page.getByLabel("Show").selectOption("all");
    await expect(rows.filter({ hasText: "Nobody" })).toHaveCount(1);
  });
});

test.describe("giving a follow-up an owner", () => {
  test("it starts with me, can go to a colleague, and shows in their reminders", async ({ page, request, browser }) => {
    const { id } = await atRiskStudent(request);
    const a = await createUser(request, { role: "staff", prefix: "ownerA" });
    const b = await createUser(request, { role: "staff", prefix: "ownerB" });

    await signIn(page, a.username, a.password);
    await page.goto(`/students/${id}`);
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await expect(page.getByLabel("Assigned to")).toHaveValue(a.username);
    await page.getByLabel("Assigned to").selectOption(b.username);
    await page.getByLabel("Due date (optional)").fill(isoDay(0));
    await page.getByLabel("What was done or is planned").fill("Please call the guardian today.");
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await expect(page.getByText(`Assigned to ${b.username}.`)).toBeVisible();
    await expect(page.getByText(/Due today/)).toBeVisible();

    // The colleague sees it on their own overview, the person who recorded it does not
    const other = await browser.newContext();
    const bPage = await other.newPage();
    await signIn(bPage, b.username, b.password);
    await expect(bPage.locator(".reminder-counts")).toContainText("1 due soon");
    await other.close();
    await page.goto("/");
    await expect(page.getByText(/Nothing of yours is overdue/)).toBeVisible();
  });

  test("'Nobody' is a choice, and an owner can be changed later", async ({ page, request }) => {
    const { id } = await atRiskStudent(request);
    const a = await createUser(request, { role: "staff", prefix: "ownA" });
    const b = await createUser(request, { role: "staff", prefix: "ownB" });
    await signIn(page, a.username, a.password);
    await page.goto(`/students/${id}`);

    await page.getByRole("button", { name: "Add follow-up" }).click();
    await page.getByLabel("Assigned to").selectOption({ label: "Nobody (anyone can pick it up)" });
    await page.getByLabel("What was done or is planned").fill("Someone should look at this.");
    await page.getByRole("button", { name: "Add follow-up" }).click();
    await expect(page.getByText("Not assigned.")).toBeVisible();

    await page.getByRole("button", { name: "Edit", exact: true }).click();
    await expect(page.getByLabel("Assigned to")).toHaveValue("");
    await page.getByLabel("Assigned to").selectOption(b.username);
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText(`Assigned to ${b.username}.`)).toBeVisible();
  });

  test("viewers get no reminders and cannot be chosen as owners", async ({ page, request }) => {
    const { id } = await atRiskStudent(request);
    const viewer = await createUser(request, { role: "viewer", prefix: "viewer" });
    const staff = await createUser(request, { role: "staff", prefix: "pick" });

    await signIn(page, viewer.username, viewer.password);
    await expect(page.getByRole("heading", { name: "Your follow-ups" })).toHaveCount(0);
    await expect(nav(page).getByRole("link", { name: /need your attention/ })).toHaveCount(0);
    await page.goto("/account");
    await expect(page.getByRole("heading", { name: "Reminder emails" })).toHaveCount(0);

    // a staff member's list of possible owners does not include the viewer
    await page.context().clearCookies();
    await page.evaluate(() => sessionStorage.clear());
    await signIn(page, staff.username, staff.password);
    await page.goto(`/students/${id}`);
    await page.getByRole("button", { name: "Add follow-up" }).click();
    const options = await page.getByLabel("Assigned to").locator("option").allTextContents();
    expect(options.some((text) => text.includes(viewer.username))).toBe(false);
    expect(options.some((text) => text.includes(staff.username))).toBe(true);
  });
});

test.describe("reminder emails", () => {
  test("staff can set, correct and remove their address", async ({ page, request }) => {
    const staff = await createUser(request, { role: "staff", prefix: "mail" });
    await signIn(page, staff.username, staff.password);
    await nav(page).getByRole("link", { name: "Account" }).click();
    await expect(page.getByRole("heading", { name: "Reminder emails" })).toBeVisible();

    await page.getByLabel("Email address (optional)").fill("not an address");
    await page.getByRole("button", { name: "Save email" }).click();
    await expect(page.getByRole("alert")).toHaveText("Enter a valid email address");

    await page.getByLabel("Email address (optional)").fill("  Staff.Person@School.ORG ");
    await page.getByRole("button", { name: "Save email" }).click();
    await expect(page.getByRole("status")).toHaveText("Email saved.");
    await expect(page.getByLabel("Email address (optional)")).toHaveValue("staff.person@school.org");

    await page.reload();
    await expect(page.getByLabel("Email address (optional)")).toHaveValue("staff.person@school.org");

    await page.getByLabel("Email address (optional)").fill("");
    await page.getByRole("button", { name: "Save email" }).click();
    await expect(page.getByRole("status")).toContainText("Email removed");
    await page.reload();
    await expect(page.getByLabel("Email address (optional)")).toHaveValue("");
  });

  test("an administrator can add an address when creating a user, and it is listed", async ({ page }) => {
    const username = uid("withmail");
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Temporary password").fill("a-long-password-1");
    await page.getByLabel("Email (optional, for reminders)").fill("Teacher@School.org");
    await page.getByLabel("Role", { exact: true }).selectOption({ label: "Staff (can record follow-ups)" });
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByRole("row", { name: new RegExp(username) })).toContainText("teacher@school.org");
  });
});
