"""Emotion-related models for translations and check-ins."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin, UUIDMixin


class TranslationStatus(str, Enum):
    """Status of emotion translation request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckinType(str, Enum):
    """Type of check-in interaction."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ResponseType(str, Enum):
    """Type of user response to check-in."""
    TEXT = "text"
    VOICE = "voice"
    EMOJI = "emoji"
    SCALE = "scale"


class EmotionTranslation(BaseModel, UUIDMixin, TimestampMixin):
    """Model for storing emotion translation requests and responses."""
    
    __tablename__ = "emotion_translations"
    
    # Request data
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    child_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    situation_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Translation results
    translated_emotions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    response_options: Mapped[Optional[List[Dict[str, str]]]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Processing info
    status: Mapped[TranslationStatus] = mapped_column(
        String(20), default=TranslationStatus.PENDING, nullable=False
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Model info
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="emotion_translations")
    
    child_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("children.id", ondelete="SET NULL"), nullable=True
    )
    child: Mapped[Optional["Children"]] = relationship(
        "Children", back_populates="emotion_translations"
    )
    
    def __repr__(self) -> str:
        return f"<EmotionTranslation(id={self.id}, status={self.status})>"


class Checkin(BaseModel, UUIDMixin, TimestampMixin):
    """Model for storing check-in interactions."""
    
    __tablename__ = "checkins"
    
    # Check-in details
    checkin_type: Mapped[CheckinType] = mapped_column(String(20), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Response data
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_type: Mapped[ResponseType] = mapped_column(String(20), nullable=False)
    response_metadata: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    
    # Emotional analysis
    detected_emotions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    emotion_intensity: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON, nullable=True)
    mood_score: Mapped[Optional[float]] = mapped_column(nullable=True)  # -1 to 1 scale
    
    # Context
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="checkins")
    
    child_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("children.id", ondelete="SET NULL"), nullable=True
    )
    child: Mapped[Optional["Children"]] = relationship(
        "Children", back_populates="checkins"
    )
    
    def __repr__(self) -> str:
        return f"<Checkin(id={self.id}, type={self.checkin_type}, completed={self.is_completed})>"


class WeeklyReport(BaseModel, UUIDMixin, TimestampMixin):
    """Model for storing generated weekly emotion reports."""
    
    __tablename__ = "weekly_reports"
    
    # Report period
    week_start: Mapped[datetime] = mapped_column(nullable=False)
    week_end: Mapped[datetime] = mapped_column(nullable=False)
    
    # Report content
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    emotion_trends: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    insights: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Metrics
    total_checkins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_translations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_mood_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Generation info
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User")
    
    child_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("children.id", ondelete="SET NULL"), nullable=True
    )
    child: Mapped[Optional["Children"]] = relationship("Children")
    
    def __repr__(self) -> str:
        return f"<WeeklyReport(id={self.id}, week_start={self.week_start})>"