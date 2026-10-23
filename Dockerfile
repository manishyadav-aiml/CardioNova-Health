FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

# Train the model inside the image so the pickle matches the installed scikit-learn,
# then collect the static files (including the evaluation charts).
RUN python train_model.py && python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "docker-entrypoint.sh"]
