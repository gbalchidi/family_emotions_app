"""Domain events for Family Emotions App."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "event_type": self.__class__.__name__,
            "timestamp": self.timestamp.isoformat(),
            **{k: v for k, v in self.__dict__.items() if k != "timestamp"}
        }


@dataclass(frozen=True)
class UserRegisteredEvent(DomainEvent):
    """Event raised when a new user registers."""
    
    user_id: UUID
    telegram_id: int
    first_name: str
    language_code: str


@dataclass(frozen=True)
class ChildAddedEvent(DomainEvent):
    """Event raised when a child is added to a family."""
    
    child_id: UUID
    parent_id: UUID
    child_name: str
    child_age: int


@dataclass(frozen=True)
class FamilyMemberAddedEvent(DomainEvent):
    """Event raised when a family member is added."""
    
    member_id: UUID
    family_id: UUID
    member_name: str
    role: str
    added_by: UUID


@dataclass(frozen=True)
class EmotionTranslatedEvent(DomainEvent):
    """Event raised when an emotion is translated."""
    
    translation_id: UUID
    user_id: UUID
    child_id: Optional[UUID]
    detected_emotions: List[str]
    requires_attention: bool = False


@dataclass(frozen=True)
class CheckInScheduledEvent(DomainEvent):
    """Event raised when a check-in is scheduled."""
    
    checkin_id: UUID
    user_id: UUID
    child_id: Optional[UUID]
    scheduled_at: datetime


@dataclass(frozen=True)
class CheckInCompletedEvent(DomainEvent):
    """Event raised when a check-in is completed."""
    
    checkin_id: UUID
    user_id: UUID
    child_id: Optional[UUID]
    mood_score: float
    detected_emotions: List[str]
    completed_at: datetime


@dataclass(frozen=True)
class WeeklyReportGeneratedEvent(DomainEvent):
    """Event raised when a weekly report is generated."""
    
    report_id: UUID
    user_id: UUID
    child_id: Optional[UUID]
    week_start: datetime
    week_end: datetime
    average_mood_score: float


@dataclass(frozen=True)
class SubscriptionChangedEvent(DomainEvent):
    """Event raised when subscription status changes."""
    
    user_id: UUID
    old_status: str
    new_status: str
    expires_at: Optional[datetime]


@dataclass(frozen=True)
class ConcerningEmotionDetectedEvent(DomainEvent):
    """Event raised when concerning emotions are detected."""
    
    user_id: UUID
    child_id: Optional[UUID]
    emotion: str
    intensity: str
    context: str
    suggested_actions: List[str]


@dataclass(frozen=True)
class RateLimitExceededEvent(DomainEvent):
    """Event raised when rate limit is exceeded."""
    
    user_id: UUID
    limit_type: str  # daily, hourly, etc.
    current_count: int
    limit: int