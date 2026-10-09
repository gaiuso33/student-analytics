// Applies the saved (or system) theme before first paint to avoid a light flash.
// Kept as a separate file so the Content-Security-Policy can forbid inline scripts.
(function () {
  try {
    var t = localStorage.getItem("theme");
    if (t !== "light" && t !== "dark") {
      t = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.dataset.theme = t;
  } catch (e) {}
})();
