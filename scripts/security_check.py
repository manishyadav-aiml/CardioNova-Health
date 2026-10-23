#!/usr/bin/env python3
"""
Quick security audit of the repository (no extra packages needed).  Run:  python scripts/security_check.py

Checks the working tree for committed secrets, risky code patterns and unsafe settings, and, if the folder is a git
repository, scans the WHOLE git history for secrets. Exit code 1 means a HIGH finding. For a deeper history scan
use gitleaks as well:  gitleaks detect --source .
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "staticfiles", "__pycache__", "migrations"}
TEXT_SUFFIXES = {".py", ".html", ".js", ".css", ".md", ".txt", ".yml", ".yaml", ".json", ".toml", ".cfg", ".ini", ".sh",
                 ".env", ".example", ""}
SELF = Path(__file__).resolve()
PLACEHOLDER = re.compile(r"(?i)(change[-_ ]?me|changeme|example|placeholder|your[-_ ]|put[-_ ]|<.*>|xxx|\$\{|\{\{|dummy|"
                         r"S3cure-pass|pass(word)?123|local-password|not-a-real|test|://user:|://postgres:postgres@)")

SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Stripe/secret-style key", re.compile(r"\bsk_(live|test)_[0-9A-Za-z]{16,}\b")),
    ("database URL with password", re.compile(r"(postgres(ql)?|mysql|mongodb(\+srv)?)://[^:/\s]+:[^@\s${]{4,}@")),
    ("assigned secret", re.compile(r"""(?ix)[a-z_]*(secret|password|passwd|api[_-]?key|token|auth[_-]?key)[a-z_]*["']?\s*[:=]\s*["']([^"'\s]{10,})["']""")),
]
RISKY_CODE = [
    ("HIGH", "debug switched on in code", re.compile(r"^\s*DEBUG\s*=\s*True\b", re.M), {".py"}),
    ("HIGH", "hard-coded Django SECRET_KEY", re.compile(r"""^\s*SECRET_KEY\s*=\s*["'][^"']+["']""", re.M), {".py"}),
    ("HIGH", "SQL built by hand (raw/extra/execute)", re.compile(r"\.(raw|extra)\(|cursor\.execute\("), {".py"}),
    ("HIGH", "eval/exec on data", re.compile(r"(?<![\w.])(eval|exec)\("), {".py"}),
    ("HIGH", "template output marked safe", re.compile(r"\|\s*safe\b|mark_safe\(|{%\s*autoescape\s+off"), {".py", ".html"}),
    ("HIGH", "shell=True / TLS verification off", re.compile(r"shell\s*=\s*True|verify\s*=\s*False"), {".py"}),
    ("HIGH", "inline <script> or event handler (breaks the CSP)", re.compile(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>|\son(click|load|error)\s*="), {".html"}),
    ("HIGH", "wildcard CORS", re.compile(r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True|Access-Control-Allow-Origin[\"']?\s*[:=,]\s*[\"']\*"), {".py"}),
    ("HIGH", "ALLOWED_HOSTS wildcard", re.compile(r"ALLOWED_HOSTS\s*=\s*\[\s*[\"']\*[\"']"), {".py"}),
    ("INFO", "csrf_exempt (allowed only on the token-protected API)", re.compile(r"csrf_exempt"), {".py"}),
    ("INFO", "pickle-based model file is loaded (never load model files from untrusted sources)", re.compile(r"joblib\.load|pickle\.load"), {".py"}),
]
INFO_ALLOWED = {"csrf_exempt (allowed only on the token-protected API)": {"prediction/views.py"},
                "pickle-based model file is loaded (never load model files from untrusted sources)": {"prediction/ml.py", "train_model.py"}}
findings = []


def add(level, where, what):
    findings.append((level, where, what))


def files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & SKIP_DIRS) and path.suffix in TEXT_SUFFIXES \
                and path.resolve() != SELF and path.stat().st_size < 1_000_000 and not path.name.endswith((".pkl", ".png")):
            yield path


def scan_text(label, text, only_secrets=False, suffix=".py"):
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            line = text[text.rfind("\n", 0, match.start()) + 1: text.find("\n", match.end()) if "\n" in text[match.end():] else len(text)]
            if PLACEHOLDER.search(line) or "tests" in label:
                continue
            add("HIGH", label, f"possible {name}: {line.strip()[:90]}")
    if only_secrets:
        return
    for level, name, pattern, suffixes in RISKY_CODE:
        if suffix in suffixes and pattern.search(text):
            if level == "INFO" and any(label.endswith(ok) for ok in INFO_ALLOWED.get(name, ())):
                continue
            if "tests" in label and level == "HIGH" and name.startswith(("shell", "debug")):
                continue
            add(level, label, name)


def check_working_tree():
    for path in files():
        rel = str(path.relative_to(ROOT))
        try:
            scan_text(rel, path.read_text(encoding="utf-8", errors="ignore"), suffix=path.suffix)
        except OSError:
            continue
    gitignore = (ROOT / ".gitignore").read_text() if (ROOT / ".gitignore").exists() else ""
    if not re.search(r"^\.env\s*$", gitignore, re.M):
        add("HIGH", ".gitignore", ".env files are not ignored")
    if not re.search(r"^\.env\.\*", gitignore, re.M):
        add("HIGH", ".gitignore", ".env.* variants are not ignored")
    dockerignore = (ROOT / ".dockerignore").read_text() if (ROOT / ".dockerignore").exists() else ""
    if ".env" not in dockerignore:
        add("HIGH", ".dockerignore", ".env is copied into the Docker image")
    for env_file in ROOT.glob(".env*"):
        if env_file.name != ".env.example":
            add("INFO", env_file.name, "a real env file exists in this folder: make sure it is never committed or zipped for sharing")


def check_git_history():
    if not (ROOT / ".git").exists():
        add("INFO", "git history", "no .git folder here, so history was not scanned (run this script inside your clone)")
        return
    try:
        out = subprocess.run(["git", "log", "--all", "-p", "--no-color", "--unified=0"], cwd=ROOT, capture_output=True,
                             text=True, errors="ignore", timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        add("INFO", "git history", "git could not be run")
        return
    added = "\n".join(line[1:] for line in out.splitlines() if line.startswith("+") and not line.startswith("+++"))
    before = len(findings)
    scan_text("git history", added, only_secrets=True)
    for name in ("\\.env$", "\\.pem$", "id_rsa", "\\.sqlite3$"):
        names = subprocess.run(["git", "log", "--all", "--name-only", "--pretty=format:"], cwd=ROOT, capture_output=True,
                               text=True, errors="ignore").stdout.splitlines()
        if any(re.search(name, n) for n in names):
            add("HIGH", "git history", f"a file matching {name} was committed at some point (remove it and rotate every secret in it)")
    if len(findings) == before:
        add("INFO", "git history", "scanned; no secret patterns found")


def main():
    check_working_tree()
    check_git_history()
    order = {"HIGH": 0, "INFO": 1}
    for level, where, what in sorted(findings, key=lambda f: (order[f[0]], f[1])):
        print(f"[{level}] {where}: {what}")
    high = [f for f in findings if f[0] == "HIGH"]
    print(f"\nSecurity check finished: {len(high)} high finding(s), {len(findings) - len(high)} note(s).")
    return 1 if high else 0


if __name__ == "__main__":
    sys.exit(main())
