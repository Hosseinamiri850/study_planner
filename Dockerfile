# python:3.13-slim @ 2026-08 (digest verified via Docker Hub API).
# Bumping the base image = update tag AND digest together.
FROM python@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app

WORKDIR /app

# System deps: psycopg binary needs libpq; libpq-dev for build wheel fallback.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime user. Image content stays root-owned/read-only to the
# process; gunicorn binds a high port so no capability is needed.
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Plain `docker run` / non-compose orchestrators: migrate then serve.
# (Under compose, migrations + seeding run once in the dedicated init
# service before the app starts — see docker-compose.yml / TASK-034.)
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=2).status==200 else 1)"
CMD ["sh", "-c", "flask --app app db upgrade && gunicorn -b 0.0.0.0:5000 -w 4 app:app"]
