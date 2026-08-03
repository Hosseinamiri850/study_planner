FROM python:3.13-slim

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

# Run any pending migrations, then launch gunicorn on the app factory.
EXPOSE 5000
CMD ["sh", "-c", "flask --app app db upgrade && gunicorn -b 0.0.0.0:5000 -w 4 app:app"]
