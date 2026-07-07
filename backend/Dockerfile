# Werk Platform — Backend (FastAPI) container
# Referenced by infrastructure/docker-compose.yml (context: ../backend)
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed by asyncpg / psycopg2 / bcrypt builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code
COPY . .

# Non-root user (matches `user: "1000:1000"` in docker-compose.yml)
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER 1000:1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# app/main.py re-exports the FastAPI instance as `app`
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
