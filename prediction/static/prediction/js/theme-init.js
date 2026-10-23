// Runs before the page is drawn so that there is no flash of the wrong colour theme.
(function () {
  var theme = "light";
  try {
    theme = localStorage.getItem("theme");
    if (theme !== "dark" && theme !== "light") {
      theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
  } catch (e) { theme = "light"; }
  document.documentElement.setAttribute("data-theme", theme);
})();
