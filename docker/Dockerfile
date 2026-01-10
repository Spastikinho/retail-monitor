# Base image with Python
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/app \
    PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

# Set work directory
WORKDIR /app

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    playwright install chromium

# Copy source code and scripts
COPY src /app/src
COPY start.sh /app/start.sh
COPY start-worker.sh /app/start-worker.sh
COPY start-beat.sh /app/start-beat.sh

# Create directories
RUN mkdir -p /app/staticfiles /app/logs /app/data/raw_snapshots /app/browser_profiles

# Make scripts executable
RUN chmod +x /app/start.sh /app/start-worker.sh /app/start-beat.sh

EXPOSE 8000

# Default command (can be overridden by Railway service config)
CMD ["bash", "start.sh"]
