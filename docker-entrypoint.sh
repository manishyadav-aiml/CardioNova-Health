#!/bin/sh
set -e

python manage.py migrate --noinput

# Optional first admin user (set DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

exec gunicorn heart_disease.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers ${WEB_CONCURRENCY:-2} \
  --timeout 120
