#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "heart_disease.settings")
    # settings.py runs with DEBUG off unless told otherwise. When there is no .env file, no secret key,
    # no debug flag and no external database, this is clearly a local sandbox, so manage.py turns
    # development mode on. Production (gunicorn, Docker, Render) always sets these values and never
    # reaches this default.
    if not (Path(__file__).resolve().parent / ".env").exists() and not any(
            os.environ.get(name) for name in ("DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DATABASE_URL")):
        os.environ["DJANGO_DEBUG"] = "1"
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it is installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
