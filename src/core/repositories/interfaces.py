"""Repository interfaces for Family Emotions App."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from src.core.domain.aggregates import User
from src.core.domain.entities import CheckIn, Child, EmotionTranslation, FamilyMember
from src.core.models.emotion import WeeklyReport


class UserRepository(ABC):
    """Interface for user repository."""
    
    @abstractmethod
    async def save(self, user: User) -> None:
        """Save user aggregate."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        pass
    
    @abstractmethod
    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Check if user exists by telegram ID."""
        pass
    
    @abstractmethod
    async def get_active_users(self, limit: int = 100) -> List[User]:
        """Get active users."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> None:
        """Update user."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete user."""
        pass


class ChildRepository(ABC):
    """Interface for child repository."""
    
    @abstractmethod
    async def save(self, child: Child) -> None:
        """Save child entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, child_id: UUID) -> Optional[Child]:
        """Get child by ID."""
        pass
    
    @abstractmethod
    async def get_by_parent_id(self, parent_id: UUID) -> List[Child]:
        """Get children by parent ID."""
        pass
    
    @abstractmethod
    async def update(self, child: Child) -> None:
        """Update child."""
        pass
    
    @abstractmethod
    async def delete(self, child_id: UUID) -> None:
        """Delete child."""
        pass


class FamilyMemberRepository(ABC):
    """Interface for family member repository."""
    
    @abstractmethod
    async def save(self, member: FamilyMember) -> None:
        """Save family member."""
        pass
    
    @abstractmethod
    async def get_by_id(self, member_id: UUID) -> Optional[FamilyMember]:
        """Get family member by ID."""
        pass
    
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[FamilyMember]:
        """Get family member by telegram ID."""
        pass
    
    @abstractmethod
    async def get_by_family_id(self, family_id: UUID) -> List[FamilyMember]:
        """Get family members by family ID."""
        pass
    
    @abstractmethod
    async def update(self, member: FamilyMember) -> None:
        """Update family member."""
        pass
    
    @abstractmethod
    async def delete(self, member_id: UUID) -> None:
        """Delete family member."""
        pass


class EmotionTranslationRepository(ABC):
    """Interface for emotion translation repository."""
    
    @abstractmethod
    async def save(self, translation: EmotionTranslation) -> None:
        """Save emotion translation."""
        pass
    
    @abstractmethod
    async def get_by_id(self, translation_id: UUID) -> Optional[EmotionTranslation]:
        """Get translation by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[EmotionTranslation]:
        """Get translations by user ID."""
        pass
    
    @abstractmethod
    async def get_by_child_id(
        self,
        child_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[EmotionTranslation]:
        """Get translations by child ID."""
        pass
    
    @abstractmethod
    async def get_recent(
        self,
        user_id: UUID,
        days: int = 7,
        limit: int = 50
    ) -> List[EmotionTranslation]:
        """Get recent translations."""
        pass
    
    @abstractmethod
    async def count_by_user_and_date(self, user_id: UUID, date: date) -> int:
        """Count translations by user and date."""
        pass


class CheckInRepository(ABC):
    """Interface for check-in repository."""
    
    @abstractmethod
    async def save(self, checkin: CheckIn) -> None:
        """Save check-in."""
        pass
    
    @abstractmethod
    async def get_by_id(self, checkin_id: UUID) -> Optional[CheckIn]:
        """Get check-in by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        completed_only: bool = False,
        limit: int = 10,
        offset: int = 0
    ) -> List[CheckIn]:
        """Get check-ins by user ID."""
        pass
    
    @abstractmethod
    async def get_pending(self, user_id: UUID) -> List[CheckIn]:
        """Get pending check-ins for user."""
        pass
    
    @abstractmethod
    async def get_overdue(self) -> List[CheckIn]:
        """Get all overdue check-ins."""
        pass
    
    @abstractmethod
    async def get_by_date_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        child_id: Optional[UUID] = None
    ) -> List[CheckIn]:
        """Get check-ins within date range."""
        pass
    
    @abstractmethod
    async def update(self, checkin: CheckIn) -> None:
        """Update check-in."""
        pass
    
    @abstractmethod
    async def delete(self, checkin_id: UUID) -> None:
        """Delete check-in."""
        pass


class WeeklyReportRepository(ABC):
    """Interface for weekly report repository."""
    
    @abstractmethod
    async def save(self, report: WeeklyReport) -> None:
        """Save weekly report."""
        pass
    
    @abstractmethod
    async def get_by_id(self, report_id: UUID) -> Optional[WeeklyReport]:
        """Get report by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 4,
        offset: int = 0
    ) -> List[WeeklyReport]:
        """Get reports by user ID."""
        pass
    
    @abstractmethod
    async def get_by_date_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        child_id: Optional[UUID] = None
    ) -> List[WeeklyReport]:
        """Get reports within date range."""
        pass
    
    @abstractmethod
    async def get_latest(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None
    ) -> Optional[WeeklyReport]:
        """Get latest report for user/child."""
        pass
    
    @abstractmethod
    async def exists_for_week(
        self,
        user_id: UUID,
        week_start: datetime,
        child_id: Optional[UUID] = None
    ) -> bool:
        """Check if report exists for specific week."""
        pass