"""Domain entities for Family Emotions App."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from .events import (
    ChildAddedEvent,
    CheckInCompletedEvent,
    DomainEvent,
    EmotionTranslatedEvent,
    FamilyMemberAddedEvent,
    UserRegisteredEvent
)
from .value_objects import (
    Age,
    CheckInQuestion,
    EmotionContext,
    EmotionInsight,
    FamilyPermissions,
    MoodScore,
    TranslationRequest
)


class DomainEntity:
    """Base class for domain entities."""
    
    def __init__(self, entity_id: Optional[UUID] = None):
        self.id = entity_id or uuid4()
        self._domain_events: List[DomainEvent] = []
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event."""
        self._domain_events.append(event)
    
    def collect_domain_events(self) -> List[DomainEvent]:
        """Collect and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events


@dataclass
class Child(DomainEntity):
    """Child entity."""
    
    name: str
    age: Age
    parent_id: UUID
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None
    personality_traits: List[str] = field(default_factory=list)
    special_needs: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        super().__init__()
        if not self.name.strip():
            raise ValueError("Child name cannot be empty")
    
    def update_age(self, new_age: Age) -> None:
        """Update child's age."""
        self.age = new_age
    
    def add_personality_trait(self, trait: str) -> None:
        """Add a personality trait."""
        if trait and trait not in self.personality_traits:
            self.personality_traits.append(trait)
    
    def add_interest(self, interest: str) -> None:
        """Add an interest."""
        if interest and interest not in self.interests:
            self.interests.append(interest)
    
    def get_context(self, recent_events: Optional[List[str]] = None) -> EmotionContext:
        """Get emotion context for this child."""
        return EmotionContext(
            child_age=self.age,
            personality_traits=self.personality_traits,
            recent_events=recent_events,
            special_needs=self.special_needs
        )


@dataclass
class FamilyMember(DomainEntity):
    """Family member entity."""
    
    telegram_id: int
    name: str
    role: str
    permissions: FamilyPermissions
    added_by: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: Optional[datetime] = None
    
    def __post_init__(self):
        super().__init__()
        if not self.name.strip():
            raise ValueError("Member name cannot be empty")
        
        valid_roles = {"parent", "caregiver", "viewer"}
        if self.role not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
    
    def update_permissions(self, permissions: FamilyPermissions) -> None:
        """Update member permissions."""
        self.permissions = permissions
    
    def mark_active(self) -> None:
        """Mark member as active."""
        self.last_active = datetime.now(timezone.utc)
    
    def can_perform_action(self, action: str) -> bool:
        """Check if member can perform an action."""
        action_map = {
            "view_reports": self.permissions.can_view_reports,
            "create_translations": self.permissions.can_create_translations,
            "manage_children": self.permissions.can_manage_children,
            "schedule_checkins": self.permissions.can_schedule_checkins,
            "export_data": self.permissions.can_export_data
        }
        return action_map.get(action, False)


@dataclass
class EmotionTranslation(DomainEntity):
    """Emotion translation entity."""
    
    request: TranslationRequest
    user_id: UUID
    child_id: Optional[UUID] = None
    insights: List[EmotionInsight] = field(default_factory=list)
    mood_score: Optional[MoodScore] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        super().__init__()
    
    def add_insight(self, insight: EmotionInsight) -> None:
        """Add an emotion insight."""
        self.insights.append(insight)
        
        # Add event for concerning emotions
        if insight.requires_attention():
            self.add_domain_event(
                EmotionTranslatedEvent(
                    translation_id=self.id,
                    user_id=self.user_id,
                    child_id=self.child_id,
                    detected_emotions=[insight.emotion],
                    requires_attention=True,
                    timestamp=datetime.now(timezone.utc)
                )
            )
    
    def calculate_mood_score(self) -> MoodScore:
        """Calculate mood score from insights."""
        if not self.insights:
            return MoodScore(value=0)
        
        emotions = {
            insight.emotion: float(insight.confidence) * insight.intensity.value / 5
            for insight in self.insights
        }
        
        self.mood_score = MoodScore.from_emotions(emotions)
        return self.mood_score
    
    def get_primary_emotion(self) -> Optional[EmotionInsight]:
        """Get the primary (highest confidence) emotion."""
        if not self.insights:
            return None
        
        return max(self.insights, key=lambda i: i.confidence)
    
    def get_suggested_responses(self) -> List[str]:
        """Get all unique suggested responses."""
        responses = set()
        for insight in self.insights:
            responses.update(insight.suggested_responses)
        return list(responses)[:5]  # Limit to 5 responses


@dataclass
class CheckIn(DomainEntity):
    """Check-in entity."""
    
    user_id: UUID
    child_id: Optional[UUID]
    question: CheckInQuestion
    scheduled_at: datetime
    response_text: Optional[str] = None
    detected_emotions: List[str] = field(default_factory=list)
    mood_score: Optional[MoodScore] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        super().__init__()
    
    @property
    def is_completed(self) -> bool:
        """Check if check-in is completed."""
        return self.completed_at is not None
    
    @property
    def is_overdue(self) -> bool:
        """Check if check-in is overdue."""
        if self.is_completed:
            return False
        return datetime.now(timezone.utc) > self.scheduled_at
    
    def complete(
        self,
        response_text: str,
        detected_emotions: List[str],
        mood_score: MoodScore
    ) -> None:
        """Complete the check-in."""
        if self.is_completed:
            raise ValueError("Check-in already completed")
        
        self.response_text = response_text
        self.detected_emotions = detected_emotions
        self.mood_score = mood_score
        self.completed_at = datetime.now(timezone.utc)
        
        # Add domain event
        self.add_domain_event(
            CheckInCompletedEvent(
                checkin_id=self.id,
                user_id=self.user_id,
                child_id=self.child_id,
                mood_score=float(mood_score.value),
                detected_emotions=detected_emotions,
                completed_at=self.completed_at
            )
        )
    
    def skip(self, reason: str = "Skipped by user") -> None:
        """Skip the check-in."""
        if self.is_completed:
            raise ValueError("Check-in already completed")
        
        self.response_text = f"[SKIPPED] {reason}"
        self.completed_at = datetime.now(timezone.utc)