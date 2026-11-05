#!/usr/bin/env bash
# Build script for Render / Railway / similar hosts:  bash build.sh
set -o errexit

pip install --upgrade pip
pip install -r requirements-prod.txt

# Re-create the model for the Python / scikit-learn version of this server.
# Set SKIP_TRAIN=1 to keep the committed model files instead.
if [ "$SKIP_TRAIN" != "1" ]; then
  python train_model.py
fi

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Optional first admin user (set DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD in the dashboard)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi
