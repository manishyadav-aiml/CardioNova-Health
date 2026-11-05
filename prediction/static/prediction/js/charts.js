// Draws the history line chart and the doctor dashboard doughnut with the browser's own <canvas>.
// No external library and no network request: the Content-Security-Policy only allows scripts from this site.
(function () {
  "use strict";

  var NS = { drawLine: drawLine, drawDoughnut: drawDoughnut, nearest: nearest };

  /* ---------- helpers ------------------------------------------------------------------------ */
  function cssVar(name, fallback) {
    try {
      var value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return value || fallback;
    } catch (e) { return fallback; }
  }
  function palette() {
    return {
      text: cssVar("--text", "#1c2430"), muted: cssVar("--muted", "#5f6b7a"), line: cssVar("--line", "#dfe4ec"),
      card: cssVar("--card", "#ffffff"), red: cssVar("--red", "#c62828"),
      low: cssVar("--low", "#43a047"), moderate: cssVar("--moderate", "#f9a825"), high: cssVar("--high", "#e53935")
    };
  }
  function readJson(id) {
    var el = document.getElementById(id);
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  // Makes the canvas sharp on high-density screens and returns the CSS size to draw in.
  function fit(canvas, aspect) {
    var width = Math.max(260, Math.floor((canvas.parentNode && canvas.parentNode.clientWidth) || canvas.width || 600));
    var height = Math.round(width / aspect);
    var ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx: ctx, width: width, height: height };
  }
  function every(n, items) {                                    // which x labels to show so they never overlap
    var step = Math.max(1, Math.ceil(items / n));
    return function (i) { return i % step === 0 || i === items - 1; };
  }

  /* ---------- line chart: probability over time ------------------------------------------------ */
  function layoutLine(width, height, count) {
    var box = { left: 44, right: 14, top: 14, bottom: 34 };
    box.w = width - box.left - box.right;
    box.h = height - box.top - box.bottom;
    box.x = function (i) { return box.left + (count === 1 ? box.w / 2 : (i * box.w) / (count - 1)); };
    box.y = function (p) { return box.top + box.h - (Math.max(0, Math.min(100, p)) / 100) * box.h; };
    return box;
  }
  function drawLine(canvas, points, hover) {
    var size = fit(canvas, 3.2), ctx = size.ctx, c = palette();
    var box = layoutLine(size.width, size.height, points.length);
    ctx.clearRect(0, 0, size.width, size.height);
    ctx.font = "12px system-ui, sans-serif";

    ctx.lineWidth = 1; ctx.strokeStyle = c.line; ctx.fillStyle = c.muted; ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (var g = 0; g <= 100; g += 20) {                      // grid and y axis
      var gy = Math.round(box.y(g)) + 0.5;
      ctx.beginPath(); ctx.moveTo(box.left, gy); ctx.lineTo(box.left + box.w, gy); ctx.stroke();
      ctx.fillText(g + "%", box.left - 6, gy);
    }
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    var show = every(6, points.length);
    points.forEach(function (point, i) { if (show(i)) { ctx.fillText(String(point.label), box.x(i), box.top + box.h + 8); } });

    ctx.beginPath();                                          // filled area under the line
    points.forEach(function (point, i) { if (i === 0) { ctx.moveTo(box.x(i), box.y(point.p)); } else { ctx.lineTo(box.x(i), box.y(point.p)); } });
    ctx.lineTo(box.x(points.length - 1), box.top + box.h); ctx.lineTo(box.x(0), box.top + box.h); ctx.closePath();
    ctx.globalAlpha = 0.12; ctx.fillStyle = c.red; ctx.fill(); ctx.globalAlpha = 1;

    ctx.beginPath(); ctx.lineWidth = 2.5; ctx.strokeStyle = c.red; ctx.lineJoin = "round";
    points.forEach(function (point, i) { if (i === 0) { ctx.moveTo(box.x(i), box.y(point.p)); } else { ctx.lineTo(box.x(i), box.y(point.p)); } });
    ctx.stroke();

    points.forEach(function (point, i) {                      // points
      ctx.beginPath(); ctx.arc(box.x(i), box.y(point.p), i === hover ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = i === hover ? c.red : c.card; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = c.red; ctx.stroke();
    });

    if (hover !== undefined && hover !== null && points[hover]) {   // tooltip
      var text = points[hover].label + ": " + Number(points[hover].p).toFixed(1) + "%";
      var tw = ctx.measureText(text).width + 14, tx = Math.min(Math.max(box.x(hover) - tw / 2, 2), size.width - tw - 2);
      var ty = Math.max(box.y(points[hover].p) - 34, 2);
      ctx.fillStyle = c.text; ctx.fillRect(tx, ty, tw, 22);
      ctx.fillStyle = c.card; ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(text, tx + 7, ty + 11);
    }
    return box;
  }
  // index of the point closest to an x position (used for the hover tooltip), or null when too far away
  function nearest(points, x, width) {
    var box = layoutLine(width, 100, points.length), best = null, bestDistance = 28;
    points.forEach(function (point, i) {
      var distance = Math.abs(box.x(i) - x);
      if (distance < bestDistance) { best = i; bestDistance = distance; }
    });
    return best;
  }

  /* ---------- doughnut: patients per risk level -------------------------------------------------- */
  function drawDoughnut(canvas, counts) {
    var size = fit(canvas, 1.9), ctx = size.ctx, c = palette();
    var names = ["Low", "Moderate", "High"], colours = [c.low, c.moderate, c.high];
    var total = counts.reduce(function (a, b) { return a + b; }, 0);
    ctx.clearRect(0, 0, size.width, size.height);
    var radius = Math.min(size.height / 2 - 8, size.width / 4), cx = size.width * 0.3, cy = size.height / 2;
    var start = -Math.PI / 2;
    counts.forEach(function (count, i) {
      if (!count) { return; }
      var end = start + (count / total) * Math.PI * 2;
      ctx.beginPath(); ctx.arc(cx, cy, radius, start, end); ctx.arc(cx, cy, radius * 0.58, end, start, true); ctx.closePath();
      ctx.fillStyle = colours[i]; ctx.fill();
      start = end;
    });
    ctx.fillStyle = c.text; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.font = "bold 22px system-ui, sans-serif"; ctx.fillText(String(total), cx, cy - 6);
    ctx.font = "12px system-ui, sans-serif"; ctx.fillStyle = c.muted; ctx.fillText("records", cx, cy + 14);
    ctx.textAlign = "left";
    names.forEach(function (name, i) {                        // legend
      var y = size.height / 2 - 30 + i * 28, x = size.width * 0.58;
      ctx.fillStyle = colours[i]; ctx.fillRect(x, y - 7, 14, 14);
      ctx.fillStyle = c.text; ctx.font = "14px system-ui, sans-serif";
      ctx.fillText(name + ": " + counts[i] + (total ? " (" + Math.round((counts[i] * 100) / total) + "%)" : ""), x + 22, y);
    });
  }

  /* ---------- wiring --------------------------------------------------------------------------- */
  function fail() {
    Array.prototype.forEach.call(document.querySelectorAll(".chart-fallback"), function (el) { el.hidden = false; });
  }
  function debounce(fn) { var t; return function () { clearTimeout(t); t = setTimeout(fn, 120); }; }
  function init() {
    var history = readJson("chart-data"), risk = readJson("risk-data");
    var lineCanvas = document.getElementById("history-chart"), ringCanvas = document.getElementById("risk-chart");
    try {
      if (history && history.length && lineCanvas && lineCanvas.getContext) {
        var hover = null;
        var render = function () { drawLine(lineCanvas, history, hover); };
        lineCanvas.setAttribute("role", "img");
        lineCanvas.setAttribute("aria-label", "Line chart of the estimated probability of heart disease for each record, from " +
          history[0].label + " to " + history[history.length - 1].label + ".");
        lineCanvas.addEventListener("mousemove", function (event) {
          var rect = lineCanvas.getBoundingClientRect(), index = nearest(history, event.clientX - rect.left, rect.width);
          if (index !== hover) { hover = index; render(); }
        });
        lineCanvas.addEventListener("mouseleave", function () { hover = null; render(); });
        render();
        window.addEventListener("resize", debounce(render));
        new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      }
      if (risk && ringCanvas && ringCanvas.getContext) {
        var renderRing = function () { drawDoughnut(ringCanvas, risk); };
        ringCanvas.setAttribute("role", "img");
        ringCanvas.setAttribute("aria-label", "Patients by risk level: low " + risk[0] + ", moderate " + risk[1] + ", high " + risk[2] + ".");
        renderRing();
        window.addEventListener("resize", debounce(renderRing));
        new MutationObserver(renderRing).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      }
    } catch (e) { fail(); }
  }

  if (typeof module !== "undefined" && module.exports) { module.exports = NS; return; }   // used by the Node test
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); } else { init(); }
})();
