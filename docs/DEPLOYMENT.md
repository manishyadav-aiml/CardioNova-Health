# Deployment guide

This project is ready for deployment: it uses **gunicorn** (web server), **WhiteNoise** (static files),
**PostgreSQL via `DATABASE_URL`**, environment-variable settings, HTTPS security settings and a Docker setup.

> Before going online: put the **real dataset** in `dataset/`, delete `dataset/DEMO_DATA.txt`, run
> `python train_model.py` and commit the result. Otherwise the live site shows the "Demo mode" banner and its
> predictions are meaningless.

## 1. Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes (production) | Long random string. The app refuses to start without it when `DJANGO_DEBUG=0` |
| `DJANGO_DEBUG` | yes | `0` for production, `1` (default) for local development |
| `DJANGO_ALLOWED_HOSTS` | yes | Comma-separated host names, e.g. `myapp.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | yes | Comma-separated origins with scheme, e.g. `https://myapp.onrender.com` |
| `DATABASE_URL` | recommended | PostgreSQL URL. SQLite is used when it is not set (data is lost on most free hosts) |
| `DJANGO_SECURE_SSL` | no | `1` (default in production) forces HTTPS and secure cookies. Use `0` only for plain-http testing |
| `DJANGO_SUPERUSER_USERNAME`, `_EMAIL`, `_PASSWORD` | no | Creates the first admin user during build/start |
| `SKIP_TRAIN` | no | `1` = `build.sh` keeps the committed model files instead of retraining |
| `DJANGO_LOG_LEVEL`, `DJANGO_TIME_ZONE` | no | Logging level (default INFO), time zone (default Asia/Kolkata) |

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 2. Docker (local or any server)

```bash
docker compose up --build
```

Open http://localhost:8000. The compose file starts PostgreSQL and the web app, trains the model while building the
image, runs migrations and creates an admin user (`admin` / the password in `docker-compose.yml`, **change it**).

Run only the app image against your own database:

```bash
docker build -t heart-disease-prediction .
docker run -p 8000:8000 \
  -e DJANGO_DEBUG=0 -e DJANGO_SECRET_KEY=... -e DJANGO_SECURE_SSL=0 \
  -e DJANGO_ALLOWED_HOSTS=localhost -e DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000 \
  -e DATABASE_URL=postgres://user:pass@host:5432/db heart-disease-prediction
```

## 3. Render (free tier, easiest)

1. Push the project to GitHub.
2. In Render choose **New + > Blueprint**, select the repository. `render.yaml` creates the web service and a
   PostgreSQL database.
3. When asked, enter `DJANGO_SUPERUSER_PASSWORD`.
4. Wait for the build (`bash build.sh` installs packages, trains the model, collects static files, runs migrations).
5. Open the URL Render shows. Health check: `/api/health/`.

Manual setup instead of the blueprint: **New + > Web Service**, build command `bash build.sh`, start command
`gunicorn heart_disease.wsgi:application`, then add the environment variables above and a PostgreSQL database.
Free instances sleep after inactivity, so the first request can be slow.

## 4. Railway / Heroku-style platforms

The `Procfile` defines the web process. Set the variables from section 1, add a PostgreSQL plugin (it provides
`DATABASE_URL`), and use `bash build.sh` as the build step (or run `python train_model.py`,
`python manage.py collectstatic --noinput` and `python manage.py migrate` yourself).

## 5. PythonAnywhere

Upload the project, create a virtualenv with `pip install -r requirements.txt`, run `python train_model.py`,
`python manage.py migrate` and `python manage.py collectstatic`, then configure the WSGI file to use
`heart_disease.wsgi` and map `/static/` to the `staticfiles` folder.

## 6. After the first deployment

1. Log in to `/admin/` with the superuser.
2. Register a normal account for yourself, then give doctor accounts their role:
   `python manage.py make_doctor <username>` (or change the role in **Admin > Profiles**).
3. Open `/model/` and check the metrics and the "Demo mode" banner is gone.
4. Test the API: `curl https://<your-site>/api/health/`.

## 7. Production checklist

- [ ] Real dataset used, model retrained, `DEMO_DATA.txt` deleted
- [ ] `DJANGO_DEBUG=0` and a unique `DJANGO_SECRET_KEY`
- [ ] PostgreSQL configured through `DATABASE_URL`
- [ ] HTTPS enabled (default on Render/Railway)
- [ ] Default admin password changed
- [ ] Backups of the database
- [ ] Medical disclaimer visible (it is on every page and in every PDF report)
