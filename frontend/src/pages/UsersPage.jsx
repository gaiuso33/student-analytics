import { useId, useState } from "react";
import { request } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { roleLabel } from "../utils/roles";
import { validatePassword, validateUsername } from "../utils/validate";

function CreateUserForm({ onCreated }) {
  const [values, setValues] = useState({ username: "", password: "", role: "viewer" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const uid = useId();
  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    const problem = validateUsername(values.username) ?? validatePassword(values.password);
    if (problem) return setError(problem);
    setError("");
    setPending(true);
    try {
      await request("/api/users", {
        method: "POST",
        body: { username: values.username.trim(), password: values.password, role: values.role },
      });
      setValues({ username: "", password: "", role: "viewer" });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="form form--inline" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor={`${uid}-u`}>Username</label>
        <input id={`${uid}-u`} value={values.username} onChange={set("username")} autoComplete="off" autoCapitalize="none" />
      </div>
      <div className="field">
        <label htmlFor={`${uid}-p`}>Temporary password</label>
        <input id={`${uid}-p`} type="password" value={values.password} onChange={set("password")} autoComplete="new-password" />
      </div>
      <div className="field">
        <label htmlFor={`${uid}-r`}>Role</label>
        <select id={`${uid}-r`} value={values.role} onChange={set("role")}>
          <option value="viewer">Viewer (read only)</option>
          <option value="staff">Staff (can record follow-ups)</option>
          <option value="admin">Administrator (everything)</option>
        </select>
      </div>
      <div className="form__actions">
        <button type="submit" disabled={pending}>{pending ? "Creating…" : "Create user"}</button>
      </div>
      {error && <p className="state state--error form__error" role="alert">{error}</p>}
    </form>
  );
}

function ResetPasswordForm({ username, onSubmit, onCancel }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const id = useId();

  async function handleSubmit(e) {
    e.preventDefault();
    const problem = validatePassword(password);
    if (problem) return setError(problem);
    setPending(true);
    try {
      await onSubmit(password);
    } catch (err) {
      setError(err.message);
      setPending(false);
    }
  }

  return (
    <form className="form form--inline" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor={id}>New password for {username}</label>
        <input id={id} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" autoFocus />
        {error && <p className="field__error" role="alert">{error}</p>}
      </div>
      <div className="form__actions">
        <button type="submit" disabled={pending}>Set password</button>
        <button type="button" className="button--ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function UsersPage() {
  const { user: me } = useAuth();
  const { data, loading, error, refetch } = useFetch("/api/users");
  const [actionError, setActionError] = useState("");
  const [resettingId, setResettingId] = useState(null);
  const users = data ?? [];

  async function patch(user, body) {
    setActionError("");
    try {
      await request(`/api/users/${user.id}`, { method: "PATCH", body });
      refetch();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function resetPassword(user, password) {
    await request(`/api/users/${user.id}`, { method: "PATCH", body: { password } });
    setResettingId(null);
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Users</h1>
      </header>

      <section className="card form-card">
        <h2>Add a user</h2>
        <CreateUserForm onCreated={refetch} />
      </section>

      {actionError && <p className="state state--error" role="alert">{actionError}</p>}
      {loading && <p className="state">Loading users…</p>}
      {error && (
        <div className="state state--error" role="alert">
          <p>{error.message}</p>
          <button type="button" onClick={refetch}>Try again</button>
        </div>
      )}

      {data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Username</th><th>Role</th><th>Status</th><th>Created</th><th><span className="visually-hidden">Actions</span></th></tr>
            </thead>
            <tbody>
              {users.map((u) =>
                resettingId === u.id ? (
                  <tr key={u.id}>
                    <td colSpan={5}>
                      <ResetPasswordForm
                        username={u.username}
                        onSubmit={(pw) => resetPassword(u, pw)}
                        onCancel={() => setResettingId(null)}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr key={u.id}>
                    <td>
                      {u.username}
                      {u.id === me.id && <span className="badge badge--ok badge--small">You</span>}
                    </td>
                    <td>
                      {u.id === me.id ? (
                        roleLabel(u.role)
                      ) : (
                        <select
                          aria-label={`Role for ${u.username}`}
                          value={u.role}
                          onChange={(e) => patch(u, { role: e.target.value })}
                        >
                          <option value="viewer">Viewer</option>
                          <option value="staff">Staff</option>
                          <option value="admin">Administrator</option>
                        </select>
                      )}
                    </td>
                    <td>{u.active ? "Active" : "Deactivated"}</td>
                    <td>{u.created_at}</td>
                    <td className="row-actions">
                      {u.id !== me.id && (
                        <>
                          <button type="button" className="button--ghost button--small" onClick={() => setResettingId(u.id)}>
                            Reset password
                          </button>
                          <button
                            type="button"
                            className={`button--ghost button--small${u.active ? " button--danger" : ""}`}
                            onClick={() => patch(u, { active: !u.active })}
                          >
                            {u.active ? "Deactivate" : "Reactivate"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default UsersPage;
