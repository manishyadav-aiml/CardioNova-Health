"""Text clean-up for everything a user types. Does not import Django (so it can be tested on its own).

Output is ALSO escaped wherever it is shown (Django templates, PDF report), so this is defence in depth.
"""
import re

_TAG = re.compile(r"<[^>]*>?")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]")   # incl. bidi override characters


def clean_text(value, multiline=False, max_length=None):
    """Removes HTML tags and control characters; collapses spaces (and line breaks unless multiline)."""
    text = _CONTROL.sub("", _TAG.sub("", str(value or "")))
    if multiline:
        text = "\n".join(" ".join(line.split()) for line in text.replace("\r", "").split("\n")).strip()
    else:
        text = " ".join(text.split())
    return text[:max_length] if max_length else text
