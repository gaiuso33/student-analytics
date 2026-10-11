import { expect } from "@playwright/test";
import { ADMIN, API_PORT } from "./constants.js";

export const API = `http://127.0.0.1:${API_PORT}`;
export { ADMIN };

let counter = 0;
/** A short unique word, so every test works with its own data: uid("Zed") -> "Zedk3x9a1". */
export function uid(prefix = "T") {
  counter += 1;
  return `${prefix}${Date.now().toString(36).slice(-5)}${counter}${Math.random().toString(36).slice(2, 4)}`;
}

export async function apiToken(request, username, password) {
  const res = await request.post(`${API}/api/auth/login`, { data: { username, password } });
  expect(res.ok(), `login as ${username}`).toBeTruthy();
  return (await res.json()).token;
}

export const authHeaders = (token) => ({ Authorization: `Bearer ${token}` });

export async function adminToken(request) {
  return apiToken(request, ADMIN.username, ADMIN.password);
}

export async function createUser(request, { role = "viewer", prefix = "user" } = {}) {
  const token = await adminToken(request);
  const username = uid(prefix);
  const password = `${uid("pw")}-long-pass`;
  const res = await request.post(`${API}/api/users`, {
    headers: authHeaders(token),
    data: { username, password, role },
  });
  expect(res.status(), "create user").toBe(201);
  return { username, password };
}

/** Load results through the real import endpoint. rows: [[name, course, semester, score], ...] */
export async function importRows(request, rows) {
  const token = await adminToken(request);
  const csv = ["Student,Course,Semester,Score", ...rows.map((r) => r.join(","))].join("\n");
  const res = await request.post(`${API}/api/import`, { headers: authHeaders(token), data: { csv } });
  expect(res.ok(), "import rows").toBeTruthy();
}

export async function studentId(request, name) {
  const token = await adminToken(request);
  const res = await request.get(`${API}/api/students?search=${encodeURIComponent(name)}`, { headers: authHeaders(token) });
  const rows = await res.json();
  expect(rows.length, `student ${name} exists`).toBeGreaterThan(0);
  return rows[0].student_id;
}

/** Sign in through the real login form and wait for the Overview. */
export async function signIn(page, username, password) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
}

export async function signOut(page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Student analytics" })).toBeVisible();
}

/** Accept the next browser confirm() dialog (delete confirmations). */
export function acceptDialogs(page) {
  page.on("dialog", (dialog) => dialog.accept());
}
