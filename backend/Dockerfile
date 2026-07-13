# Use lightweight Python base image
FROM python:3.10-slim

# Install system dependencies
# - tesseract-ocr: required for scanned document OCR processing
# - libpq-dev & gcc: required to compile psycopg2 connection driver
# - curl: required for Docker health checks
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements file and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code to the container working directory
COPY . .

# Expose port 8000
EXPOSE 8000

# Exec database schema migration and start FastAPI server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
