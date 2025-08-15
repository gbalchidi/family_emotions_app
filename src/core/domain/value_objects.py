"""Value objects for the Family Emotions domain."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class EmotionIntensity(Enum):
    """Emotion intensity levels."""
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5


class MoodTrend(Enum):
    """Mood trend direction."""
    DECLINING = "declining"
    STABLE = "stable"
    IMPROVING = "improving"
    VOLATILE = "volatile"


@dataclass(frozen=True)
class Age:
    """Value object representing a child's age."""
    
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Age cannot be negative")
        if self.value > 18:
            raise ValueError("Age must be 18 or less for children")
    
    @classmethod
    def from_birth_date(cls, birth_date: date) -> Age:
        """Calculate age from birth date."""
        today = date.today()
        age = today.year - birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return cls(value=age)
    
    def to_age_group(self) -> str:
        """Get age group classification."""
        if self.value <= 2:
            return "toddler"
        elif self.value <= 5:
            return "preschooler"
        elif self.value <= 8:
            return "early_school"
        elif self.value <= 12:
            return "middle_school"
        else:
            return "teenager"


@dataclass(frozen=True)
class EmotionContext:
    """Value object for emotion context information."""
    
    child_age: Age
    personality_traits: Optional[List[str]] = None
    recent_events: Optional[List[str]] = None
    cultural_background: Optional[str] = None
    special_needs: Optional[str] = None
    
    def to_prompt_context(self) -> str:
        """Convert context to prompt-friendly format."""
        context_parts = [
            f"Child age: {self.child_age.value} ({self.child_age.to_age_group()})"
        ]
        
        if self.personality_traits:
            context_parts.append(f"Personality: {', '.join(self.personality_traits)}")
        
        if self.recent_events:
            context_parts.append(f"Recent events: {', '.join(self.recent_events)}")
        
        if self.cultural_background:
            context_parts.append(f"Cultural background: {self.cultural_background}")
        
        if self.special_needs:
            context_parts.append(f"Special considerations: {self.special_needs}")
        
        return " | ".join(context_parts)


@dataclass(frozen=True)
class MoodScore:
    """Value object for mood scoring."""
    
    value: Decimal
    
    def __post_init__(self):
        if self.value < -1 or self.value > 1:
            raise ValueError("Mood score must be between -1 and 1")
    
    @classmethod
    def from_emotions(cls, emotions: dict[str, float]) -> MoodScore:
        """Calculate mood score from emotion dictionary."""
        if not emotions:
            return cls(value=Decimal("0"))
        
        # Positive emotions
        positive_emotions = {
            "joy", "happiness", "excitement", "love", "gratitude",
            "contentment", "pride", "hope", "amusement", "relief"
        }
        
        # Negative emotions
        negative_emotions = {
            "sadness", "anger", "fear", "disgust", "frustration",
            "disappointment", "anxiety", "guilt", "shame", "loneliness"
        }
        
        positive_score = sum(
            score for emotion, score in emotions.items()
            if emotion.lower() in positive_emotions
        )
        
        negative_score = sum(
            score for emotion, score in emotions.items()
            if emotion.lower() in negative_emotions
        )
        
        # Calculate weighted average (-1 to 1 scale)
        total_weight = positive_score + negative_score
        if total_weight == 0:
            return cls(value=Decimal("0"))
        
        mood_value = (positive_score - negative_score) / total_weight
        return cls(value=Decimal(str(round(mood_value, 2))))
    
    def to_category(self) -> str:
        """Get mood category."""
        if self.value <= -0.6:
            return "very_negative"
        elif self.value <= -0.2:
            return "negative"
        elif self.value <= 0.2:
            return "neutral"
        elif self.value <= 0.6:
            return "positive"
        else:
            return "very_positive"
    
    def get_emoji(self) -> str:
        """Get emoji representation of mood."""
        category = self.to_category()
        emoji_map = {
            "very_negative": "😢",
            "negative": "😔",
            "neutral": "😐",
            "positive": "😊",
            "very_positive": "😄"
        }
        return emoji_map.get(category, "😐")


@dataclass(frozen=True)
class TranslationRequest:
    """Value object for emotion translation requests."""
    
    original_message: str
    child_context: EmotionContext
    parent_language: str = "en"
    response_style: str = "supportive"
    
    def __post_init__(self):
        if not self.original_message.strip():
            raise ValueError("Message cannot be empty")
        
        if len(self.original_message) > 5000:
            raise ValueError("Message too long (max 5000 characters)")
        
        valid_styles = {"supportive", "educational", "playful", "calm"}
        if self.response_style not in valid_styles:
            raise ValueError(f"Response style must be one of {valid_styles}")


@dataclass(frozen=True)
class CheckInQuestion:
    """Value object for check-in questions."""
    
    text: str
    category: str
    age_groups: List[str]
    follow_up_prompts: Optional[List[str]] = None
    
    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Question text cannot be empty")
        
        valid_categories = {"mood", "behavior", "social", "physical", "general"}
        if self.category not in valid_categories:
            raise ValueError(f"Category must be one of {valid_categories}")
        
        valid_age_groups = {"toddler", "preschooler", "early_school", "middle_school", "teenager"}
        if not all(age in valid_age_groups for age in self.age_groups):
            raise ValueError(f"Age groups must be from {valid_age_groups}")
    
    def is_appropriate_for_age(self, age: Age) -> bool:
        """Check if question is appropriate for given age."""
        age_group = age.to_age_group()
        return age_group in self.age_groups


@dataclass(frozen=True)
class EmotionInsight:
    """Value object for emotion insights."""
    
    emotion: str
    intensity: EmotionIntensity
    confidence: Decimal
    explanation: str
    suggested_responses: List[str]
    
    def __post_init__(self):
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        if not self.suggested_responses:
            raise ValueError("Must provide at least one suggested response")
        
        if len(self.suggested_responses) > 5:
            raise ValueError("Too many suggested responses (max 5)")
    
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence insight."""
        return self.confidence >= Decimal("0.7")
    
    def requires_attention(self) -> bool:
        """Check if this emotion requires immediate attention."""
        concerning_emotions = {
            "severe_anxiety", "depression", "self_harm", 
            "extreme_anger", "panic", "trauma_response"
        }
        return (
            self.emotion.lower() in concerning_emotions 
            and self.intensity in [EmotionIntensity.HIGH, EmotionIntensity.VERY_HIGH]
        )


@dataclass(frozen=True)
class FamilyPermissions:
    """Value object for family member permissions."""
    
    can_view_reports: bool = True
    can_create_translations: bool = True
    can_manage_children: bool = False
    can_schedule_checkins: bool = False
    can_export_data: bool = False
    
    @classmethod
    def for_parent(cls) -> FamilyPermissions:
        """Get full permissions for parent."""
        return cls(
            can_view_reports=True,
            can_create_translations=True,
            can_manage_children=True,
            can_schedule_checkins=True,
            can_export_data=True
        )
    
    @classmethod
    def for_caregiver(cls) -> FamilyPermissions:
        """Get default permissions for caregiver."""
        return cls(
            can_view_reports=True,
            can_create_translations=True,
            can_manage_children=False,
            can_schedule_checkins=True,
            can_export_data=False
        )
    
    @classmethod
    def for_viewer(cls) -> FamilyPermissions:
        """Get read-only permissions."""
        return cls(
            can_view_reports=True,
            can_create_translations=False,
            can_manage_children=False,
            can_schedule_checkins=False,
            can_export_data=False
        )