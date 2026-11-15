import { test, expect } from "@playwright/test";
import {
  ADMIN, addFollowUp, addResult, createUser, importCsv, signIn, studentId, uid,
} from "./helpers.js";

const HEADER = "Student,Student ID,Class,Course,Semester,Score\n";

test.describe("student IDs", () => {
  test("two students with the same name are told apart by their IDs", async ({ page, request }) => {
    const tag = uid("Twin");
    const name = `${tag} Sam`;
    await signIn(page, ADMIN.username, ADMIN.password);

    for (const [code, klass] of [[`${tag}-1`, "7A"], [`${tag}-2`, "7B"]]) {
      await page.goto("/students/new");
      await page.getByLabel("Student name").fill(name);
      await page.getByLabel("Student ID (optional)").fill(code);
      await page.getByLabel("Class (optional)").fill(klass);
      await page.getByRole("button", { name: "Create student" }).click();
      await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
      await expect(page.getByText(`Student ID ${code}`)).toBeVisible();
      await expect(page.getByText(`Class ${klass}`)).toBeVisible();
      const id = Number(page.url().split("/").pop());
      await addResult(request, id);
    }

    await page.goto(`/students?search=${encodeURIComponent(name)}`);
    await expect(page.getByText(/Showing 2 of/)).toBeVisible();
    await expect(page.locator("tbody tr").filter({ hasText: `${tag}-1` })).toContainText("7A");
    await expect(page.locator("tbody tr").filter({ hasText: `${tag}-2` })).toContainText("7B");

    await page.getByLabel("Search").fill(`${tag}-2`);
    await expect(page.getByText(/Showing 1 of/)).toBeVisible();

    // A third Sam with no ID could be either of them: refused, with the reason
    await page.goto("/students/new");
    await page.getByLabel("Student name").fill(name);
    await page.getByRole("button", { name: "Create student" }).click();
    await expect(page.getByRole("alert")).toContainText("student ID to tell them apart");
  });

  test("a student ID can only be used once", async ({ page, request }) => {
    const tag = uid("Dup");
    await importCsv(request, `${HEADER}${tag} Owner,${tag}-ID,,Math,2036-1,70\n`);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/students/new");
    await page.getByLabel("Student name").fill(`${tag} Other`);
    await page.getByLabel("Student ID (optional)").fill(`${tag}-id`);
    await page.getByRole("button", { name: "Create student" }).click();
    await expect(page.getByRole("alert")).toContainText("student ID is already in use");
  });

  test("an invalid ID is caught before anything is sent", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/students/new");
    await page.getByLabel("Student name").fill("Someone Valid");
    await page.getByLabel("Student ID (optional)").fill("not valid!");
    await page.getByRole("button", { name: "Create student" }).click();
    await expect(page.getByRole("alert")).toContainText("Student ID can use letters, numbers");
  });

  test("an ID and class can be added to an existing student", async ({ page, request }) => {
    const name = uid("Later");
    await importCsv(request, `Student,Course,Semester,Score\n${name},Math,2036-1,70\n`);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${name}`);
    await page.getByRole("link", { name }).click();
    await expect(page.getByText("No student ID")).toBeVisible();
    await expect(page.getByText("No class")).toBeVisible();

    await page.getByRole("button", { name: "Rename" }).click();
    await page.getByLabel("Student ID (optional)").fill(`${name}-ID`);
    await page.getByLabel("Class (optional)").fill("8C");
    await page.getByRole("button", { name: "Save name" }).click();
    await expect(page.getByText(`Student ID ${name}-ID`)).toBeVisible();
    await expect(page.getByText("Class 8C")).toBeVisible();
  });
});

test.describe("importing IDs and classes", () => {
  test("the preview says what will change, and the import adds IDs to existing students", async ({ page, request }) => {
    const name = uid("Adopt");
    await importCsv(request, `Student,Course,Semester,Score\n${name},Math,2036-1,70\n`);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/import");
    await page.getByLabel("CSV file").setInputFiles({
      name: "ids.csv", mimeType: "text/csv",
      buffer: Buffer.from(`${HEADER}${name},${name}-ID,9Z,English,2036-1,81\n`),
    });
    await expect(page.getByText("1 student ID to add to existing students")).toBeVisible();
    await expect(page.getByText("1 student moved to a different class")).toBeVisible();
    await page.getByRole("button", { name: "Import 1 result" }).click();
    await expect(page.getByText(/1 student ID added\./)).toBeVisible();

    await page.goto(`/students?search=${name}-ID`);
    await expect(page.locator("tbody tr").first()).toContainText("9Z");
  });

  test("a name shared by several students is never guessed", async ({ page, request }) => {
    const tag = uid("Share");
    await importCsv(request, `${HEADER}${tag} Pat,${tag}-1,,Math,2036-1,70\n${tag} Pat,${tag}-2,,Math,2036-1,60\n`);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/import");
    await page.getByLabel("CSV file").setInputFiles({
      name: "names.csv", mimeType: "text/csv",
      buffer: Buffer.from(`Student,Course,Semester,Score\n${tag} Pat,English,2036-1,75\n`),
    });
    await expect(page.getByText("1 row can't be imported.", { exact: false })).toBeVisible();
    await expect(page.getByRole("table").getByText(`Several students are called ${tag} Pat`)).toBeVisible();
    await expect(page.getByRole("button", { name: /^Import \d/ })).toHaveCount(0);
  });
});

test.describe("classes", () => {
  test("the Students page can be narrowed to one class", async ({ page, request }) => {
    const tag = uid("Cls");
    const [a, b] = [`${tag}A`, `${tag}B`];
    await importCsv(request, `${HEADER}${tag} Ann,,${a},Math,2036-1,70\n${tag} Ben,,${b},Math,2036-1,80\n`);
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto(`/students?search=${tag}`);
    await expect(page.getByText(/Showing 2 of/)).toBeVisible();
    await page.getByLabel("Class").selectOption(a);
    await expect(page.getByText(/Showing 1 of/)).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Ann` })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`class=${a}`));
    await page.getByLabel("Class").selectOption("");
    await page.getByLabel("Search").fill(b);                // the search box also finds classes
    await expect(page.getByRole("link", { name: `${tag} Ben` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Ann` })).toHaveCount(0);
  });
});

test.describe("a teacher limited to some classes", () => {
  test("sees only their own classes, everywhere", async ({ page, request }) => {
    const tag = uid("Lim");
    const [mine, other] = [`${tag}A`, `${tag}B`];
    await importCsv(request, `${HEADER}${tag} Mine,,${mine},Math,2036-1,30\n${tag} Theirs,,${other},Math,2036-1,35\n`);
    const theirId = await studentId(request, `${tag} Theirs`);
    await addFollowUp(request, theirId, { note: "Not for this teacher.", assigned_to: null });
    const teacher = await createUser(request, { role: "staff", prefix: "teacher", scope: "classes", classes: [mine] });

    await signIn(page, teacher.username, teacher.password);
    await expect(page.getByRole("note")).toContainText(`You can see students in these classes: ${mine}`);

    await page.goto(`/students?search=${tag}`);
    await expect(page.getByRole("link", { name: `${tag} Mine` })).toBeVisible();
    await expect(page.getByRole("link", { name: `${tag} Theirs` })).toHaveCount(0);
    const options = await page.getByLabel("Class").locator("option").allTextContents();
    expect(options).toEqual(["All classes", mine]);

    // Typing the address of a student from another class gets the same answer as a student that doesn't exist
    await page.goto(`/students/${theirId}`);
    await expect(page.getByText("This student could not be found.")).toBeVisible();

    await page.goto("/interventions");
    await expect(page.getByText("Not for this teacher.")).toHaveCount(0);
    await expect(page.locator("tbody tr").filter({ hasText: `${tag} Theirs` })).toHaveCount(0);
  });

  test("an administrator changes what they can see, and it applies at once", async ({ page, request, browser }) => {
    const tag = uid("Acc");
    const [a, b] = [`${tag}A`, `${tag}B`];
    await importCsv(request, `${HEADER}${tag} One,,${a},Math,2036-1,70\n${tag} Two,,${b},Math,2036-1,80\n`);
    const teacher = await createUser(request, { role: "staff", prefix: "access" });   // starts with access to everyone

    const other = await browser.newContext();
    const teacherPage = await other.newPage();
    await signIn(teacherPage, teacher.username, teacher.password);
    await teacherPage.goto(`/students?search=${tag}`);
    await expect(teacherPage.getByText(/Showing 2 of/)).toBeVisible();

    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");
    const row = page.getByRole("row", { name: new RegExp(teacher.username) });
    await expect(row).toContainText("All students");
    await row.getByRole("button", { name: /Edit access/ }).click();
    await page.getByLabel("Only students in these classes").check();
    await page.getByLabel(a, { exact: true }).check();
    await page.getByRole("button", { name: "Save access" }).click();
    await expect(row).toContainText(`Classes: ${a}`);

    await teacherPage.reload();
    await expect(teacherPage.getByText(/Showing 1 of/)).toBeVisible();
    await expect(teacherPage.getByRole("link", { name: `${tag} Two` })).toHaveCount(0);

    await row.getByRole("button", { name: /Edit access/ }).click();
    await page.getByLabel("All students", { exact: true }).check();
    await page.getByRole("button", { name: "Save access" }).click();
    await expect(row).toContainText("All students");
    await teacherPage.reload();
    await expect(teacherPage.getByText(/Showing 2 of/)).toBeVisible();
    await other.close();
  });

  test("administrators have no access setting, because they always see everyone", async ({ page }) => {
    await signIn(page, ADMIN.username, ADMIN.password);
    await page.goto("/admin/users");
    const adminRow = page.getByRole("row", { name: new RegExp(`^${ADMIN.username}\\b`) });
    await expect(adminRow).toContainText("All students");
    await expect(adminRow.getByRole("button")).toHaveCount(0);
  });
});
