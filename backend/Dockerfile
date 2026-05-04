FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY app /app/app
COPY scripts /app/scripts
RUN pip install --no-cache-dir -e .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Worker command:
# python -m app.workers.worker_main
# Migration command:
# python scripts/run_migrations.py
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
