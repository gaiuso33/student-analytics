// Shared by playwright.config.js and the tests. These ports differ from the dev servers
// (5000 / 5173) so the tests never touch your own running app or database.
export const API_PORT = 5100;
export const WEB_PORT = 5273;
export const ADMIN = { username: "admin", password: "e2e-admin-password-1" };
