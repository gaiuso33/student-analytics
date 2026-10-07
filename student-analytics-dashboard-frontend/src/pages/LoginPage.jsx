import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle";
import { useAuth } from "../auth/useAuth";

function LoginPage() {
  const { status, signIn } = useAuth();
  const location = useLocation();
  const from = location.state?.from ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  if (status === "authed") return <Navigate to={from} replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }
    setError("");
    setPending(true);
    try {
      await signIn(username.trim(), password);
    } catch (err) {
      setError(err.message);
      setPending(false);
    }
  }

  return (
    <main className="login">
      <form className="card form login__card" onSubmit={handleSubmit} noValidate>
        <h1>Student analytics</h1>
        <p className="state">Sign in to continue.</p>

        <div className="field">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            autoFocus
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>

        {error && <p className="state state--error" role="alert">{error}</p>}
        <button type="submit" disabled={pending}>{pending ? "Signing in…" : "Sign in"}</button>
      </form>
      <div className="login__theme"><ThemeToggle /></div>
    </main>
  );
}

export default LoginPage;
