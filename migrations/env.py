"""Alembic environment configuration for Family Emotions App."""
import asyncio
import logging
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

# Try to import async components, fallback to sync if not available
try:
    from sqlalchemy.ext.asyncio import create_async_engine
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.config import settings
from src.core.models.base import BaseModel

# Import all model classes to register them with Base metadata
from src.core.models.user import User, Children, FamilyMember
from src.core.models.emotion import EmotionTranslation, Checkin, WeeklyReport

# Alias for compatibility
Base = BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger('alembic.env')

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """Get database URL from settings or config."""
    try:
        # Try to get from app settings first
        db_url = settings.database.url
        # Convert asyncpg URL to sync for Alembic
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        return db_url
    except Exception:
        # Fallback to config file URL
        return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    if not ASYNC_AVAILABLE:
        logger.warning("SQLAlchemy async extensions not available, falling back to sync")
        return run_sync_migrations()
        
    url = get_database_url()
    
    connectable = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_sync_migrations() -> None:
    """Run migrations in sync mode."""
    url = get_database_url()
    
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Always use sync approach for Alembic migrations
    # This is the most reliable method for database migrations
    logger.info("Running migrations in synchronous mode")
    run_sync_migrations()


if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")
    run_migrations_online()