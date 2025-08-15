"""SQLAlchemy implementations of repository interfaces."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.core.domain.aggregates import User as UserAggregate
from src.core.domain.entities import Child, CheckIn, EmotionTranslation, FamilyMember
from src.core.domain.value_objects import Age, FamilyPermissions
from src.core.models.analytics import WeeklyReport
from src.core.models.emotion import CheckinType, EmotionTranslation as EmotionTranslationModel
from src.core.models.user import Children, User, FamilyMember as FamilyMemberModel
from src.core.repositories.interfaces import (
    CheckInRepository,
    ChildRepository,
    EmotionTranslationRepository,
    FamilyMemberRepository,
    UserRepository,
    WeeklyReportRepository
)

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, user: UserAggregate) -> None:
        """Save user aggregate."""
        # Check if user exists
        existing_user = await self.get_by_id(user.id)
        
        if existing_user:
            # Update existing user
            stmt = select(User).where(User.id == user.id)
            result = await self._session.execute(stmt)
            db_user = result.scalar_one()
            
            # Update fields
            db_user.first_name = user.first_name
            db_user.last_name = user.last_name
            db_user.username = user.username
            db_user.language_code = user.language_code
            db_user.timezone = user.timezone
            db_user.subscription_status = user.subscription_status
            db_user.subscription_expires_at = user.subscription_expires_at
            db_user.daily_requests_count = user.daily_requests_count
            db_user.last_request_date = user.last_request_date
            db_user.is_active = user.is_active
            db_user.updated_at = user.updated_at
            
        else:
            # Create new user
            db_user = User(
                id=user.id,
                telegram_id=user.telegram_id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                language_code=user.language_code,
                timezone=user.timezone,
                subscription_status=user.subscription_status,
                subscription_expires_at=user.subscription_expires_at,
                daily_requests_count=user.daily_requests_count,
                last_request_date=user.last_request_date,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            self._session.add(db_user)
        
        await self._session.commit()
    
    async def get_by_id(self, user_id: UUID) -> Optional[UserAggregate]:
        """Get user by ID and reconstruct aggregate."""
        stmt = (
            select(User)
            .options(
                selectinload(User.children),
                selectinload(User.family_members)
            )
            .where(User.id == user_id)
        )
        
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
        
        return self._map_to_aggregate(db_user)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserAggregate]:
        """Get user by telegram ID."""
        stmt = (
            select(User)
            .options(
                selectinload(User.children),
                selectinload(User.family_members)
            )
            .where(User.telegram_id == telegram_id)
        )
        
        result = await self._session.execute(stmt)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
        
        return self._map_to_aggregate(db_user)
    
    async def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """Check if user exists by telegram ID."""
        stmt = select(func.count(User.id)).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0
    
    async def get_active_users(self, limit: int = 100) -> List[UserAggregate]:
        """Get active users."""
        stmt = (
            select(User)
            .options(
                selectinload(User.children),
                selectinload(User.family_members)
            )
            .where(User.is_active == True)
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        db_users = result.scalars().all()
        
        return [self._map_to_aggregate(db_user) for db_user in db_users]
    
    async def update(self, user: UserAggregate) -> None:
        """Update user."""
        await self.save(user)
    
    async def delete(self, user_id: UUID) -> None:
        """Delete user."""
        stmt = delete(User).where(User.id == user_id)
        await self._session.execute(stmt)
        await self._session.commit()
    
    def _map_to_aggregate(self, db_user: User) -> UserAggregate:
        """Map database model to domain aggregate."""
        # Create user aggregate
        user_aggregate = UserAggregate(
            telegram_id=db_user.telegram_id,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            username=db_user.username,
            language_code=db_user.language_code,
            timezone=db_user.timezone,
            subscription_status=db_user.subscription_status,
            subscription_expires_at=db_user.subscription_expires_at,
            daily_requests_count=db_user.daily_requests_count,
            last_request_date=db_user.last_request_date,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            is_active=db_user.is_active,
            id=db_user.id
        )
        
        # Map children
        user_aggregate.children = []
        for db_child in db_user.children:
            child = Child(
                name=db_child.name,
                age=Age(value=db_child.age),
                parent_id=db_child.parent_id,
                birth_date=db_child.birth_date,
                gender=db_child.gender,
                personality_traits=db_child.personality_traits.split(',') if db_child.personality_traits else [],
                special_needs=db_child.special_needs,
                interests=db_child.interests.split(',') if db_child.interests else [],
                created_at=db_child.created_at
            )
            child.id = db_child.id
            user_aggregate.children.append(child)
        
        # Map family members
        user_aggregate.family_members = []
        for db_member in db_user.family_members:
            permissions = FamilyPermissions(
                can_view_reports=db_member.can_view_reports,
                can_create_translations=db_member.can_create_translations,
                can_manage_children=db_member.can_manage_children
            )
            
            member = FamilyMember(
                telegram_id=db_member.telegram_id,
                name=db_member.name,
                role=db_member.role,
                permissions=permissions,
                added_by=db_member.user_id,
                created_at=db_member.created_at
            )
            member.id = db_member.id
            user_aggregate.family_members.append(member)
        
        return user_aggregate


class SQLAlchemyChildRepository(ChildRepository):
    """SQLAlchemy implementation of ChildRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, child: Child) -> None:
        """Save child entity."""
        # Check if child exists
        existing = await self.get_by_id(child.id)
        
        if existing:
            # Update existing
            stmt = select(Children).where(Children.id == child.id)
            result = await self._session.execute(stmt)
            db_child = result.scalar_one()
            
            db_child.name = child.name
            db_child.age = child.age.value
            db_child.birth_date = child.birth_date
            db_child.gender = child.gender
            db_child.personality_traits = ','.join(child.personality_traits) if child.personality_traits else None
            db_child.special_needs = child.special_needs
            db_child.interests = ','.join(child.interests) if child.interests else None
            
        else:
            # Create new
            db_child = Children(
                id=child.id,
                parent_id=child.parent_id,
                name=child.name,
                age=child.age.value,
                birth_date=child.birth_date,
                gender=child.gender,
                personality_traits=','.join(child.personality_traits) if child.personality_traits else None,
                special_needs=child.special_needs,
                interests=','.join(child.interests) if child.interests else None,
                created_at=child.created_at
            )
            self._session.add(db_child)
        
        await self._session.commit()
    
    async def get_by_id(self, child_id: UUID) -> Optional[Child]:
        """Get child by ID."""
        stmt = select(Children).where(Children.id == child_id)
        result = await self._session.execute(stmt)
        db_child = result.scalar_one_or_none()
        
        if not db_child:
            return None
        
        return self._map_to_entity(db_child)
    
    async def get_by_parent_id(self, parent_id: UUID) -> List[Child]:
        """Get children by parent ID."""
        stmt = (
            select(Children)
            .where(Children.parent_id == parent_id)
            .order_by(Children.name)
        )
        
        result = await self._session.execute(stmt)
        db_children = result.scalars().all()
        
        return [self._map_to_entity(db_child) for db_child in db_children]
    
    async def update(self, child: Child) -> None:
        """Update child."""
        await self.save(child)
    
    async def delete(self, child_id: UUID) -> None:
        """Delete child."""
        stmt = delete(Children).where(Children.id == child_id)
        await self._session.execute(stmt)
        await self._session.commit()
    
    def _map_to_entity(self, db_child: Children) -> Child:
        """Map database model to domain entity."""
        child = Child(
            name=db_child.name,
            age=Age(value=db_child.age),
            parent_id=db_child.parent_id,
            birth_date=db_child.birth_date,
            gender=db_child.gender,
            personality_traits=db_child.personality_traits.split(',') if db_child.personality_traits else [],
            special_needs=db_child.special_needs,
            interests=db_child.interests.split(',') if db_child.interests else [],
            created_at=db_child.created_at
        )
        child.id = db_child.id
        return child


