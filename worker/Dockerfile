FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTF1_CACHE_DIR=/tmp/fastf1-cache \
    INGEST_SOURCE=fastf1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run Jobs sets JOB_ID via container env overrides from the Next.js API.
ENTRYPOINT ["python", "entrypoint.py"]
