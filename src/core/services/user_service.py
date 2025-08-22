"""User service for managing user operations."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user import User, Children, FamilyMember, SubscriptionStatus, UserRole
from ..exceptions import (
    ResourceNotFoundError,
    ValidationError,
    BusinessLogicError,
    RateLimitExceededError
)
from ..config import settings

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and related operations."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: str = "en",
        timezone: str = "UTC"
    ) -> User:
        """
        Create a new user account.
        
        Args:
            telegram_id: Telegram user ID
            first_name: User's first name
            last_name: User's last name (optional)
            username: Telegram username (optional)
            language_code: User's language preference
            timezone: User's timezone
            
        Returns:
            Created User instance
            
        Raises:
            ValidationError: If user already exists or invalid data
        """
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            raise ValidationError(f"User with Telegram ID {telegram_id} already exists")
        
        # Create new user
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            timezone=timezone
        )
        
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        
        logger.info(f"Created new user: {user.id} (Telegram ID: {telegram_id})")
        return user
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by UUID."""
        stmt = (
            select(User)
            .options(
                selectinload(User.children),
                selectinload(User.family_members)
            )
            .where(User.id == user_id)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        stmt = (
            select(User)
            .options(
                selectinload(User.children),
                selectinload(User.family_members)
            )
            .where(User.telegram_id == telegram_id)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_profile(
        self,
        user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
        timezone: Optional[str] = None
    ) -> User:
        """Update user profile information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        # Update fields if provided
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if username is not None:
            user.username = username
        if language_code is not None:
            user.language_code = language_code
        if timezone is not None:
            user.timezone = timezone
        
        user.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(user)
        
        logger.info(f"Updated user profile: {user_id}")
        return user
    
    async def update_subscription(
        self,
        user_id: UUID,
        subscription_status: SubscriptionStatus,
        expires_at: Optional[datetime] = None
    ) -> User:
        """Update user subscription status."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        user.subscription_status = subscription_status
        user.subscription_expires_at = expires_at
        user.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(user)
        
        logger.info(f"Updated subscription for user {user_id}: {subscription_status}")
        return user
    
    async def check_daily_limit(self, user_id: UUID) -> bool:
        """
        Check if user has exceeded daily request limit.
        
        Returns:
            True if user can make more requests, False if limit exceeded
            
        Raises:
            RateLimitExceededError: If limit is exceeded
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        # Reset counter if new day
        today = date.today()
        if user.last_request_date != today:
            user.daily_requests_count = 0
            user.last_request_date = today
        
        # Check limits based on subscription
        if user.subscription_status == SubscriptionStatus.FREE:
            limit = settings.free_tier_daily_limit
        else:
            limit = settings.premium_tier_daily_limit
        
        if user.daily_requests_count >= limit:
            raise RateLimitExceededError(
                f"Daily limit of {limit} requests exceeded",
                details={"limit": limit, "current": user.daily_requests_count}
            )
        
        return True
    
    async def increment_request_count(self, user_id: UUID) -> None:
        """Increment user's daily request count."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        today = date.today()
        if user.last_request_date != today:
            user.daily_requests_count = 1
            user.last_request_date = today
        else:
            user.daily_requests_count += 1
        
        await self._session.commit()
    
    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(user)
        
        logger.info(f"Deactivated user: {user_id}")
        return user
    
    async def reactivate_user(self, user_id: UUID) -> User:
        """Reactivate user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(user)
        
        logger.info(f"Reactivated user: {user_id}")
        return user
    
    async def get_active_users_count(self) -> int:
        """Get count of active users."""
        stmt = select(User).where(User.is_active == True)
        result = await self._session.execute(stmt)
        users = result.scalars().all()
        return len(users)
    
    async def get_users_by_subscription_status(
        self, 
        status: SubscriptionStatus
    ) -> List[User]:
        """Get users by subscription status."""
        stmt = (
            select(User)
            .where(User.subscription_status == status)
            .where(User.is_active == True)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())