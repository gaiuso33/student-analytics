import { useCallback, useEffect, useMemo, useState } from "react";
import { getToken, request, setToken, setUnauthorizedHandler } from "../api/client";
import { AuthContext } from "./context";

function AuthProvider({ children }) {
  // If a token survived a reload we must check it with the server before showing anything.
  const [state, setState] = useState(() => ({ user: null, status: getToken() ? "loading" : "anon" }));

  const signOut = useCallback(() => {
    setToken(null);
    setState({ user: null, status: "anon" });
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  useEffect(() => {
    if (!getToken()) return undefined;
    const controller = new AbortController();
    request("/api/auth/me", { signal: controller.signal })
      .then(({ user }) => setState({ user, status: "authed" }))
      .catch((err) => {
        if (err.name === "AbortError") return;
        setToken(null);
        setState({ user: null, status: "anon" });
      });
    return () => controller.abort();
  }, []);

  const signIn = useCallback(async (username, password) => {
    const data = await request("/api/auth/login", { method: "POST", body: { username, password } });
    setToken(data.token);
    setState({ user: data.user, status: "authed" });
  }, []);

  /** After a password change the server issues a fresh token (all other sessions are revoked). */
  const updateSession = useCallback(({ token, user }) => {
    setToken(token);
    setState({ user, status: "authed" });
  }, []);

  const value = useMemo(
    () => ({
      ...state,
      isAdmin: state.user?.role === "admin",
      canRecord: state.user?.role === "admin" || state.user?.role === "staff", // may log follow-ups
      signIn,
      signOut,
      updateSession,
    }),
    [state, signIn, signOut, updateSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
