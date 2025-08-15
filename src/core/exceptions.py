"""Custom exceptions for Family Emotions App."""
from __future__ import annotations

from typing import Any, Dict, Optional


class FamilyEmotionsException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(FamilyEmotionsException):
    """Raised when data validation fails."""
    pass


class AuthenticationError(FamilyEmotionsException):
    """Raised when user authentication fails."""
    pass


class AuthorizationError(FamilyEmotionsException):
    """Raised when user lacks required permissions."""
    pass


class ResourceNotFoundError(FamilyEmotionsException):
    """Raised when requested resource doesn't exist."""
    pass


class RateLimitExceededError(FamilyEmotionsException):
    """Raised when user exceeds rate limits."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class ExternalServiceError(FamilyEmotionsException):
    """Raised when external service (Claude API, etc.) fails."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message, **kwargs)


class DatabaseError(FamilyEmotionsException):
    """Raised when database operations fail."""
    pass


class ConfigurationError(FamilyEmotionsException):
    """Raised when configuration is invalid."""
    pass


class BusinessLogicError(FamilyEmotionsException):
    """Raised when business rules are violated."""
    pass


class TelegramBotError(FamilyEmotionsException):
    """Raised when Telegram bot operations fail."""
    pass


class CacheError(FamilyEmotionsException):
    """Raised when cache operations fail."""
    pass


class SchedulingError(FamilyEmotionsException):
    """Raised when task scheduling fails."""
    pass