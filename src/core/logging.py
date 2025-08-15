"""Logging configuration for Family Emotions App."""
from __future__ import annotations

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

import structlog

from .config import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=False),
                "foreign_pre_chain": [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.ExtraAdder(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                ]
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "simple" if settings.debug else "detailed",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": logs_dir / "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": logs_dir / "errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        },
        "loggers": {
            # Root logger
            "": {
                "handlers": ["console", "file"],
                "level": settings.log_level,
                "propagate": False
            },
            
            # Application loggers
            "family_emotions": {
                "handlers": ["console", "file", "error_file"],
                "level": settings.log_level,
                "propagate": False
            },
            
            # Bot specific logger
            "telegram": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            
            # External service loggers
            "anthropic": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            
            "redis": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False
            },
            
            # Database loggers
            "sqlalchemy.engine": {
                "handlers": ["file"],
                "level": "INFO" if settings.debug else "WARNING",
                "propagate": False
            },
            
            "sqlalchemy.pool": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            },
            
            # HTTP client loggers
            "httpx": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            },
            
            "urllib3": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            },
            
            # Asyncio logger
            "asyncio": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up application logger
    logger = logging.getLogger("family_emotions")
    logger.info(f"Logging configured - Level: {settings.log_level}, Debug: {settings.debug}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"family_emotions.{name}")


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__.lower())


# Custom log filters and handlers for specific use cases

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs."""
    
    SENSITIVE_PATTERNS = [
        "password",
        "token",
        "secret",
        "key",
        "api_key",
        "telegram_id"
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        if hasattr(record, 'msg'):
            message = str(record.msg).lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in message:
                    # Replace with placeholder
                    record.msg = record.msg.replace(
                        record.msg[record.msg.lower().find(pattern):],
                        f"{pattern.upper()}_REDACTED"
                    )
        return True


class StructuredLogger:
    """Structured logger with context support."""
    
    def __init__(self, name: str):
        self._logger = structlog.get_logger(name)
        self._context = {}
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Bind context variables."""
        new_logger = StructuredLogger(self._logger.name)
        new_logger._logger = self._logger.bind(**kwargs)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, **kwargs)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger."""
    return StructuredLogger(f"family_emotions.{name}")


# Performance logging decorator
def log_performance(logger: logging.Logger = None, level: int = logging.INFO):
    """Decorator to log function execution time."""
    import time
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            function_logger = logger or get_logger(func.__module__)
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                function_logger.log(
                    level,
                    f"Function {func.__name__} executed in {execution_time:.3f}s"
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                function_logger.error(
                    f"Function {func.__name__} failed after {execution_time:.3f}s: {e}"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            function_logger = logger or get_logger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                function_logger.log(
                    level,
                    f"Function {func.__name__} executed in {execution_time:.3f}s"
                )
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                function_logger.error(
                    f"Function {func.__name__} failed after {execution_time:.3f}s: {e}"
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator