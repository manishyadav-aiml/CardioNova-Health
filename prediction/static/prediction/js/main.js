// HeartCare front-end behaviour. No inline scripts are used anywhere (Content-Security-Policy: script-src 'self').
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;

  function $(selector, context) { return (context || doc).querySelector(selector); }
  function $all(selector, context) { return Array.prototype.slice.call((context || doc).querySelectorAll(selector)); }
  function store(key, value) {                      // localStorage can be blocked: never let that break the page
    try { if (value === undefined) { return localStorage.getItem(key); } localStorage.setItem(key, value); } catch (e) { return null; }
    return value;
  }
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* 1 -- dark mode toggle ------------------------------------------------------------------ */
  function initTheme() {
    var button = $("#theme-toggle");
    if (!button) { return; }
    function sync() {
      var dark = root.getAttribute("data-theme") === "dark";
      button.setAttribute("aria-pressed", dark ? "true" : "false");
      button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    }
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store("theme", next);
      sync();
    });
    sync();
  }

  /* 2 -- simple cookie banner ---------------------------------------------------------------- */
  function initCookieBanner() {
    var banner = $("#cookie-banner"), accept = $("#cookie-accept");
    if (!banner || !accept) { return; }
    if (store("cookie-notice") !== "ok") { banner.hidden = false; }
    accept.addEventListener("click", function () { store("cookie-notice", "ok"); banner.hidden = true; });
  }

  /* 4 + 8 -- back to top button and scroll progress bar ------------------------------------------ */
  function initScroll() {
    var bar = $("#scroll-progress"), toTop = $("#back-to-top"), waiting = false;
    function update() {
      var height = root.scrollHeight - root.clientHeight;
      var share = height > 0 ? root.scrollTop / height : 0;
      if (bar) { bar.style.transform = "scaleX(" + Math.min(1, Math.max(0, share)) + ")"; }
      if (toTop) { toTop.hidden = root.scrollTop < 400; }
      waiting = false;
    }
    window.addEventListener("scroll", function () {
      if (!waiting) { waiting = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    if (toTop) {
      toTop.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
        var main = $("#main-content");
        if (main) { main.focus({ preventScroll: true }); }
      });
    }
    update();
  }

  /* 5 -- mobile menu ----------------------------------------------------------------------- */
  function initMenu() {
    var header = $("#site-header"), toggle = $("#nav-toggle");
    if (!header || !toggle) { return; }
    function set(open) {
      header.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
    toggle.addEventListener("click", function () { set(!header.classList.contains("nav-open")); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape") { set(false); } });
    $all("#site-nav a").forEach(function (link) { link.addEventListener("click", function () { set(false); }); });
  }

  /* 13 -- password visibility toggle ----------------------------------------------------------- */
  function initPasswordToggles() {
    $all("input[type=password]").forEach(function (input) {
      var wrap = doc.createElement("div");
      wrap.className = "pw-wrap";
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);
      var button = doc.createElement("button");
      button.type = "button";
      button.className = "pw-toggle";
      button.textContent = "Show";
      button.setAttribute("aria-label", "Show password");
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", function () {
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        button.textContent = show ? "Hide" : "Show";
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        button.setAttribute("aria-pressed", show ? "true" : "false");
      });
      wrap.appendChild(button);
    });
  }

  /* 9 -- copy button ----------------------------------------------------------------------- */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) { return navigator.clipboard.writeText(text); }
    return new Promise(function (resolve, reject) {      // fallback for plain http / old browsers
      var area = doc.createElement("textarea");
      area.value = text; area.setAttribute("readonly", ""); area.className = "hp";
      doc.body.appendChild(area); area.select();
      var ok = false;
      try { ok = doc.execCommand("copy"); } catch (e) { ok = false; }
      doc.body.removeChild(area);
      return ok ? resolve() : reject(new Error("copy failed"));
    });
  }
  function initCopy() {
    doc.addEventListener("click", function (e) {
      var button = e.target.closest("[data-copy], [data-copy-text]");
      if (!button) { return; }
      e.preventDefault();
      var text = button.getAttribute("data-copy-text");
      if (text === null) {
        var target = $(button.getAttribute("data-copy"));
        text = target ? (target.value || target.textContent) : "";
      }
      var label = button.textContent;
      copyText(String(text).trim()).then(function () {
        button.textContent = "Copied \u2713"; button.classList.add("copied");
      }, function () { button.textContent = "Press Ctrl+C to copy"; });
      setTimeout(function () { button.textContent = label; button.classList.remove("copied"); }, 2000);
    });
    // 10 -- print button (the print stylesheet does the rest)
    doc.addEventListener("click", function (e) {
      if (e.target.closest("[data-print]")) { e.preventDefault(); window.print(); }
    });
  }

  /* 17 -- confirmation modals ----------------------------------------------------------------- */
  function initConfirm() {
    var dialog = $("#confirm-dialog");
    var confirmed = [];
    var pending = null;
    function open(el) {
      var message = el.getAttribute("data-confirm");
      if (!dialog || typeof dialog.showModal !== "function") {           // very old browsers
        if (window.confirm(message)) { proceed(el); }
        return;
      }
      pending = el;
      $("#confirm-title").textContent = el.getAttribute("data-confirm-title") || "Please confirm";
      $("#confirm-text").textContent = message;
      $("#confirm-ok").textContent = el.getAttribute("data-confirm-ok") || "Confirm";
      dialog.returnValue = "";
      dialog.showModal();
      $("#confirm-cancel").focus();                                       // the safe choice has the focus
    }
    function proceed(el) { confirmed.push(el); el.click(); }
    doc.addEventListener("click", function (e) {
      var el = e.target.closest("[data-confirm]");
      if (!el) { return; }
      var index = confirmed.indexOf(el);
      if (index !== -1) { confirmed.splice(index, 1); return; }          // user already agreed: let the click through
      e.preventDefault();
      open(el);
    });
    if (dialog) {
      dialog.addEventListener("close", function () {
        var el = pending; pending = null;
        if (el && dialog.returnValue === "ok") { proceed(el); }
      });
    }
  }

  /* 6 + 16 -- loading state on submit and form error state ------------------------------------------ */
  function messageFor(el) {
    var v = el.validity;
    if (!v || v.valid) { return ""; }
    if (v.valueMissing) { return "This field is required."; }
    if (v.rangeUnderflow || v.rangeOverflow) { return "Enter a value between " + el.min + " and " + el.max + "."; }
    if (v.tooShort) { return "Please enter at least " + el.minLength + " characters."; }
    if (v.typeMismatch) { return "Enter a valid value."; }
    return "Please check this value.";
  }
  function showFieldError(el, message) {
    var field = el.closest(".field");
    if (!field) { return; }
    var note = field.querySelector(".js-error");
    if (!message) {
      if (note) { note.remove(); }
      field.classList.remove("has-error");
      el.removeAttribute("aria-invalid");
      return;
    }
    if (!note) {
      note = doc.createElement("div");
      note.className = "error js-error";
      note.setAttribute("role", "alert");
      (el.closest(".pw-wrap") || el).insertAdjacentElement("afterend", note);
    }
    note.textContent = message;
    field.classList.add("has-error");
    el.setAttribute("aria-invalid", "true");
  }
  function initForms() {
    var loader = $("#page-loader");
    function resetLoading() {
      $all("form").forEach(function (f) { delete f.dataset.submitting; });
      $all(".btn.loading").forEach(function (b) { b.classList.remove("loading"); b.removeAttribute("aria-busy"); });
      if (loader) { loader.hidden = true; }
    }
    window.addEventListener("pageshow", resetLoading);                    // back button restores the page

    doc.addEventListener("focusout", function (e) {                      // live error state while typing
      var el = e.target;
      if (el.matches && el.matches(".form-control") && el.form && el.form.hasAttribute("novalidate")) {
        showFieldError(el, messageFor(el));
      }
    });
    doc.addEventListener("input", function (e) {
      var el = e.target;
      if (el.matches && el.matches(".form-control") && el.closest(".field.has-error") && !messageFor(el)) {
        showFieldError(el, "");
      }
    });

    doc.addEventListener("submit", function (e) {
      var form = e.target;
      if (!(form instanceof HTMLFormElement) || (form.getAttribute("method") || "").toLowerCase() === "dialog") { return; }
      if (form.hasAttribute("novalidate")) {                              // the server checks again; this is just faster feedback
        var bad = $all(".form-control", form).filter(function (el) {
          var message = messageFor(el); showFieldError(el, message); return message;
        });
        if (bad.length) { e.preventDefault(); bad[0].focus(); return; }
      }
      if (e.defaultPrevented) { return; }
      if (form.dataset.submitting === "1") { e.preventDefault(); return; }   // no double submit
      var submitter = e.submitter || $("[type=submit]", form);
      if (submitter && submitter.hasAttribute("data-no-loader")) { return; }  // downloads never leave the page
      form.dataset.submitting = "1";
      if (submitter) { submitter.classList.add("loading"); submitter.setAttribute("aria-busy", "true"); }
      if (loader && form.method.toLowerCase() === "post") { setTimeout(function () { if (form.dataset.submitting === "1") { loader.hidden = false; } }, 500); }
    });

    var focusTarget = $("#form-error-summary") || $("#form-success") || $(".field.has-error .form-control");
    if (focusTarget) { focusTarget.focus(); }
  }

  /* page polish: messages, result gauge, factor bars, "/" focuses the search box ----------------------- */
  function initPolish() {
    $all(".messages .message:not(.error)").forEach(function (el) {
      setTimeout(function () {
        el.style.transition = "opacity .6s"; el.style.opacity = "0";
        setTimeout(function () { el.remove(); }, 700);
      }, 6000);
    });
    var marker = $(".gauge-marker");
    if (marker) {
      var value = parseFloat(marker.dataset.left);
      if (!isNaN(value)) {
        value = Math.max(0, Math.min(100, value));
        setTimeout(function () { marker.style.left = "calc(" + value + "% - 2px)"; }, 100);
      }
    }
    $all(".bar[data-width]").forEach(function (bar) {
      var w = parseFloat(bar.dataset.width);
      if (!isNaN(w)) { setTimeout(function () { bar.style.width = Math.max(2, Math.min(100, w)) + "%"; }, 150); }
    });
    doc.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      if (e.key === "/" && !e.ctrlKey && !e.metaKey && tag !== "input" && tag !== "textarea" && tag !== "select") {
        var box = $("#nav-q");
        if (box) { e.preventDefault(); box.focus(); }
      }
    });
    doc.body.classList.add("is-ready");
  }

  function start() {
    initTheme(); initCookieBanner(); initScroll(); initMenu(); initPasswordToggles();
    initCopy(); initConfirm(); initForms(); initPolish();
  }
  if (doc.readyState === "loading") { doc.addEventListener("DOMContentLoaded", start); } else { start(); }
})();
