const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function fetchJson(path, { signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { signal });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  if (!res.ok) {
    throw new ApiError(`Request failed (${res.status})`, res.status);
  }
  try {
    return await res.json();
  } catch {
    throw new ApiError("The server returned an unreadable response.", res.status);
  }
}
