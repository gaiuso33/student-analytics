import { useState } from "react";
import { request } from "../api/client";
import { useAuth } from "../auth/useAuth";

/** Where reminder emails go. Shown to staff and administrators; leaving it blank turns the emails off. */
function EmailSettings() {
  const { user, refreshUser } = useAuth();
  const [email, setEmail] = useState(user.email ?? "");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setPending(true);
    try {
      const data = await request("/api/auth/me", { method: "PATCH", body: { email } });
      refreshUser(data.user);
      setEmail(data.user.email ?? "");
      setMessage(data.user.email ? "Email saved." : "Email removed. You won't get reminder emails.");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="card form-card">
      <h2>Reminder emails</h2>
      <p>
        If your school has set up email, you get a short message when follow-ups assigned to you are overdue or due soon.
        It says how many there are and links to the dashboard; it never contains notes. Leave the address blank to turn
        these emails off.
      </p>
      <form className="form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="reminder-email">Email address (optional)</label>
          <input
            id="reminder-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            aria-invalid={Boolean(error)}
          />
        </div>
        {error && <p className="state state--error" role="alert">{error}</p>}
        {message && <p className="notice" role="status">{message}</p>}
        <div className="form__actions form__actions--flush">
          <button type="submit" disabled={pending}>{pending ? "Saving…" : "Save email"}</button>
        </div>
      </form>
    </section>
  );
}

export default EmailSettings;
