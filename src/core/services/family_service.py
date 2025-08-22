"""Family service for managing children and family members."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user import User, Children, FamilyMember, UserRole
from ..exceptions import (
    ResourceNotFoundError,
    ValidationError,
    BusinessLogicError,
    AuthorizationError
)

logger = logging.getLogger(__name__)


class FamilyService:
    """Service for managing family-related operations."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    # Children management
    
    async def add_child(
        self,
        parent_id: UUID,
        name: str,
        age: int,
        birth_date: Optional[date] = None,
        gender: Optional[str] = None,
        personality_traits: Optional[str] = None,
        special_needs: Optional[str] = None,
        interests: Optional[str] = None
    ) -> Children:
        """
        Add a child to a parent's family.
        
        Args:
            parent_id: UUID of the parent user
            name: Child's name
            age: Child's age
            birth_date: Child's birth date (optional)
            gender: Child's gender (optional)
            personality_traits: Description of child's personality
            special_needs: Any special needs or considerations
            interests: Child's interests and hobbies
            
        Returns:
            Created Children instance
            
        Raises:
            ResourceNotFoundError: If parent doesn't exist
            ValidationError: If child data is invalid
        """
        # Verify parent exists
        parent_stmt = select(User).where(User.id == parent_id)
        parent_result = await self._session.execute(parent_stmt)
        parent = parent_result.scalar_one_or_none()
        
        if not parent:
            raise ResourceNotFoundError(f"Parent user {parent_id} not found")
        
        # Validate age
        if age < 0 or age > 18:
            raise ValidationError("Child age must be between 0 and 18")
        
        # Create child
        child = Children(
            parent_id=parent_id,
            name=name,
            age=age,
            birth_date=birth_date,
            gender=gender,
            personality_traits=personality_traits,
            special_needs=special_needs,
            interests=interests
        )
        
        self._session.add(child)
        await self._session.commit()
        await self._session.refresh(child)
        
        logger.info(f"Added child {child.id} ({name}) to parent {parent_id}")
        return child
    
    async def get_child_by_id(self, child_id: UUID) -> Optional[Children]:
        """Get child by ID."""
        stmt = (
            select(Children)
            .options(selectinload(Children.parent))
            .where(Children.id == child_id)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_children_by_parent(self, parent_id: UUID) -> List[Children]:
        """Get all children for a parent."""
        stmt = (
            select(Children)
            .where(Children.parent_id == parent_id)
            .order_by(Children.name)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_child(
        self,
        child_id: UUID,
        requester_id: UUID,
        name: Optional[str] = None,
        age: Optional[int] = None,
        birth_date: Optional[date] = None,
        gender: Optional[str] = None,
        personality_traits: Optional[str] = None,
        special_needs: Optional[str] = None,
        interests: Optional[str] = None
    ) -> Children:
        """
        Update child information.
        
        Args:
            child_id: Child's UUID
            requester_id: UUID of user making the request
            Other args: Fields to update (optional)
            
        Returns:
            Updated Children instance
            
        Raises:
            ResourceNotFoundError: If child doesn't exist
            AuthorizationError: If requester lacks permissions
            ValidationError: If data is invalid
        """
        child = await self.get_child_by_id(child_id)
        if not child:
            raise ResourceNotFoundError(f"Child {child_id} not found")
        
        # Check permissions
        can_update = await self._can_manage_child(requester_id, child_id)
        if not can_update:
            raise AuthorizationError("Insufficient permissions to update child")
        
        # Update fields
        if name is not None:
            child.name = name
        if age is not None:
            if age < 0 or age > 18:
                raise ValidationError("Child age must be between 0 and 18")
            child.age = age
        if birth_date is not None:
            child.birth_date = birth_date
        if gender is not None:
            child.gender = gender
        if personality_traits is not None:
            child.personality_traits = personality_traits
        if special_needs is not None:
            child.special_needs = special_needs
        if interests is not None:
            child.interests = interests
        
        child.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(child)
        
        logger.info(f"Updated child {child_id} by user {requester_id}")
        return child
    
    async def remove_child(self, child_id: UUID, requester_id: UUID) -> None:
        """
        Remove a child from the system.
        
        Args:
            child_id: Child's UUID
            requester_id: UUID of user making the request
            
        Raises:
            ResourceNotFoundError: If child doesn't exist
            AuthorizationError: If requester lacks permissions
        """
        child = await self.get_child_by_id(child_id)
        if not child:
            raise ResourceNotFoundError(f"Child {child_id} not found")
        
        # Check permissions
        can_manage = await self._can_manage_child(requester_id, child_id)
        if not can_manage:
            raise AuthorizationError("Insufficient permissions to remove child")
        
        # Delete child (cascades to related records)
        stmt = delete(Children).where(Children.id == child_id)
        await self._session.execute(stmt)
        await self._session.commit()
        
        logger.info(f"Removed child {child_id} by user {requester_id}")
    
    # Family members management
    
    async def add_family_member(
        self,
        user_id: UUID,
        telegram_id: int,
        name: str,
        role: UserRole,
        can_view_reports: bool = True,
        can_create_translations: bool = True,
        can_manage_children: bool = False
    ) -> FamilyMember:
        """
        Add a family member to user's family.
        
        Args:
            user_id: UUID of the main user
            telegram_id: Telegram ID of family member
            name: Family member's name
            role: Their role (parent, child, caregiver)
            can_view_reports: Can view weekly reports
            can_create_translations: Can create emotion translations
            can_manage_children: Can manage children information
            
        Returns:
            Created FamilyMember instance
        """
        # Verify main user exists
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self._session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        # Check if family member already exists
        existing_stmt = select(FamilyMember).where(
            FamilyMember.telegram_id == telegram_id
        )
        existing_result = await self._session.execute(existing_stmt)
        existing_member = existing_result.scalar_one_or_none()
        
        if existing_member:
            raise ValidationError(f"Family member with Telegram ID {telegram_id} already exists")
        
        # Create family member
        family_member = FamilyMember(
            user_id=user_id,
            telegram_id=telegram_id,
            name=name,
            role=role,
            can_view_reports=can_view_reports,
            can_create_translations=can_create_translations,
            can_manage_children=can_manage_children
        )
        
        self._session.add(family_member)
        await self._session.commit()
        await self._session.refresh(family_member)
        
        logger.info(f"Added family member {family_member.id} ({name}) to user {user_id}")
        return family_member
    
    async def get_family_member_by_telegram_id(
        self, 
        telegram_id: int
    ) -> Optional[FamilyMember]:
        """Get family member by Telegram ID."""
        stmt = (
            select(FamilyMember)
            .options(selectinload(FamilyMember.user))
            .where(FamilyMember.telegram_id == telegram_id)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_family_members(self, user_id: UUID) -> List[FamilyMember]:
        """Get all family members for a user."""
        stmt = (
            select(FamilyMember)
            .where(FamilyMember.user_id == user_id)
            .order_by(FamilyMember.name)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_family_member_permissions(
        self,
        family_member_id: UUID,
        requester_id: UUID,
        can_view_reports: Optional[bool] = None,
        can_create_translations: Optional[bool] = None,
        can_manage_children: Optional[bool] = None
    ) -> FamilyMember:
        """Update family member permissions."""
        # Get family member
        stmt = select(FamilyMember).where(FamilyMember.id == family_member_id)
        result = await self._session.execute(stmt)
        family_member = result.scalar_one_or_none()
        
        if not family_member:
            raise ResourceNotFoundError(f"Family member {family_member_id} not found")
        
        # Check if requester is the main user
        if family_member.user_id != requester_id:
            raise AuthorizationError("Only the main user can update family member permissions")
        
        # Update permissions
        if can_view_reports is not None:
            family_member.can_view_reports = can_view_reports
        if can_create_translations is not None:
            family_member.can_create_translations = can_create_translations
        if can_manage_children is not None:
            family_member.can_manage_children = can_manage_children
        
        family_member.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        await self._session.refresh(family_member)
        
        logger.info(f"Updated permissions for family member {family_member_id}")
        return family_member
    
    async def remove_family_member(
        self, 
        family_member_id: UUID, 
        requester_id: UUID
    ) -> None:
        """Remove a family member."""
        # Get family member
        stmt = select(FamilyMember).where(FamilyMember.id == family_member_id)
        result = await self._session.execute(stmt)
        family_member = result.scalar_one_or_none()
        
        if not family_member:
            raise ResourceNotFoundError(f"Family member {family_member_id} not found")
        
        # Check if requester is the main user
        if family_member.user_id != requester_id:
            raise AuthorizationError("Only the main user can remove family members")
        
        # Delete family member
        delete_stmt = delete(FamilyMember).where(FamilyMember.id == family_member_id)
        await self._session.execute(delete_stmt)
        await self._session.commit()
        
        logger.info(f"Removed family member {family_member_id}")
    
    # Permission checking helpers
    
    async def _can_manage_child(self, requester_id: UUID, child_id: UUID) -> bool:
        """Check if user can manage a specific child."""
        child = await self.get_child_by_id(child_id)
        if not child:
            return False
        
        # Parent can always manage their own children
        if child.parent_id == requester_id:
            return True
        
        # Check if requester is a family member with permissions
        family_member = await self.get_family_member_by_user_and_family(
            requester_id, child.parent_id
        )
        if family_member and family_member.can_manage_children:
            return True
        
        return False
    
    async def get_family_member_by_user_and_family(
        self, 
        telegram_id: int, 
        family_user_id: UUID
    ) -> Optional[FamilyMember]:
        """Get family member by their telegram ID and the family they belong to."""
        stmt = (
            select(FamilyMember)
            .where(FamilyMember.telegram_id == telegram_id)
            .where(FamilyMember.user_id == family_user_id)
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()