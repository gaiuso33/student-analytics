import { useTheme } from "../hooks/useTheme";

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const toDark = theme === "light";

  return (
    <button type="button" className="button--ghost button--small" onClick={toggle}>
      {toDark ? "Dark mode" : "Light mode"}
    </button>
  );
}

export default ThemeToggle;
