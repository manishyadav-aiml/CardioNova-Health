#!/usr/bin/env python3
"""
Static audit of the user interface: finds buttons, links and forms that cannot work.
Pure standard library (no Django needed), so it also runs in CI.

    python scripts/audit_ui.py

What it checks
  1. every {% url 'name' ... %} exists and gets the right number of arguments
  2. every view named in urls.py really exists
  3. every {% static '...' %} file exists
  4. every <button> either submits a form or has a JavaScript hook (id or data-* attribute)
  5. every POST form has {% csrf_token %}; file inputs have enctype="multipart/form-data"
  6. no dead links (href="#", empty href) and every #anchor has a target
  7. every element id that the JavaScript looks up exists in a template
  8. {% extends %} / {% include %} targets exist; no inline scripts, inline handlers or inline styles (CSP)
Exit code 1 when something is wrong.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "prediction"
TEMPLATES = APP / "templates"
STATIC = APP / "static"

problems, notes = [], []


def problem(where, message):
    problems.append(f"{where}: {message}")


def read(path):
    return Path(path).read_text(encoding="utf-8")


def rel(path):
    return str(Path(path).relative_to(ROOT))


# --------------------------------------------------------------------------- urls and views
urls_src = read(APP / "urls.py")
url_names = {}                                            # name -> number of converters in the path
for match in re.finditer(r'path\(\s*(?:\n\s*)?"([^"]*)"(.*?)(?<!\w)name="([^"]+)"', urls_src, re.S):
    url_names[match.group(3)] = len(re.findall(r"<[^>]+>", match.group(1)))
if not url_names:
    problem("urls.py", "no URL names found (parser problem?)")

module_defs = {}
for module in ("views", "password_reset_views"):
    tree = ast.parse(read(APP / f"{module}.py"))
    module_defs[module] = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
for alias, module in (("views", "views"), ("reset_views", "password_reset_views")):
    for name in re.findall(rf"\b{alias}\.(\w+)", urls_src):
        if name not in module_defs[module]:
            problem("urls.py", f"{alias}.{name} does not exist")
project_urls = read(ROOT / "heart_disease" / "urls.py")
for handler in re.findall(r'handler\d+ = "prediction\.views\.(\w+)"', project_urls):
    if handler not in module_defs["views"]:
        problem("heart_disease/urls.py", f"error handler {handler} does not exist")

# --------------------------------------------------------------------------- templates
templates = sorted(p for p in TEMPLATES.rglob("*") if p.suffix in (".html", ".txt"))
all_ids, all_template_text = set(), ""
for path in templates:
    text = read(path)
    all_template_text += text
    all_ids |= set(re.findall(r'\bid="([^"{]+)"', text))
    all_ids |= set(re.findall(r"\bid='([^'{]+)'", text))

JS_HOOK_ATTRS = ("data-copy", "data-copy-text", "data-print", "data-confirm")
js_files = sorted((STATIC / "prediction" / "js").glob("*.js"))
js_text = "\n".join(read(p) for p in js_files)
js_ids = set(re.findall(r'getElementById\("([\w-]+)"\)', js_text)) | set(re.findall(r'\$\("#([\w-]+)"\)', js_text))
js_ids |= set(re.findall(r'querySelector\("#([\w-]+)"\)', js_text))

for path in templates:
    text = read(path)
    where = rel(path)

    # 1. url tags
    for match in re.finditer(r"{%\s*url\s+'([^']+)'([^%]*)%}", text):
        name, rest = match.group(1), match.group(2).strip()
        if name not in url_names and not name.startswith("admin:"):
            problem(where, f"{{% url '{name}' %}} is not defined in urls.py")
        elif name in url_names:
            given = len([a for a in rest.split() if a and a != "as"]) if rest else 0
            if given != url_names[name]:
                problem(where, f"{{% url '{name}' %}} gets {given} argument(s) but the path takes {url_names[name]}")

    # 3. static files
    for match in re.finditer(r"{%\s*static\s+'([^']+)'\s*%}", text):
        if not (STATIC / match.group(1)).exists():
            problem(where, f"static file '{match.group(1)}' does not exist")
    loads_static = bool(re.search(r"{%\s*load\s[^%]*\bstatic\b", text))
    if "{% static" in text and not loads_static:
        problem(where, "uses {% static %} without {% load static %} (every template must load it itself)")

    # 8. extends / include / CSP
    for match in re.finditer(r"{%\s*(?:extends|include)\s+['\"]([^'\"]+)['\"]", text):
        if not (TEMPLATES / match.group(1)).exists():
            problem(where, f"template '{match.group(1)}' does not exist")
    if path.suffix == ".html":
        for external in re.findall(r'<(?:script|link)\b[^>]*(?:src|href)="(https?://[^"]+)"', text, re.I):
            problem(where, f"external resource {external} (the CSP only allows this site)")
        for bad, why in ((r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", "inline <script>"), (r"\son\w+\s*=\s*[\"']", "inline event handler"),
                         (r"<[a-z][^>]*\sstyle\s*=", "inline style attribute")):
            if re.search(bad, text, re.I) and "json_script" not in text[:0]:
                problem(where, f"{why} (blocked by the Content-Security-Policy)")

    if path.suffix != ".html":
        continue

    # 4. buttons
    forms = [(m.start(), m.end()) for m in re.finditer(r"<form\b.*?</form>", text, re.S | re.I)]
    for match in re.finditer(r"<button\b([^>]*)>", text, re.I):
        attrs = match.group(1)
        inside_form = any(a <= match.start() < b for a, b in forms)
        kind = re.search(r'\btype="(\w+)"', attrs)
        kind = kind.group(1) if kind else "submit"
        ident = re.search(r'\bid="([^"{]+)"', attrs)
        has_hook = any(attr in attrs for attr in JS_HOOK_ATTRS) or (ident and ident.group(1) in js_ids)
        if kind == "submit" and not inside_form and "form=" not in attrs:
            problem(where, f"submit button outside any form: <button{attrs[:70]}>")
        if kind == "button" and not has_hook:
            problem(where, f"button without any JavaScript hook: <button{attrs[:70]}>")
        if kind == "reset" and not inside_form:
            problem(where, "reset button outside a form")

    # 5. forms
    for match in re.finditer(r"<form\b([^>]*)>(.*?)</form>", text, re.S | re.I):
        attrs, body = match.group(1), match.group(2)
        method = re.search(r'\bmethod="(\w+)"', attrs)
        method = method.group(1).lower() if method else "get"
        if method == "post" and "{% csrf_token %}" not in body:
            problem(where, f"POST form without {{% csrf_token %}}: <form{attrs[:70]}>")
        if 'type="file"' in body and 'multipart/form-data' not in attrs:
            problem(where, "file upload form without enctype=multipart/form-data")
        if method == "dialog":
            if 'value="ok"' not in body or 'value="cancel"' not in body:
                problem(where, "dialog form needs buttons with value=ok and value=cancel")
        if method == "post" and not re.search(r"\baction=", attrs) and "{% block" in text:
            pass                                          # posts to the current page, which is allowed

    # 6. links
    for match in re.finditer(r"<a\b([^>]*)>", text, re.I):
        attrs = match.group(1)
        href = re.search(r'\bhref="([^"]*)"', attrs)
        if not href:
            if "name=" not in attrs:
                problem(where, f"<a> without href: <a{attrs[:60]}>")
            continue
        value = href.group(1).strip()
        if value in ("", "#", "javascript:void(0)") or value.lower().startswith("javascript:"):
            problem(where, f"dead link href=\"{value}\"")
        elif value.startswith("#") and not value.startswith("#{") and value[1:] not in all_ids:
            problem(where, f"anchor {value} has no target id")

# 7. JavaScript lookups
dynamic = {"wi-"}                                         # ids built at run time, e.g. "#wi-age-out"
for ident in sorted(js_ids):
    if ident not in all_ids and not any(ident.startswith(p) for p in dynamic):
        problem("static/prediction/js", f"JavaScript looks for id '{ident}' but no template has it")
for match in re.finditer(r'<input type="range"[^>]*data-feature="(\w+)"', all_template_text):
    if f'id="wi-{match.group(1)}-out"' not in all_template_text:
        problem("result.html", f"what-if slider '{match.group(1)}' has no output element (its number will not update)")

# dialog markup that main.js relies on
for needed in ("confirm-dialog", "confirm-title", "confirm-text", "confirm-ok", "confirm-cancel", "cookie-banner", "cookie-accept",
               "theme-toggle", "nav-toggle", "site-header", "site-nav", "back-to-top", "scroll-progress", "main-content", "page-loader"):
    if needed not in all_ids:
        problem("base.html", f"main.js expects an element with id '{needed}'")

# every JS file is loaded somewhere
for js in js_files:
    if js.name not in all_template_text:
        problem(rel(js), "this script is never loaded by a template")

print(f"Checked {len(templates)} templates, {len(js_files)} scripts, {len(url_names)} URL names.")
for line in notes:
    print("[NOTE]", line)
if problems:
    print(f"\n{len(problems)} problem(s):")
    for line in problems:
        print(" -", line)
    sys.exit(1)
print("UI audit passed: every URL name, static file, button, form and JavaScript hook is wired up.")
