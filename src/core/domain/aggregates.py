"""Domain aggregates for Family Emotions App."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from .entities import Child, CheckIn, EmotionTranslation, FamilyMember
from .events import (
    ChildAddedEvent,
    DomainEvent,
    FamilyMemberAddedEvent,
    RateLimitExceededEvent,
    SubscriptionChangedEvent,
    UserRegisteredEvent
)
from .exceptions import DomainException
from .value_objects import Age, FamilyPermissions


class SubscriptionPlan:
    """Subscription plan configuration."""
    
    FREE = {
        "name": "free",
        "daily_translation_limit": 10,
        "daily_checkin_limit": 3,
        "max_children": 2,
        "max_family_members": 1,
        "weekly_reports": False,
        "priority_support": False
    }
    
    PREMIUM = {
        "name": "premium",
        "daily_translation_limit": 100,
        "daily_checkin_limit": 20,
        "max_children": 10,
        "max_family_members": 5,
        "weekly_reports": True,
        "priority_support": True
    }
    
    TRIAL = {
        "name": "trial",
        "daily_translation_limit": 50,
        "daily_checkin_limit": 10,
        "max_children": 5,
        "max_family_members": 3,
        "weekly_reports": True,
        "priority_support": False,
        "duration_days": 14
    }


@dataclass
class User:
    """User aggregate root."""
    
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: str = "en"
    timezone: str = "UTC"
    subscription_status: str = "free"
    subscription_expires_at: Optional[datetime] = None
    daily_requests_count: int = 0
    last_request_date: Optional[date] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    
    # Aggregate members
    children: List[Child] = field(default_factory=list)
    family_members: List[FamilyMember] = field(default_factory=list)
    
    # Domain events
    _domain_events: List[DomainEvent] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize user aggregate."""
        if not self.first_name.strip():
            raise ValueError("First name cannot be empty")
        
        # Add registration event
        self._add_event(
            UserRegisteredEvent(
                user_id=self.id,
                telegram_id=self.telegram_id,
                first_name=self.first_name,
                language_code=self.language_code,
                timestamp=self.created_at
            )
        )
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    @property
    def subscription_plan(self) -> dict:
        """Get current subscription plan configuration."""
        plans = {
            "free": SubscriptionPlan.FREE,
            "premium": SubscriptionPlan.PREMIUM,
            "trial": SubscriptionPlan.TRIAL
        }
        return plans.get(self.subscription_status, SubscriptionPlan.FREE)
    
    def add_child(
        self,
        name: str,
        age: int,
        birth_date: Optional[datetime] = None,
        gender: Optional[str] = None,
        personality_traits: Optional[List[str]] = None,
        special_needs: Optional[str] = None,
        interests: Optional[List[str]] = None
    ) -> Child:
        """Add a child to the family."""
        # Check limits
        max_children = self.subscription_plan["max_children"]
        if len(self.children) >= max_children:
            raise DomainException(
                f"Cannot add more than {max_children} children on {self.subscription_status} plan"
            )
        
        # Create child entity
        child = Child(
            name=name,
            age=Age(value=age),
            parent_id=self.id,
            birth_date=birth_date,
            gender=gender,
            personality_traits=personality_traits or [],
            special_needs=special_needs,
            interests=interests or []
        )
        
        self.children.append(child)
        
        # Add domain event
        self._add_event(
            ChildAddedEvent(
                child_id=child.id,
                parent_id=self.id,
                child_name=name,
                child_age=age,
                timestamp=datetime.now(timezone.utc)
            )
        )
        
        return child
    
    def remove_child(self, child_id: UUID) -> None:
        """Remove a child from the family."""
        self.children = [c for c in self.children if c.id != child_id]
    
    def get_child(self, child_id: UUID) -> Optional[Child]:
        """Get a child by ID."""
        return next((c for c in self.children if c.id == child_id), None)
    
    def add_family_member(
        self,
        telegram_id: int,
        name: str,
        role: str = "caregiver"
    ) -> FamilyMember:
        """Add a family member."""
        # Check limits
        max_members = self.subscription_plan["max_family_members"]
        if len(self.family_members) >= max_members:
            raise DomainException(
                f"Cannot add more than {max_members} family members on {self.subscription_status} plan"
            )
        
        # Check if member already exists
        if any(m.telegram_id == telegram_id for m in self.family_members):
            raise DomainException("Family member already exists")
        
        # Set permissions based on role
        permissions_map = {
            "parent": FamilyPermissions.for_parent(),
            "caregiver": FamilyPermissions.for_caregiver(),
            "viewer": FamilyPermissions.for_viewer()
        }
        permissions = permissions_map.get(role, FamilyPermissions.for_viewer())
        
        member = FamilyMember(
            telegram_id=telegram_id,
            name=name,
            role=role,
            permissions=permissions,
            added_by=self.id
        )
        
        self.family_members.append(member)
        
        # Add domain event
        self._add_event(
            FamilyMemberAddedEvent(
                member_id=member.id,
                family_id=self.id,
                member_name=name,
                role=role,
                added_by=self.id,
                timestamp=datetime.now(timezone.utc)
            )
        )
        
        return member
    
    def remove_family_member(self, member_id: UUID) -> None:
        """Remove a family member."""
        self.family_members = [m for m in self.family_members if m.id != member_id]
    
    def get_family_member(self, telegram_id: int) -> Optional[FamilyMember]:
        """Get family member by telegram ID."""
        return next((m for m in self.family_members if m.telegram_id == telegram_id), None)
    
    def can_make_request(self, request_type: str = "translation") -> bool:
        """Check if user can make a request based on rate limits."""
        # Reset daily counter if needed
        today = date.today()
        if self.last_request_date != today:
            self.daily_requests_count = 0
            self.last_request_date = today
        
        # Check limits based on request type
        if request_type == "translation":
            limit = self.subscription_plan["daily_translation_limit"]
        elif request_type == "checkin":
            limit = self.subscription_plan["daily_checkin_limit"]
        else:
            limit = 10  # Default limit
        
        return self.daily_requests_count < limit
    
    def increment_request_count(self) -> None:
        """Increment daily request count."""
        today = date.today()
        if self.last_request_date != today:
            self.daily_requests_count = 0
            self.last_request_date = today
        
        self.daily_requests_count += 1
        
        # Check if limit exceeded
        limit = self.subscription_plan["daily_translation_limit"]
        if self.daily_requests_count >= limit:
            self._add_event(
                RateLimitExceededEvent(
                    user_id=self.id,
                    limit_type="daily",
                    current_count=self.daily_requests_count,
                    limit=limit,
                    timestamp=datetime.now(timezone.utc)
                )
            )
    
    def upgrade_subscription(self, plan: str, duration_days: Optional[int] = None) -> None:
        """Upgrade user subscription."""
        old_status = self.subscription_status
        self.subscription_status = plan
        
        if duration_days:
            self.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        elif plan == "trial":
            self.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=14)
        else:
            self.subscription_expires_at = None
        
        self._add_event(
            SubscriptionChangedEvent(
                user_id=self.id,
                old_status=old_status,
                new_status=plan,
                expires_at=self.subscription_expires_at,
                timestamp=datetime.now(timezone.utc)
            )
        )
    
    def check_subscription_expiry(self) -> None:
        """Check and update subscription if expired."""
        if self.subscription_expires_at and datetime.now(timezone.utc) > self.subscription_expires_at:
            old_status = self.subscription_status
            self.subscription_status = "free"
            self.subscription_expires_at = None
            
            self._add_event(
                SubscriptionChangedEvent(
                    user_id=self.id,
                    old_status=old_status,
                    new_status="free",
                    expires_at=None,
                    timestamp=datetime.now(timezone.utc)
                )
            )
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def reactivate(self) -> None:
        """Reactivate user account."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def _add_event(self, event: DomainEvent) -> None:
        """Add a domain event."""
        self._domain_events.append(event)
    
    def collect_events(self) -> List[DomainEvent]:
        """Collect and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        
        # Also collect events from children and family members
        for child in self.children:
            events.extend(child.collect_domain_events())
        
        for member in self.family_members:
            events.extend(member.collect_domain_events())
        
        return events