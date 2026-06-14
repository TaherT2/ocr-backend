FROM python:3.11-slim

# Aggressive memory limits for 500MB RAM ceiling
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

RUN apt-get update && apt-get install -y \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Force exactly 1 worker to prevent memory duplication
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
