# Multi-stage production Dockerfile for TinyTravel API on Google Cloud Run
# Optimized for Headless Chromium + Playwright execution with non-root security.

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080

WORKDIR /app

# Install minimal OS dependencies required for Chromium headless execution
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt playwright

# Install Playwright Chromium headless browser binaries
RUN python -m playwright install --with-deps chromium

# Copy application codebase
COPY api /app/api
COPY fixtures /app/fixtures
COPY scripts /app/scripts

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Cloud Run default entrypoint
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
