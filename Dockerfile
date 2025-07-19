# 1. Use the specified platform and a slim base image
FROM --platform=linux/amd64 python:3.9-slim

# Set working directory
WORKDIR /app

# 2. Install build and system dependencies
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    tesseract-ocr \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy the rest of the application code
COPY . .

# 4. Create necessary directories for input, output, AND LOGS
RUN mkdir -p /app/input /app/output /app/logs

# 5. Create and switch to a non-root user
RUN useradd --create-home app
# Grant ownership of the entire /app directory to the 'app' user
RUN chown -R app:app /app
USER app

# 6. Default command
CMD ["python", "src/main.py"]