import { useEffect, useState } from "react";

const KEY = "theme";

function readInitial() {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // storage unavailable (private mode etc.): fall back to the system setting
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Light/dark theme. Only an explicit toggle is saved, so unset users keep following the system. */
export function useTheme() {
  const [theme, setTheme] = useState(readInitial);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // ignore: the theme still changes for this session
    }
  }

  return { theme, toggle };
}
