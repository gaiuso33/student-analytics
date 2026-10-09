import { Outlet } from "react-router-dom";
import { useAuth } from "./useAuth";

/** Hides admin-only pages from viewers. The server enforces this too; this just gives a clear message. */
function RequireAdmin() {
  const { isAdmin } = useAuth();
  if (!isAdmin) {
    return (
      <div className="page">
        <h1>No access</h1>
        <p>This page is for administrators only.</p>
      </div>
    );
  }
  return <Outlet />;
}

export default RequireAdmin;
