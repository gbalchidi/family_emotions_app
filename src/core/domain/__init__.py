"""Domain layer for Family Emotions App."""

from .aggregates import User
from .entities import Child, CheckIn, EmotionTranslation, FamilyMember
from .events import (
    ChildAddedEvent,
    CheckInCompletedEvent,
    DomainEvent,
    EmotionTranslatedEvent,
    FamilyMemberAddedEvent,
    UserRegisteredEvent,
    WeeklyReportGeneratedEvent
)
from .exceptions import (
    ChildNotFoundException,
    DomainException,
    EmotionTranslationException,
    InvalidAgeException,
    PermissionDeniedException,
    RateLimitExceededException,
    SubscriptionLimitExceededException,
    UserNotFoundException
)
from .value_objects import (
    Age,
    CheckInQuestion,
    EmotionContext,
    EmotionInsight,
    EmotionIntensity,
    FamilyPermissions,
    MoodScore,
    TranslationRequest
)

__all__ = [
    # Aggregates
    "User",
    
    # Entities
    "Child",
    "CheckIn", 
    "EmotionTranslation",
    "FamilyMember",
    
    # Events
    "DomainEvent",
    "UserRegisteredEvent",
    "ChildAddedEvent",
    "FamilyMemberAddedEvent",
    "EmotionTranslatedEvent",
    "CheckInCompletedEvent",
    "WeeklyReportGeneratedEvent",
    
    # Exceptions
    "DomainException",
    "UserNotFoundException",
    "ChildNotFoundException",
    "SubscriptionLimitExceededException",
    "RateLimitExceededException",
    "InvalidAgeException",
    "EmotionTranslationException",
    "PermissionDeniedException",
    
    # Value Objects
    "Age",
    "EmotionContext",
    "EmotionInsight",
    "EmotionIntensity",
    "MoodScore",
    "TranslationRequest",
    "CheckInQuestion",
    "FamilyPermissions",
]