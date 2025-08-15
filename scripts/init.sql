-- Initial database setup for Family Emotions App
-- This script runs when PostgreSQL container starts

-- Create database if it doesn't exist
-- Note: This might not work in all PostgreSQL Docker images
-- The database is usually created via POSTGRES_DB environment variable

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for performance (will be created after tables)
-- These will be run by Alembic migrations