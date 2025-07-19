# 1. Use the specified platform and a slim base image
FROM --platform=linux/amd64 python:3.9-slim

# Set working directory
WORKDIR /app

# 2. Install build and system dependencies (including Tesseract OCR)
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

# 4. Create a non-root user for better security
RUN useradd --create-home app
USER app

# 5. The CMD is good for documentation, but the hackathon's run command will override it.
CMD ["python", "src/main.py"]