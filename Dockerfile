FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

# Train the model inside the image so the pickle matches the installed scikit-learn,
# then collect the static files (including the evaluation charts).
# The key below exists only for this build step (settings refuse to load without one); the real key
# comes from the environment at run time.
RUN python train_model.py \
 && DJANGO_SECRET_KEY=build-only-placeholder python manage.py collectstatic --noinput

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["sh", "docker-entrypoint.sh"]
