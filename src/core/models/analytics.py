"""Analytics and usage tracking models."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin, UUIDMixin


class EventType(str, Enum):
    """Types of user events to track."""
    USER_REGISTRATION = "user_registration"
    CHILD_ADDED = "child_added"
    TRANSLATION_REQUEST = "translation_request"
    CHECKIN_COMPLETED = "checkin_completed"
    REPORT_GENERATED = "report_generated"
    SUBSCRIPTION_CHANGED = "subscription_changed"
    ERROR_OCCURRED = "error_occurred"
    BOT_COMMAND_USED = "bot_command_used"
    FEATURE_ACCESSED = "feature_accessed"


class UsageAnalytics(BaseModel, UUIDMixin, TimestampMixin):
    """Model for tracking user analytics and usage patterns."""
    
    __tablename__ = "usage_analytics"
    
    # Event details
    event_type: Mapped[EventType] = mapped_column(String(50), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Event metadata
    event_data: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # User context
    user_telegram_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    user_timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Technical details
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bot_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Performance metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped[Optional["User"]] = relationship("User")
    
    def __repr__(self) -> str:
        return f"<UsageAnalytics(id={self.id}, event_type={self.event_type}, date={self.event_date})>"


class DailyStats(BaseModel, UUIDMixin, TimestampMixin):
    """Model for storing daily aggregated statistics."""
    
    __tablename__ = "daily_stats"
    
    # Date and metrics
    stat_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    
    # User metrics
    total_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Feature usage
    total_translations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_checkins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_reports_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Performance metrics
    average_response_time_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    error_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Additional metrics
    subscription_conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_usage_breakdown: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)
    
    def __repr__(self) -> str:
        return f"<DailyStats(date={self.stat_date}, active_users={self.active_users})>"