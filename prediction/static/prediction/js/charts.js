// Draws the history line chart and the doctor dashboard doughnut (needs Chart.js from the CDN).
document.addEventListener("DOMContentLoaded", function () {
  function data(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }
  function fallback() {
    document.querySelectorAll(".chart-fallback").forEach(function (el) { el.hidden = false; });
  }

  var history = data("chart-data");
  var risk = data("risk-data");
  if (typeof Chart === "undefined") { if (history || risk) { fallback(); } return; }

  if (history && document.getElementById("history-chart")) {
    new Chart(document.getElementById("history-chart"), {
      type: "line",
      data: {
        labels: history.map(function (d) { return d.label; }),
        datasets: [{
          label: "Probability of heart disease (%)",
          data: history.map(function (d) { return d.p; }),
          borderColor: "#C62828", backgroundColor: "rgba(198,40,40,.12)",
          fill: true, tension: 0.25, pointRadius: 4
        }]
      },
      options: {
        scales: { y: { min: 0, max: 100, title: { display: true, text: "%" } } },
        plugins: { legend: { display: true } }
      }
    });
  }

  if (risk && document.getElementById("risk-chart")) {
    new Chart(document.getElementById("risk-chart"), {
      type: "doughnut",
      data: {
        labels: ["Low", "Moderate", "High"],
        datasets: [{ data: risk, backgroundColor: ["#43A047", "#F9A825", "#E53935"] }]
      },
      options: { plugins: { legend: { position: "bottom" } } }
    });
  }
});
