import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { roleLabel } from "../utils/roles";
import ThemeToggle from "./ThemeToggle";

const LINKS = [
  { to: "/", label: "Overview", end: true },
  { to: "/students", label: "Students" },
  { to: "/courses", label: "Courses" },
  { to: "/interventions", label: "Follow-ups" },
];
const ADMIN_LINKS = [
  { to: "/admin/import", label: "Import data" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/audit", label: "Audit log" },
];
const ACCOUNT_LINK = { to: "/account", label: "Account" };

function Sidebar() {
  const { pathname } = useLocation();
  const { user, isAdmin, signOut } = useAuth();
  // The menu is "open" only for the page it was opened on, so navigating closes it automatically.
  const [openAt, setOpenAt] = useState(null);
  const open = openAt === pathname;

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") setOpenAt(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const links = [...LINKS, ...(isAdmin ? ADMIN_LINKS : []), ACCOUNT_LINK];

  return (
    <aside className="sidebar">
      <div className="sidebar__top">
        <h2>Analytics</h2>
        <div className="sidebar__actions">
          <ThemeToggle />
          <button
            type="button"
            className="button--ghost button--small sidebar__menu"
            aria-expanded={open}
            aria-controls="main-nav"
            onClick={() => setOpenAt(open ? null : pathname)}
          >
            {open ? "Close" : "Menu"}
          </button>
        </div>
      </div>

      <div id="main-nav" className={`sidebar__panel${open ? " is-open" : ""}`}>
        <nav aria-label="Main">
          <ul>
            {links.map(({ to, label, end }) => (
              <li key={to}>
                <NavLink to={to} end={end}>{label}</NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar__user">
          <p>
            <strong>{user.username}</strong>
            <br />
            <span>{roleLabel(user.role)}</span>
          </p>
          <button type="button" className="button--ghost button--small" onClick={signOut}>
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
