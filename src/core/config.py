"""Configuration settings for Family Emotions App."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    # Support both DATABASE_URL and individual DB_ prefixed variables
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL", description="Full database URL")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port") 
    name: str = Field(default="family_emotions", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: Optional[str] = Field(default=None, description="Database password")
    
    # Connection pool settings
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        if self.database_url:
            # If DATABASE_URL is provided, use it directly but ensure asyncpg driver
            if self.database_url.startswith("postgres://"):
                return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif self.database_url.startswith("postgresql://"):
                return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif self.database_url.startswith("postgresql+asyncpg://"):
                return self.database_url
            else:
                return self.database_url
        else:
            # Build from individual components
            if not self.password:
                raise ValueError("Database password is required")
            return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    
    # Connection settings
    max_connections: int = Field(default=10, description="Max connections in pool")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class TelegramSettings(BaseSettings):
    """Telegram bot configuration settings."""
    
    model_config = SettingsConfigDict(extra="ignore")
    
    bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN", description="Telegram bot token")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for production")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook secret token")
    
    # Bot settings
    max_message_length: int = Field(default=4096, description="Max Telegram message length")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("Invalid bot token")
        return v


class AnthropicSettings(BaseSettings):
    """Anthropic Claude API configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Allow extra environment variables
    )
    
    # This will read from CLAUDE_API_KEY environment variable
    claude_api_key: str = Field(alias="CLAUDE_API_KEY", description="Claude API key")
    model: str = Field(default="claude-3-5-sonnet-20241022", description="Claude model to use")
    max_tokens: int = Field(default=1000, description="Max tokens per request")
    temperature: float = Field(default=0.7, description="Model temperature")
    
    # Rate limiting
    requests_per_minute: int = Field(default=50, description="API requests per minute")
    requests_per_day: int = Field(default=1000, description="API requests per day")
    
    # Proxy settings (optional)
    proxy_url: Optional[str] = Field(default=None, alias="ANTHROPIC_PROXY_URL", description="HTTP/SOCKS proxy URL for Claude API")
    
    @field_validator("claude_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or not v.startswith("sk-"):
            raise ValueError("Invalid Claude API key format - must start with 'sk-'")
        return v
    
    @property
    def api_key(self) -> str:
        """Get the API key (alias for compatibility)."""
        return self.claude_api_key


class AppSettings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App info
    app_name: str = Field(default="Family Emotions App", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment")
    
    # Security
    secret_key: str = Field(alias="SECRET_KEY", description="Secret key for encryption")
    encryption_key: Optional[str] = Field(default=None, alias="ENCRYPTION_KEY", description="Encryption key for sensitive data")
    
    # Features
    enable_analytics: bool = Field(default=True, description="Enable analytics tracking")
    enable_caching: bool = Field(default=True, description="Enable Redis caching")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    
    # User limits
    free_tier_daily_limit: int = Field(default=5, description="Free tier daily translation limit")
    premium_tier_daily_limit: int = Field(default=50, description="Premium tier daily translation limit")
    
    # Scheduled tasks
    enable_scheduled_checkins: bool = Field(default=True, description="Enable scheduled check-ins")
    weekly_report_day: int = Field(default=0, description="Day of week for reports (0=Monday)")
    checkin_times: list[str] = Field(
        default=["09:00", "18:00"], 
        description="Default check-in times"
    )
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @property
    def log_level(self) -> str:
        """Get appropriate log level."""
        return "DEBUG" if self.debug else "INFO"


# Global settings instance
settings = AppSettings()