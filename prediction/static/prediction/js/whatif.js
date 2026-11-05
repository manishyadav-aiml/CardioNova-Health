// What-if simulator on the result page. Sends ONLY the changed values; the server reads the patient's data from the database.
(function () {
  "use strict";
  var box = document.getElementById("whatif");
  if (!box) { return; }

  var url = box.getAttribute("data-url");
  var meta = document.querySelector('meta[name="csrf-token"]');
  var token = meta ? meta.getAttribute("content") : "";
  var before = parseFloat(box.getAttribute("data-before"));
  var inputs = Array.prototype.slice.call(box.querySelectorAll("[data-feature]"));
  var after = document.getElementById("wi-after");
  var delta = document.getElementById("wi-delta");
  var level = document.getElementById("wi-level");
  var errorBox = document.getElementById("wi-error");
  var original = { text: after.textContent, level: level.textContent, cls: level.className };
  var timer = null, counter = 0;

  function valueOf(el) { return el.type === "checkbox" ? (el.checked ? 1 : 0) : Number(el.value); }
  function changes() {
    var out = {};
    inputs.forEach(function (el) {
      var v = valueOf(el);
      if (v !== Number(el.getAttribute("data-start"))) { out[el.getAttribute("data-feature")] = v; }
    });
    return out;
  }
  function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
  function render(data) {
    errorBox.hidden = true;
    after.textContent = data.after.toFixed(1) + "%";
    var change = Math.round((data.after - before) * 10) / 10;
    delta.textContent = (change > 0 ? "+" : "") + change.toFixed(1) + " points";
    delta.className = "wi-delta " + (change > 0 ? "up" : change < 0 ? "down" : "");
    level.textContent = data.risk_level;
    level.className = "badge badge-" + data.risk_level.toLowerCase();
  }
  function showOriginal() {
    errorBox.hidden = true;
    after.textContent = original.text; delta.textContent = "no change"; delta.className = "wi-delta";
    level.textContent = original.level; level.className = original.cls;
  }
  function request() {
    var body = changes();
    if (!Object.keys(body).length) { showOriginal(); return; }
    var mine = ++counter;
    after.classList.add("is-loading");
    fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ changes: body })
    }).then(function (response) {
      return response.json().then(function (json) { return { ok: response.ok, json: json }; });
    }).then(function (result) {
      if (mine !== counter) { return; }                       // an newer request is already on its way
      after.classList.remove("is-loading");
      if (result.ok) { render(result.json); } else { showError(result.json.error || "The estimate could not be calculated."); }
    }).catch(function () {
      if (mine !== counter) { return; }
      after.classList.remove("is-loading");
      showError("Could not reach the server. Check your connection and try again.");
    });
  }

  inputs.forEach(function (el) {
    el.addEventListener("input", function () {
      var out = box.querySelector("#wi-" + el.getAttribute("data-feature") + "-out");
      if (out) { out.textContent = el.value; }
      clearTimeout(timer);
      timer = setTimeout(request, 250);                        // wait until the slider stops moving
    });
  });
  document.getElementById("wi-reset").addEventListener("click", function () {
    inputs.forEach(function (el) {
      var start = el.getAttribute("data-start");
      if (el.type === "checkbox") { el.checked = start === "1"; } else { el.value = start; }
      var out = box.querySelector("#wi-" + el.getAttribute("data-feature") + "-out");
      if (out) { out.textContent = start; }
    });
    counter++; showOriginal();
  });
})();
