(function () {
  "use strict";
  function current() {
    return document.documentElement.getAttribute("data-bs-theme") || "light";
  }
  function updateIcon(t) {
    var b = document.getElementById("themeToggle");
    if (b) b.textContent = t === "dark" ? "☀️" : "🌙";
  }
  function set(t) {
    document.documentElement.setAttribute("data-bs-theme", t);
    try { localStorage.setItem("theme", t); } catch (e) {}
    updateIcon(t);
  }
  document.addEventListener("DOMContentLoaded", function () {
    updateIcon(current());
    var b = document.getElementById("themeToggle");
    if (b) b.addEventListener("click", function () {
      set(current() === "dark" ? "light" : "dark");
    });
  });
})();
