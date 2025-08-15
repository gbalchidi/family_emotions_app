"""Configuration settings for Family Emotions App."""

from typing import Any, Dict, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    app_name: str = "Family Emotions App"
    debug: bool = False
    environment: str = "production"
    
    # Telegram Bot settings
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    telegram_webhook_secret: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_SECRET")
    
    # Database settings
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis settings
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_ttl: int = Field(3600, env="REDIS_CACHE_TTL")  # 1 hour
    
    # Claude API settings
    claude_api_key: str = Field(..., env="CLAUDE_API_KEY")
    claude_model: str = Field("claude-3-5-sonnet-20240620", env="CLAUDE_MODEL")
    claude_max_tokens: int = Field(1024, env="CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(0.7, env="CLAUDE_TEMPERATURE")
    
    # Rate limiting
    rate_limit_requests_per_hour: int = Field(100, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    rate_limit_emotions_per_day: int = Field(20, env="RATE_LIMIT_EMOTIONS_PER_DAY")
    
    # Supabase settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_ANON_KEY")
    
    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # Monitoring settings
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Celery settings
    celery_broker_url: str = Field("redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")
    
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level setting."""
        if v.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Invalid log level")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()