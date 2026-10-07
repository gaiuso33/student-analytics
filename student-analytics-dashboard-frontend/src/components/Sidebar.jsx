import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

const LINKS = [
  { to: "/", label: "Overview", end: true },
  { to: "/students", label: "Students" },
  { to: "/courses", label: "Courses" },
];

function Sidebar() {
  const { pathname } = useLocation();
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

      <nav id="main-nav" aria-label="Main" className={open ? "is-open" : ""}>
        <ul>
          {LINKS.map(({ to, label, end }) => (
            <li key={to}>
              <NavLink to={to} end={end}>{label}</NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

export default Sidebar;
