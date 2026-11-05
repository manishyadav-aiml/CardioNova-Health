// Run with:  node tests_js/charts.test.js      (no packages needed)
// Loads static/prediction/js/charts.js into a fake browser and checks what it draws.
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");

const SOURCE = fs.readFileSync(__dirname + "/../prediction/static/prediction/js/charts.js", "utf8");

function fakeContext() {
  const calls = [];
  const ctx = new Proxy({ calls }, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop === "measureText") return (text) => ({ width: String(text).length * 6 });
      return (...args) => { calls.push([prop, ...args]); };
    },
    set(target, prop, value) { target[prop] = value; return true; },
  });
  return ctx;
}

function fakeCanvas(width) {
  const listeners = {};
  const attrs = {};
  const ctx = fakeContext();
  return {
    width: 300, height: 150, style: {}, parentNode: { clientWidth: width },
    getContext: () => ctx, ctx, listeners, attrs,
    setAttribute: (k, v) => { attrs[k] = v; },
    addEventListener: (name, fn) => { listeners[name] = fn; },
    getBoundingClientRect: () => ({ left: 0, width }),
  };
}

function boot(elements, extra = {}) {
  const fallback = { hidden: true };
  const document = {
    readyState: "complete",
    getElementById: (id) => elements[id] || null,
    querySelectorAll: (sel) => (sel === ".chart-fallback" ? [fallback] : []),
    documentElement: {},
    addEventListener() {},
  };
  const sandbox = {
    document, window: { devicePixelRatio: 2, addEventListener() {} },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
    MutationObserver: class { observe() {} },
    setTimeout, clearTimeout, console, Math, JSON, Number, String, Array, ...extra,
  };
  vm.runInNewContext(SOURCE, sandbox);
  return { fallback };
}

let passed = 0;
function test(name, fn) { fn(); passed += 1; console.log("ok -", name); }

test("history chart draws one point per record with labels and aria text", () => {
  const canvas = fakeCanvas(640);
  const data = [{ label: "01 Oct", p: 12.5 }, { label: "08 Oct", p: 48 }, { label: "15 Oct", p: 71.2 }];
  boot({ "history-chart": canvas, "chart-data": { textContent: JSON.stringify(data) } });
  const arcs = canvas.ctx.calls.filter((c) => c[0] === "arc");
  assert.strictEqual(arcs.length, 3);
  const texts = canvas.ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
  ["0%", "100%", "01 Oct", "15 Oct"].forEach((t) => assert.ok(texts.includes(t), "missing label " + t));
  assert.strictEqual(canvas.attrs.role, "img");
  assert.ok(canvas.attrs["aria-label"].includes("01 Oct") && canvas.attrs["aria-label"].includes("15 Oct"));
  assert.strictEqual(canvas.width, 1280);                   // sharp on a 2x screen
});

test("hovering a point shows its value", () => {
  const canvas = fakeCanvas(640);
  const data = [{ label: "A", p: 10 }, { label: "B", p: 90 }];
  boot({ "history-chart": canvas, "chart-data": { textContent: JSON.stringify(data) } });
  canvas.ctx.calls.length = 0;
  canvas.listeners.mousemove({ clientX: 626 });             // right edge = second point
  const texts = canvas.ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
  assert.ok(texts.includes("B: 90.0%"), "tooltip text missing: " + texts.join("|"));
  canvas.ctx.calls.length = 0;
  canvas.listeners.mouseleave();
  assert.ok(!canvas.ctx.calls.some((c) => c[0] === "fillText" && /: \d/.test(c[1])));
});

test("nearest() ignores the mouse when it is far from every point", () => {
  const { nearest } = (() => { const m = { exports: {} }; vm.runInNewContext(SOURCE, { module: m, document: {}, window: {} }); return m.exports; })();
  const pts = [{ label: "A", p: 1 }, { label: "B", p: 2 }, { label: "C", p: 3 }];
  assert.strictEqual(nearest(pts, 44, 640), 0);
  assert.strictEqual(nearest(pts, 330, 640), 1);
  assert.strictEqual(nearest(pts, 200, 640), null);
});

test("a single record is centred and does not divide by zero", () => {
  const canvas = fakeCanvas(500);
  boot({ "history-chart": canvas, "chart-data": { textContent: JSON.stringify([{ label: "Only", p: 33 }]) } });
  const arcs = canvas.ctx.calls.filter((c) => c[0] === "arc");
  assert.strictEqual(arcs.length, 1);
  assert.ok(Number.isFinite(arcs[0][1]) && Number.isFinite(arcs[0][2]));
});

test("doughnut shows the counts and percentages", () => {
  const canvas = fakeCanvas(360);
  boot({ "risk-chart": canvas, "risk-data": { textContent: "[3, 1, 1]" } });
  const texts = canvas.ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
  assert.ok(texts.includes("5"));
  assert.ok(texts.includes("Low: 3 (60%)"));
  assert.ok(texts.includes("Moderate: 1 (20%)"));
  assert.ok(texts.includes("High: 1 (20%)"));
});

test("doughnut with no records at all does not crash", () => {
  const canvas = fakeCanvas(360);
  boot({ "risk-chart": canvas, "risk-data": { textContent: "[0, 0, 0]" } });
  const texts = canvas.ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
  assert.ok(texts.includes("Low: 0"));
});

test("a drawing error shows the fallback text instead of a blank page", () => {
  const canvas = fakeCanvas(500);
  canvas.getContext = () => { throw new Error("no canvas"); };
  const { fallback } = boot({ "history-chart": canvas, "chart-data": { textContent: JSON.stringify([{ label: "x", p: 1 }]) } });
  assert.strictEqual(fallback.hidden, false);
});

test("broken JSON is ignored quietly", () => {
  const canvas = fakeCanvas(500);
  boot({ "history-chart": canvas, "chart-data": { textContent: "{not json" } });
  assert.strictEqual(canvas.ctx.calls.length, 0);
});

console.log(`\n${passed} JavaScript tests passed`);
