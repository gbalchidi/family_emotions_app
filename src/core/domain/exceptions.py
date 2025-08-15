"""Domain exceptions for Family Emotions App."""
from __future__ import annotations

from typing import Optional


class DomainException(Exception):
    """Base exception for domain errors."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code or self.__class__.__name__


class UserNotFoundException(DomainException):
    """Exception raised when user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}", "USER_NOT_FOUND")


class ChildNotFoundException(DomainException):
    """Exception raised when child is not found."""
    
    def __init__(self, child_id: str):
        super().__init__(f"Child not found: {child_id}", "CHILD_NOT_FOUND")


class SubscriptionLimitExceededException(DomainException):
    """Exception raised when subscription limit is exceeded."""
    
    def __init__(self, limit_type: str, current: int, limit: int):
        super().__init__(
            f"Subscription limit exceeded for {limit_type}: {current}/{limit}",
            "SUBSCRIPTION_LIMIT_EXCEEDED"
        )
        self.limit_type = limit_type
        self.current = current
        self.limit = limit


class RateLimitExceededException(DomainException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit_type: str = "daily"):
        super().__init__(
            f"Rate limit exceeded ({limit_type}). Please try again later.",
            "RATE_LIMIT_EXCEEDED"
        )
        self.limit_type = limit_type


class InvalidAgeException(DomainException):
    """Exception raised for invalid age values."""
    
    def __init__(self, age: int):
        super().__init__(f"Invalid age: {age}. Age must be between 0 and 18.", "INVALID_AGE")


class EmotionTranslationException(DomainException):
    """Exception raised during emotion translation."""
    
    def __init__(self, message: str):
        super().__init__(f"Emotion translation failed: {message}", "TRANSLATION_FAILED")


class CheckInException(DomainException):
    """Exception raised during check-in process."""
    
    def __init__(self, message: str):
        super().__init__(f"Check-in error: {message}", "CHECKIN_ERROR")


class PermissionDeniedException(DomainException):
    """Exception raised when permission is denied."""
    
    def __init__(self, action: str):
        super().__init__(f"Permission denied for action: {action}", "PERMISSION_DENIED")
        self.action = action


class InvalidSubscriptionPlanException(DomainException):
    """Exception raised for invalid subscription plans."""
    
    def __init__(self, plan: str):
        super().__init__(f"Invalid subscription plan: {plan}", "INVALID_PLAN")


class FamilyMemberAlreadyExistsException(DomainException):
    """Exception raised when family member already exists."""
    
    def __init__(self, telegram_id: int):
        super().__init__(
            f"Family member with telegram_id {telegram_id} already exists",
            "MEMBER_EXISTS"
        )