class SQLAlchemyFamilyMemberRepository(FamilyMemberRepository):
    """SQLAlchemy implementation of FamilyMemberRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, member: FamilyMember) -> None:
        """Save family member."""
        # Check if member exists
        existing = await self.get_by_id(member.id)
        
        if existing:
            # Update existing
            stmt = select(FamilyMemberModel).where(FamilyMemberModel.id == member.id)
            result = await self._session.execute(stmt)
            db_member = result.scalar_one()
            
            db_member.name = member.name
            db_member.role = member.role
            db_member.can_view_reports = member.permissions.can_view_reports
            db_member.can_create_translations = member.permissions.can_create_translations
            db_member.can_manage_children = member.permissions.can_manage_children
            
        else:
            # Create new
            db_member = FamilyMemberModel(
                id=member.id,
                user_id=member.added_by,  # In domain model, added_by is family_id
                telegram_id=member.telegram_id,
                name=member.name,
                role=member.role,
                can_view_reports=member.permissions.can_view_reports,
                can_create_translations=member.permissions.can_create_translations,
                can_manage_children=member.permissions.can_manage_children,
                created_at=member.created_at
            )
            self._session.add(db_member)
        
        await self._session.commit()
    
    async def get_by_id(self, member_id: UUID) -> Optional[FamilyMember]:
        """Get family member by ID."""
        stmt = select(FamilyMemberModel).where(FamilyMemberModel.id == member_id)
        result = await self._session.execute(stmt)
        db_member = result.scalar_one_or_none()
        
        if not db_member:
            return None
        
        return self._map_to_entity(db_member)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[FamilyMember]:
        """Get family member by telegram ID."""
        stmt = select(FamilyMemberModel).where(FamilyMemberModel.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        db_member = result.scalar_one_or_none()
        
        if not db_member:
            return None
        
        return self._map_to_entity(db_member)
    
    async def get_by_family_id(self, family_id: UUID) -> List[FamilyMember]:
        """Get family members by family ID."""
        stmt = (
            select(FamilyMemberModel)
            .where(FamilyMemberModel.user_id == family_id)
            .order_by(FamilyMemberModel.name)
        )
        
        result = await self._session.execute(stmt)
        db_members = result.scalars().all()
        
        return [self._map_to_entity(db_member) for db_member in db_members]
    
    async def update(self, member: FamilyMember) -> None:
        """Update family member."""
        await self.save(member)
    
    async def delete(self, member_id: UUID) -> None:
        """Delete family member."""
        stmt = delete(FamilyMemberModel).where(FamilyMemberModel.id == member_id)
        await self._session.execute(stmt)
        await self._session.commit()
    
    def _map_to_entity(self, db_member: FamilyMemberModel) -> FamilyMember:
        """Map database model to domain entity."""
        permissions = FamilyPermissions(
            can_view_reports=db_member.can_view_reports,
            can_create_translations=db_member.can_create_translations,
            can_manage_children=db_member.can_manage_children
        )
        
        member = FamilyMember(
            telegram_id=db_member.telegram_id,
            name=db_member.name,
            role=db_member.role,
            permissions=permissions,
            added_by=db_member.user_id,
            created_at=db_member.created_at,
            last_active=db_member.updated_at
        )
        member.id = db_member.id
        return member


class SQLAlchemyEmotionTranslationRepository(EmotionTranslationRepository):
    """SQLAlchemy implementation of EmotionTranslationRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, translation: EmotionTranslation) -> None:
        """Save emotion translation."""
        # Create database model
        db_translation = EmotionTranslationModel(
            id=translation.id,
            user_id=translation.user_id,
            child_id=translation.child_id,
            original_message=translation.request.original_message,
            child_context=translation.request.child_context.to_prompt_context() if translation.request.child_context else None,
            translated_emotions=[insight.emotion for insight in translation.insights],
            response_options=[insight.suggested_responses for insight in translation.insights],
            confidence_score=float(translation.insights[0].confidence) if translation.insights else None,
            processing_time_ms=translation.processing_time_ms,
            created_at=translation.created_at
        )
        
        self._session.add(db_translation)
        await self._session.commit()
    
    async def get_by_id(self, translation_id: UUID) -> Optional[EmotionTranslation]:
        """Get translation by ID."""
        stmt = select(EmotionTranslationModel).where(EmotionTranslationModel.id == translation_id)
        result = await self._session.execute(stmt)
        db_translation = result.scalar_one_or_none()
        
        if not db_translation:
            return None
        
        # Note: Full reconstruction would require storing more data
        # For now, return a simplified version
        return None  # This would need proper domain entity reconstruction
    
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[EmotionTranslation]:
        """Get translations by user ID."""
        stmt = (
            select(EmotionTranslationModel)
            .where(EmotionTranslationModel.user_id == user_id)
            .order_by(desc(EmotionTranslationModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self._session.execute(stmt)
        db_translations = result.scalars().all()
        
        # Note: Would need proper domain entity reconstruction
        return []
    
    async def get_by_child_id(
        self,
        child_id: UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[EmotionTranslation]:
        """Get translations by child ID."""
        stmt = (
            select(EmotionTranslationModel)
            .where(EmotionTranslationModel.child_id == child_id)
            .order_by(desc(EmotionTranslationModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self._session.execute(stmt)
        db_translations = result.scalars().all()
        
        # Note: Would need proper domain entity reconstruction
        return []
    
    async def get_recent(
        self,
        user_id: UUID,
        days: int = 7,
        limit: int = 50
    ) -> List[EmotionTranslation]:
        """Get recent translations."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stmt = (
            select(EmotionTranslationModel)
            .where(
                and_(
                    EmotionTranslationModel.user_id == user_id,
                    EmotionTranslationModel.created_at >= cutoff_date
                )
            )
            .order_by(desc(EmotionTranslationModel.created_at))
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        db_translations = result.scalars().all()
        
        # Note: Would need proper domain entity reconstruction
        return []
    
    async def count_by_user_and_date(self, user_id: UUID, date: date) -> int:
        """Count translations by user and date."""
        start_date = datetime.combine(date, datetime.min.time())
        end_date = datetime.combine(date, datetime.max.time())
        
        stmt = (
            select(func.count(EmotionTranslationModel.id))
            .where(
                and_(
                    EmotionTranslationModel.user_id == user_id,
                    EmotionTranslationModel.created_at >= start_date,
                    EmotionTranslationModel.created_at <= end_date
                )
            )
        )
        
        result = await self._session.execute(stmt)
        return result.scalar() or 0


class SQLAlchemyWeeklyReportRepository(WeeklyReportRepository):
    """SQLAlchemy implementation of WeeklyReportRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def save(self, report: WeeklyReport) -> None:
        """Save weekly report."""
        self._session.add(report)
        await self._session.commit()
    
    async def get_by_id(self, report_id: UUID) -> Optional[WeeklyReport]:
        """Get report by ID."""
        stmt = select(WeeklyReport).where(WeeklyReport.id == report_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 4,
        offset: int = 0
    ) -> List[WeeklyReport]:
        """Get reports by user ID."""
        stmt = (
            select(WeeklyReport)
            .where(WeeklyReport.user_id == user_id)
            .order_by(desc(WeeklyReport.week_start))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
        child_id: Optional[UUID] = None
    ) -> List[WeeklyReport]:
        """Get reports within date range."""
        conditions = [
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start >= start_date,
            WeeklyReport.week_end <= end_date
        ]
        
        if child_id:
            conditions.append(WeeklyReport.child_id == child_id)
        
        stmt = (
            select(WeeklyReport)
            .where(and_(*conditions))
            .order_by(desc(WeeklyReport.week_start))
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None
    ) -> Optional[WeeklyReport]:
        """Get latest report for user/child."""
        conditions = [WeeklyReport.user_id == user_id]
        
        if child_id:
            conditions.append(WeeklyReport.child_id == child_id)
        
        stmt = (
            select(WeeklyReport)
            .where(and_(*conditions))
            .order_by(desc(WeeklyReport.week_start))
            .limit(1)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def exists_for_week(
        self,
        user_id: UUID,
        week_start: datetime,
        child_id: Optional[UUID] = None
    ) -> bool:
        """Check if report exists for specific week."""
        conditions = [
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start == week_start
        ]
        
        if child_id:
            conditions.append(WeeklyReport.child_id == child_id)
        
        stmt = select(func.count(WeeklyReport.id)).where(and_(*conditions))
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0


# Note: CheckInRepository implementation would be similar but requires
# the CheckIn database model to be created first