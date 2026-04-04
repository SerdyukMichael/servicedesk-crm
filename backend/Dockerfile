FROM python:3.11-slim

WORKDIR /app

# Зависимости системы (нужны для pymysql/cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev gcc curl libmagic1t64 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
