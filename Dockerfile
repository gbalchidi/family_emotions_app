FROM python:3.11.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CACHE_BUST=v2024082503

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
# Install PostgreSQL drivers FIRST
RUN pip install psycopg2-binary asyncpg && \
    pip install python-telegram-bot && \
    pip install fastapi uvicorn[standard] && \
    pip install pydantic pydantic-settings && \
    pip install sqlalchemy alembic && \
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

# Test database connections during build
RUN python test_db_connection.py || echo "Database connection test failed but continuing build"

# Add database migration script
COPY <<EOF /app/run_migrations.py
#!/usr/bin/env python3
"""Run database migrations on startup."""

import asyncio
import logging
from alembic.config import Config
from alembic import command
from src.core.config import settings

logger = logging.getLogger(__name__)

def run_migrations():
    """Run Alembic migrations."""
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        
        # Set the database URL for migrations
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database.url.replace("postgresql+asyncpg://", "postgresql://"))
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = run_migrations()
    sys.exit(0 if success else 1)
EOF

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