# Confirmed entrypoint: app/main.py exposes `app` (verified via your existing
# tests/test_smoke.py, which does `from app.main import app`).
FROM python:3.10-slim

WORKDIR /code

# System deps needed by scipy/scikit-learn/evidently wheels on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Change this if your app binds a different port internally.
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]