import { useState } from "react";
import { request } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { roleLabel } from "../utils/roles";
import { validatePassword } from "../utils/validate";

function AccountPage() {
  const { user, updateSession } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setDone(false);
    const problem = validatePassword(next) ?? (next !== confirm ? "The new passwords don't match" : null);
    if (!current) return setError("Enter your current password");
    if (problem) return setError(problem);
    setError("");
    setPending(true);
    try {
      const data = await request("/api/auth/change-password", {
        method: "POST",
        body: { current_password: current, new_password: next },
      });
      updateSession(data); // other sessions are signed out; this one gets a new token
      setCurrent("");
      setNext("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Account</h1>
      </header>

      <section className="card form-card">
        <p>
          Signed in as <strong>{user.username}</strong>{" "}
          <span className="badge badge--ok">{roleLabel(user.role)}</span>
        </p>

        <h2>Change password</h2>
        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="current">Current password</label>
            <input id="current" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          </div>
          <div className="field">
            <label htmlFor="new">New password</label>
            <input id="new" type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          </div>
          <div className="field">
            <label htmlFor="confirm">Repeat new password</label>
            <input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          </div>
          {error && <p className="state state--error" role="alert">{error}</p>}
          {done && <p className="notice" role="status">Password changed. Your other sessions were signed out.</p>}
          <div className="form__actions">
            <button type="submit" disabled={pending}>{pending ? "Saving…" : "Change password"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default AccountPage;
