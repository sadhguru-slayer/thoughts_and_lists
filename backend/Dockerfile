FROM python:3.12-slim

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
CMD sh -c "gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT --workers 4"