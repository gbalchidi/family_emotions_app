"""Structured logging configuration."""

import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
import json

import structlog
from pythonjsonlogger import jsonlogger

from ...core.config import settings


def configure_logging():
    """Configure structured logging for the application."""
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="ISO"),
            
            # Add context information
            add_app_context,
            add_user_context,
            
            # Format exceptions
            structlog.processors.format_exc_info,
            
            # JSON output for production
            structlog.processors.JSONRenderer() if settings.environment == "production"
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    
    # Add JSON formatter for production
    if settings.environment == "production":
        handler = logging.StreamHandler(sys.stdout)
        formatter = CustomJSONFormatter()
        handler.setFormatter(formatter)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    
    # Set application loggers
    logging.getLogger("family_emotions").setLevel(settings.log_level.upper())


def add_app_context(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add application context to log entries."""
    event_dict.update({
        "service": "family-emotions-bot",
        "version": "0.1.0",
        "environment": settings.environment
    })
    return event_dict


def add_user_context(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add user context to log entries if available."""
    # This would be populated from context in actual requests
    # For now, we'll leave it as a placeholder
    return event_dict


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logs."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Ensure level is present
        if not log_record.get('level'):
            log_record['level'] = record.levelname.lower()
        
        # Add service info
        log_record['service'] = 'family-emotions-bot'
        log_record['logger'] = record.name


class LogContext:
    """Context manager for adding structured logging context."""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.logger = structlog.get_logger()
    
    def __enter__(self):
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.bound_logger.error(
                "Exception in log context",
                exc_type=exc_type.__name__,
                exc_value=str(exc_val),
                traceback=traceback.format_exception(exc_type, exc_val, exc_tb)
            )


class UserLogContext(LogContext):
    """Logging context with user information."""
    
    def __init__(self, user_id: int, username: Optional[str] = None, **kwargs):
        super().__init__(
            user_id=user_id,
            username=username,
            **kwargs
        )


class RequestLogContext(LogContext):
    """Logging context for request processing."""
    
    def __init__(self, 
                 user_id: int,
                 message_type: str,
                 request_id: Optional[str] = None,
                 **kwargs):
        super().__init__(
            user_id=user_id,
            message_type=message_type,
            request_id=request_id,
            **kwargs
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for the given name."""
    return structlog.get_logger(name)


def log_telegram_message(
    user_id: int,
    message_type: str,
    message_text: str,
    username: Optional[str] = None,
    **kwargs
):
    """Log an incoming Telegram message."""
    logger = get_logger("telegram.message")
    
    logger.info(
        "telegram_message_received",
        user_id=user_id,
        username=username,
        message_type=message_type,
        message_length=len(message_text),
        message_preview=message_text[:100] + "..." if len(message_text) > 100 else message_text,
        **kwargs
    )


def log_emotion_analysis(
    user_id: int,
    child_age: int,
    success: bool,
    processing_time_ms: int,
    confidence_score: Optional[float] = None,
    error: Optional[str] = None,
    **kwargs
):
    """Log an emotion analysis request."""
    logger = get_logger("emotion.analysis")
    
    log_data = {
        "user_id": user_id,
        "child_age": child_age,
        "success": success,
        "processing_time_ms": processing_time_ms,
        **kwargs
    }
    
    if confidence_score is not None:
        log_data["confidence_score"] = confidence_score
    
    if error:
        log_data["error"] = error
        logger.error("emotion_analysis_failed", **log_data)
    else:
        logger.info("emotion_analysis_completed", **log_data)


def log_checkin_completion(
    user_id: int,
    completed: bool,
    mood_score: Optional[int] = None,
    response_count: int = 0,
    **kwargs
):
    """Log a check-in completion."""
    logger = get_logger("checkin.completion")
    
    logger.info(
        "checkin_completed" if completed else "checkin_abandoned",
        user_id=user_id,
        completed=completed,
        mood_score=mood_score,
        response_count=response_count,
        **kwargs
    )


def log_api_call(
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    success: bool,
    error: Optional[str] = None,
    **kwargs
):
    """Log an external API call."""
    logger = get_logger(f"api.{service}")
    
    log_data = {
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "success": success,
        **kwargs
    }
    
    if error:
        log_data["error"] = error
        logger.error("api_call_failed", **log_data)
    else:
        logger.info("api_call_completed", **log_data)


def log_database_query(
    operation: str,
    table: str,
    query_time_ms: int,
    rows_affected: Optional[int] = None,
    error: Optional[str] = None,
    **kwargs
):
    """Log a database query."""
    logger = get_logger("database.query")
    
    log_data = {
        "operation": operation,
        "table": table,
        "query_time_ms": query_time_ms,
        **kwargs
    }
    
    if rows_affected is not None:
        log_data["rows_affected"] = rows_affected
    
    if error:
        log_data["error"] = error
        logger.error("database_query_failed", **log_data)
    else:
        logger.info("database_query_completed", **log_data)


def log_user_action(
    user_id: int,
    action: str,
    success: bool,
    details: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """Log a user action."""
    logger = get_logger("user.action")
    
    log_data = {
        "user_id": user_id,
        "action": action,
        "success": success,
        **kwargs
    }
    
    if details:
        log_data["details"] = details
    
    level = "info" if success else "warning"
    getattr(logger, level)("user_action", **log_data)


def log_system_event(
    event_type: str,
    message: str,
    level: str = "info",
    details: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """Log a system event."""
    logger = get_logger("system.event")
    
    log_data = {
        "event_type": event_type,
        "message": message,
        **kwargs
    }
    
    if details:
        log_data["details"] = details
    
    getattr(logger, level.lower())("system_event", **log_data)


def log_security_event(
    event_type: str,
    user_id: Optional[int],
    severity: str,
    description: str,
    source_ip: Optional[str] = None,
    **kwargs
):
    """Log a security-related event."""
    logger = get_logger("security.event")
    
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "severity": severity,
        "description": description,
        **kwargs
    }
    
    if source_ip:
        log_data["source_ip"] = source_ip
    
    # Security events are always at least WARNING level
    level = "critical" if severity == "high" else "warning"
    getattr(logger, level)("security_event", **log_data)


# Initialize logging when module is imported
if settings:  # Only configure if settings are available
    configure_logging()