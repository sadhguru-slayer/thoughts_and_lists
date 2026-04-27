FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend app folder
COPY ./app /app

# Set Python path so imports work as in local
ENV PYTHONPATH=/app

# Run Gunicorn with Uvicorn worker
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app",
     "--bind", "0.0.0.0:8080",
     "--workers", "1",
     "--max-requests", "500",
     "--max-requests-jitter", "50",
     "--timeout", "60",
     "--graceful-timeout", "30",
     "--worker-tmp-dir", "/dev/shm"]
