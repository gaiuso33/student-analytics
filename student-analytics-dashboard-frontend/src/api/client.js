const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN_KEY = "auth_token";

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.field = details?.field;
  }
}

// The login token lives in sessionStorage: it is cleared when the tab closes.
export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable: the session just won't survive a reload
  }
}

let onUnauthorized = null;
/** Called when the server rejects our token (expired, revoked, account disabled). */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

export async function request(path, { method = "GET", body, signal } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }

  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no JSON body
  }

  if (!res.ok) {
    if (res.status === 401 && token && onUnauthorized) onUnauthorized();
    throw new ApiError(data?.message ?? `Request failed (${res.status})`, res.status, data);
  }
  if (data === null) throw new ApiError("The server returned an unreadable response.", res.status);
  return data;
}

export const fetchJson = (path, options) => request(path, options);
