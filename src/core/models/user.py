"""User-related models for Family Emotions App."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin, UUIDMixin


class UserRole(str, Enum):
    """User roles in the system."""
    PARENT = "parent"
    CHILD = "child" 
    CAREGIVER = "caregiver"


class SubscriptionStatus(str, Enum):
    """Subscription status for users."""
    FREE = "free"
    PREMIUM = "premium"
    TRIAL = "trial"
    EXPIRED = "expired"


class User(BaseModel, UUIDMixin, TimestampMixin):
    """User model representing parents and caregivers."""
    
    __tablename__ = "users"
    
    # Telegram info
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # User settings
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Subscription
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        String(20), default=SubscriptionStatus.FREE, nullable=False
    )
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Usage tracking
    daily_requests_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_request_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    children: Mapped[List["Children"]] = relationship(
        "Children", back_populates="parent", cascade="all, delete-orphan"
    )
    family_members: Mapped[List["FamilyMember"]] = relationship(
        "FamilyMember", back_populates="user", cascade="all, delete-orphan"
    )
    emotion_translations: Mapped[List["EmotionTranslation"]] = relationship(
        "EmotionTranslation", back_populates="user"
    )
    checkins: Mapped[List["Checkin"]] = relationship(
        "Checkin", back_populates="user"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, name={self.first_name})>"


class Children(BaseModel, UUIDMixin, TimestampMixin):
    """Children model for tracking family children."""
    
    __tablename__ = "children"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Additional context
    personality_traits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    special_needs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Parent relationship
    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent: Mapped["User"] = relationship("User", back_populates="children")
    
    # Relationships
    emotion_translations: Mapped[List["EmotionTranslation"]] = relationship(
        "EmotionTranslation", back_populates="child"
    )
    checkins: Mapped[List["Checkin"]] = relationship(
        "Checkin", back_populates="child"
    )
    
    def __repr__(self) -> str:
        return f"<Children(id={self.id}, name={self.name}, age={self.age})>"


class FamilyMember(BaseModel, UUIDMixin, TimestampMixin):
    """Family members that can access child information."""
    
    __tablename__ = "family_members"
    
    # Member info
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False)
    
    # Permissions
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_create_translations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_manage_children: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Family connection
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="family_members")
    
    def __repr__(self) -> str:
        return f"<FamilyMember(id={self.id}, name={self.name}, role={self.role})>"