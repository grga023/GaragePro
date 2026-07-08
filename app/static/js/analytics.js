(function () {
  "use strict";
  var el = document.getElementById("chartData");
  if (!el || typeof Chart === "undefined") return;

  var d;
  try { d = JSON.parse(el.textContent); } catch (e) { return; }
  var cur = d.currency || "RSD";

  var isDark = document.documentElement.getAttribute("data-bs-theme") === "dark";
  Chart.defaults.color = isDark ? "#ccc" : "#666";
  Chart.defaults.borderColor = isDark ? "rgba(255,255,255,.1)" : "rgba(0,0,0,.1)";

  function money(v) {
    return Number(v || 0).toLocaleString("sr-RS", { maximumFractionDigits: 0 }) + " " + cur;
  }
  var moneyTick = { callback: function (v) { return money(v); } };
  function tip(axis) {
    return { callbacks: { label: function (c) {
      var val = axis === "x" ? c.parsed.x : (c.parsed.y !== undefined ? c.parsed.y : c.parsed);
      return (c.dataset && c.dataset.label ? c.dataset.label + ": " : (c.label ? c.label + ": " : "")) + money(val);
    } } };
  }

  var elTime = document.getElementById("chTime");
  if (elTime) {
    new Chart(elTime, {
      data: {
        labels: d.labels,
        datasets: [
          { type: "bar", label: "Promet", data: d.revenue,
            backgroundColor: "rgba(13,110,253,.5)", borderColor: "#0d6efd" },
          { type: "line", label: "Profit", data: d.profit,
            borderColor: "#198754", backgroundColor: "rgba(25,135,84,.2)", tension: 0.3 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: true,
        scales: { y: { ticks: moneyTick } },
        plugins: { tooltip: tip("y") } }
    });
  }

  var elStruct = document.getElementById("chStruct");
  if (elStruct) {
    new Chart(elStruct, {
      type: "doughnut",
      data: { labels: d.structure.labels,
              datasets: [{ data: d.structure.data, backgroundColor: ["#0d6efd", "#ffc107"] }] },
      options: { plugins: { tooltip: tip() } }
    });
  }

  var elParts = document.getElementById("chParts");
  if (elParts) {
    new Chart(elParts, {
      type: "bar",
      data: { labels: d.parts.labels,
              datasets: [{ label: "Iznos", data: d.parts.data,
                           backgroundColor: ["#0d6efd", "#dc3545", "#198754"] }] },
      options: { scales: { y: { ticks: moneyTick } },
                 plugins: { legend: { display: false }, tooltip: tip("y") } }
    });
  }

  if (d.byworker) {
    var elW = document.getElementById("chWorker");
    if (elW) {
      new Chart(elW, {
        type: "bar",
        data: { labels: d.byworker.labels,
                datasets: [{ label: "Profit", data: d.byworker.data, backgroundColor: "#198754" }] },
        options: { indexAxis: "y", scales: { x: { ticks: moneyTick } },
                   plugins: { legend: { display: false }, tooltip: tip("x") } }
      });
    }
  }
})();
