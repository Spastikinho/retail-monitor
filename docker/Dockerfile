# Base image with Python
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Web target (Django + Gunicorn)
# ============================================
FROM base as web

# Copy source code and scripts
COPY src /app/src
COPY scripts /app/scripts

# Create staticfiles directory and logs directory
RUN mkdir -p /app/staticfiles /app/logs

# Create non-root user
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

EXPOSE 8000

# ============================================
# Worker target (Celery + Playwright)
# ============================================
FROM base as worker

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Create non-root user BEFORE installing playwright
RUN addgroup --system app && adduser --system --group app --home /home/app

# Set environment for playwright to use correct home directory
ENV HOME=/home/app
ENV PLAYWRIGHT_BROWSERS_PATH=/home/app/.cache/ms-playwright

# Install Playwright browsers as root first to a shared location
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH && \
    playwright install chromium && \
    chown -R app:app $PLAYWRIGHT_BROWSERS_PATH

# Copy source code
COPY src /app/src

# Create directories for data
RUN mkdir -p /app/data/raw_snapshots /app/browser_profiles /app/logs

# Set ownership
RUN chown -R app:app /app
USER app
