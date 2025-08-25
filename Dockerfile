FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CACHE_BUST=v2024082501

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Upgrade pip first
RUN pip install --upgrade pip

# Copy only requirements first for better caching
COPY requirements.txt .

# Install dependencies without version conflicts - let pip resolve
RUN pip install python-telegram-bot && \
    pip install fastapi uvicorn[standard] && \
    pip install pydantic pydantic-settings && \
    pip install sqlalchemy alembic asyncpg && \
    pip install redis && \
    pip install anthropic && \
    pip install supabase && \
    pip install celery && \
    pip install structlog && \
    pip install sentry-sdk[fastapi] && \
    pip install prometheus-client && \
    pip install python-jose[cryptography] && \
    pip install httpx && \
    pip install python-multipart && \
    pip install psutil && \
    pip install python-json-logger

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs tmp && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py"]