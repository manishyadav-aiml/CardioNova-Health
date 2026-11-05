// Run with:  node tests_js/ui.test.js     (no packages needed)
// Checks the click behaviour of the buttons that matter most: confirm dialogs (delete record / account),
// the dark-mode switch, and the what-if simulator (request body, display, reset, error).
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");

const JS = (name) => fs.readFileSync(__dirname + "/../prediction/static/prediction/js/" + name, "utf8");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------------------------------------------------------------- tiny fake DOM */
function element(attrs = {}, extra = {}) {
  const listeners = {};
  const el = {
    attrs: { ...attrs }, listeners, textContent: "", hidden: false, className: "", value: "", checked: false, type: "",
    classList: { _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); }, contains(c) { return this._s.has(c); }, toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); } },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    hasAttribute(k) { return k in this.attrs; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(name, fn) { (listeners[name] = listeners[name] || []).push(fn); },
    focus() { this.focused = true; },
    closest(sel) { return this.matchesSel && this.matchesSel(sel) ? this : null; },
    ...extra,
  };
  return el;
}

function page(registry) {
  const docListeners = {};
  const root = element({ "data-theme": "light" });
  const store = {};
  const document = {
    readyState: "complete", documentElement: root, body: element(),
    getElementById: (id) => registry["#" + id] || null,
    querySelector: (sel) => registry[sel] || null,
    querySelectorAll: (sel) => (registry["all:" + sel] || []),
    createElement: () => element(),
    addEventListener(name, fn) { (docListeners[name] = docListeners[name] || []).push(fn); },
  };
  function dispatch(name, target) {                       // like a click: returns true when the default action would run
    const event = { target, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, key: "" };
    (docListeners[name] || []).forEach((fn) => fn(event));
    return !event.defaultPrevented;
  }
  const window = {
    addEventListener() {}, requestAnimationFrame: (fn) => fn(), scrollTo() {}, print() { window.printed = true; },
    isSecureContext: false, confirm: () => false,
  };
  const sandbox = {
    document, window, localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } },
    navigator: {}, HTMLFormElement: function () {}, setTimeout, clearTimeout, console, Math, parseFloat, isNaN, Array, Promise, Error, String,
  };
  return { document, window, sandbox, root, store, dispatch, docListeners };
}

let passed = 0;
async function test(name, fn) { await fn(); passed += 1; console.log("ok -", name); }

(async () => {
  /* ---------------------------------------------------------------- confirm dialog */
  function confirmPage() {
    const submit = element({ "data-confirm": "Delete this record?", "data-confirm-title": "Delete record", "data-confirm-ok": "Delete" });
    submit.matchesSel = (s) => s === "[data-confirm]";
    const dialog = element({}, { returnValue: "", showModal() { this.opened = true; } });
    const reg = {
      "#confirm-dialog": dialog, "#confirm-title": element(), "#confirm-text": element(), "#confirm-ok": element(), "#confirm-cancel": element(),
      "#cookie-banner": null, "all:form": [], "all:.messages .message:not(.error)": [], "all:.bar[data-width]": [],
    };
    const p = page(reg);
    let submitted = 0;
    submit.click = () => { if (p.dispatch("click", submit)) { submitted += 1; } };   // the browser would submit the form here
    vm.runInNewContext(JS("main.js"), p.sandbox);
    return { p, submit, dialog, reg, get submitted() { return submitted; } };
  }
  const fire = (dialog, value) => { dialog.returnValue = value; (dialog.listeners.close || []).forEach((fn) => fn()); };

  await test("a confirm button opens the dialog and does NOT submit straight away", () => {
    const c = confirmPage();
    c.submit.click();
    assert.strictEqual(c.dialog.opened, true);
    assert.strictEqual(c.submitted, 0);
    assert.strictEqual(c.reg["#confirm-title"].textContent, "Delete record");
    assert.strictEqual(c.reg["#confirm-text"].textContent, "Delete this record?");
    assert.strictEqual(c.reg["#confirm-ok"].textContent, "Delete");
    assert.strictEqual(c.reg["#confirm-cancel"].focused, true);          // the safe choice has the focus
  });

  await test("choosing OK submits exactly once", () => {
    const c = confirmPage();
    c.submit.click();
    fire(c.dialog, "ok");
    assert.strictEqual(c.submitted, 1);
  });

  await test("choosing Cancel (or Escape) submits nothing", () => {
    const c = confirmPage();
    c.submit.click(); fire(c.dialog, "cancel");
    c.submit.click(); fire(c.dialog, "");
    assert.strictEqual(c.submitted, 0);
  });

  await test("the dialog works again after a confirmed action", () => {
    const c = confirmPage();
    c.submit.click(); fire(c.dialog, "ok");
    c.dialog.opened = false;
    c.submit.click();
    assert.strictEqual(c.dialog.opened, true);                           // asked again, not silently submitted
    assert.strictEqual(c.submitted, 1);
  });

  /* ---------------------------------------------------------------- dark mode */
  await test("the dark-mode button switches the theme and remembers it", () => {
    const button = element();
    const p = page({ "#theme-toggle": button, "all:form": [], "all:.messages .message:not(.error)": [], "all:.bar[data-width]": [] });
    vm.runInNewContext(JS("main.js"), p.sandbox);
    assert.strictEqual(button.attrs["aria-pressed"], "false");
    button.listeners.click[0]();
    assert.strictEqual(p.root.attrs["data-theme"], "dark");
    assert.strictEqual(p.store.theme, "dark");
    assert.strictEqual(button.attrs["aria-pressed"], "true");
    button.listeners.click[0]();
    assert.strictEqual(p.root.attrs["data-theme"], "light");
  });

  /* ---------------------------------------------------------------- what-if simulator */
  function whatifPage(fetchImpl) {
    const input = element({ "data-feature": "trestbps", "data-start": "140" }, { type: "range", value: "140" });
    const out = element();
    const box = element({ "data-url": "/result/7/whatif/", "data-before": "20" }, {
      querySelectorAll: () => [input], querySelector: (s) => (s === "#wi-trestbps-out" ? out : null),
    });
    const reg = {
      "#whatif": box, "#wi-after": element({}, { textContent: "20.0%" }), "#wi-delta": element(), "#wi-level": element({}, { textContent: "LOW", className: "badge badge-low" }),
      "#wi-error": element({}, { hidden: true }), "#wi-reset": element(),
      'meta[name="csrf-token"]': element({ content: "tok123" }),
    };
    reg["#wi-after"].classList = element().classList;
    const p = page(reg);
    const calls = [];
    p.sandbox.fetch = (url, options) => { calls.push({ url, options }); return fetchImpl(url, options); };
    p.sandbox.Object = Object; p.sandbox.JSON = JSON; p.sandbox.Number = Number;
    vm.runInNewContext(JS("whatif.js"), p.sandbox);
    return { input, out, reg, calls };
  }
  const ok = (json) => () => Promise.resolve({ ok: true, json: () => Promise.resolve(json) });

  await test("moving a slider sends ONLY the changed value with the CSRF token", async () => {
    const w = whatifPage(ok({ after: 35.54, risk_level: "MODERATE" }));
    w.input.value = "120";
    w.input.listeners.input[0]();
    assert.strictEqual(w.out.textContent, "120");
    await wait(330);
    assert.strictEqual(w.calls.length, 1);
    assert.strictEqual(w.calls[0].url, "/result/7/whatif/");
    assert.deepStrictEqual(JSON.parse(w.calls[0].options.body), { changes: { trestbps: 120 } });
    assert.strictEqual(w.calls[0].options.headers["X-CSRFToken"], "tok123");
    assert.strictEqual(w.reg["#wi-after"].textContent, "35.5%");
    assert.strictEqual(w.reg["#wi-delta"].textContent, "+15.5 points");
    assert.strictEqual(w.reg["#wi-level"].textContent, "MODERATE");
    assert.strictEqual(w.reg["#wi-level"].className, "badge badge-moderate");
  });

  await test("putting the slider back to its start value sends nothing and shows the original", async () => {
    const w = whatifPage(ok({ after: 50, risk_level: "MODERATE" }));
    w.input.value = "140";
    w.input.listeners.input[0]();
    await wait(330);
    assert.strictEqual(w.calls.length, 0);
    assert.strictEqual(w.reg["#wi-after"].textContent, "20.0%");
    assert.strictEqual(w.reg["#wi-delta"].textContent, "no change");
  });

  await test("Reset restores the sliders and the original estimate", async () => {
    const w = whatifPage(ok({ after: 35.5, risk_level: "MODERATE" }));
    w.input.value = "120"; w.input.listeners.input[0](); await wait(330);
    w.reg["#wi-reset"].listeners.click[0]();
    assert.strictEqual(w.input.value, "140");
    assert.strictEqual(w.reg["#wi-after"].textContent, "20.0%");
    assert.strictEqual(w.reg["#wi-level"].textContent, "LOW");
  });

  await test("a server error is shown to the user, not swallowed", async () => {
    const w = whatifPage(() => Promise.resolve({ ok: false, json: () => Promise.resolve({ error: "Value out of range." }) }));
    w.input.value = "300"; w.input.listeners.input[0](); await wait(330);
    assert.strictEqual(w.reg["#wi-error"].textContent, "Value out of range.");
    assert.strictEqual(w.reg["#wi-error"].hidden, false);
  });

  await test("a network failure shows a helpful message", async () => {
    const w = whatifPage(() => Promise.reject(new Error("offline")));
    w.input.value = "120"; w.input.listeners.input[0](); await wait(330);
    assert.ok(/Could not reach the server/.test(w.reg["#wi-error"].textContent));
  });

  console.log(`\n${passed} UI behaviour tests passed`);
})().catch((error) => { console.error("FAILED:", error.message); process.exit(1); });
