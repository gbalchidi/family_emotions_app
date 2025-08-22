"""Main emotion service that orchestrates emotion analysis and storage."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .claude_service import ClaudeService, EmotionAnalysisRequest
from ...core.models.emotion import EmotionTranslation, TranslationStatus
from ...core.models.user import User, Children
from ...core.services import UserService, AnalyticsService
from ...core.exceptions import (
    ResourceNotFoundError,
    RateLimitExceededError,
    ExternalServiceError,
    BusinessLogicError
)
from ...core.models.analytics import EventType

logger = logging.getLogger(__name__)


class EmotionService:
    """High-level service for emotion analysis and translation."""
    
    def __init__(
        self, 
        session: AsyncSession,
        claude_service: ClaudeService,
        user_service: UserService,
        analytics_service: AnalyticsService
    ):
        self._session = session
        self._claude_service = claude_service
        self._user_service = user_service
        self._analytics_service = analytics_service
    
    async def create_emotion_translation(
        self,
        user_id: UUID,
        child_message: str,
        child_id: Optional[UUID] = None,
        situation_context: Optional[str] = None
    ) -> EmotionTranslation:
        """
        Create and process an emotion translation request.
        
        Args:
            user_id: User requesting the translation
            child_message: The child's message or behavior description
            child_id: ID of the specific child (optional)
            situation_context: Additional context about the situation
            
        Returns:
            EmotionTranslation instance with results
            
        Raises:
            ResourceNotFoundError: If user or child not found
            RateLimitExceededError: If user has exceeded daily limits
            BusinessLogicError: If child data is insufficient
        """
        try:
            # Check user's daily limit
            await self._user_service.check_daily_limit(user_id)
            
            # Get user and child data
            user = await self._user_service.get_user_by_id(user_id)
            if not user:
                raise ResourceNotFoundError(f"User {user_id} not found")
            
            child = None
            if child_id:
                child_stmt = select(Children).where(Children.id == child_id)
                child_result = await self._session.execute(child_stmt)
                child = child_result.scalar_one_or_none()
                
                if not child:
                    raise ResourceNotFoundError(f"Child {child_id} not found")
                
                # Verify child belongs to user
                if child.parent_id != user_id:
                    raise BusinessLogicError("Child does not belong to this user")
            
            # Create initial translation record
            translation = EmotionTranslation(
                user_id=user_id,
                child_id=child_id,
                original_message=child_message,
                situation_context=situation_context,
                status=TranslationStatus.PENDING
            )
            
            self._session.add(translation)
            await self._session.commit()
            await self._session.refresh(translation)
            
            # Track analytics
            await self._analytics_service.track_event(
                event_type=EventType.TRANSLATION_REQUEST,
                user_id=user_id,
                user_telegram_id=user.telegram_id,
                event_data={
                    "translation_id": str(translation.id),
                    "has_child_context": child is not None,
                    "has_situation_context": situation_context is not None
                }
            )
            
            # Process the translation asynchronously
            await self._process_translation(translation, user, child)
            
            # Increment user's request count
            await self._user_service.increment_request_count(user_id)
            
            return translation
            
        except (RateLimitExceededError, ResourceNotFoundError, BusinessLogicError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Error creating emotion translation: {e}")
            
            # Track error
            await self._analytics_service.track_event(
                event_type=EventType.ERROR_OCCURRED,
                user_id=user_id,
                error_code="TRANSLATION_CREATION_FAILED",
                error_message=str(e)
            )
            
            raise ExternalServiceError(
                f"Failed to create emotion translation: {str(e)}",
                service_name="EmotionService"
            )
    
    async def _process_translation(
        self,
        translation: EmotionTranslation,
        user: User,
        child: Optional[Children] = None
    ) -> None:
        """Process the emotion translation using Claude API."""
        try:
            # Update status to processing
            translation.status = TranslationStatus.PROCESSING
            await self._session.commit()
            
            # Prepare request for Claude
            child_name = child.name if child else "the child"
            child_age = child.age if child else 7  # Default age if no child specified
            
            # Build child context
            child_context = ""
            if child:
                if child.personality_traits:
                    child_context += f"Personality: {child.personality_traits}. "
                if child.interests:
                    child_context += f"Interests: {child.interests}. "
                if child.special_needs:
                    child_context += f"Special considerations: {child.special_needs}. "
            
            request = EmotionAnalysisRequest(
                child_message=translation.original_message,
                child_age=child_age,
                child_name=child_name,
                situation_context=translation.situation_context,
                personality_traits=child.personality_traits if child else None,
                special_needs=child.special_needs if child else None,
                interests=child.interests if child else None
            )
            
            # Call Claude API
            start_time = datetime.now(timezone.utc)
            analysis_result = await self._claude_service.analyze_child_emotions(request)
            
            # Update translation with results
            translation.translated_emotions = analysis_result.detected_emotions
            translation.response_options = [
                {
                    "title": resp["title"],
                    "text": resp["text"],
                    "approach": resp["approach"]
                }
                for resp in analysis_result.response_options
            ]
            translation.confidence_score = analysis_result.confidence_score
            translation.processing_time_ms = analysis_result.processing_time_ms
            translation.status = TranslationStatus.COMPLETED
            translation.model_version = "claude-3-5-sonnet"
            translation.prompt_version = "v1.0"
            
            await self._session.commit()
            
            # Track successful completion
            await self._analytics_service.track_event(
                event_type=EventType.TRANSLATION_REQUEST,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                event_data={
                    "translation_id": str(translation.id),
                    "status": "completed",
                    "emotions_detected": len(analysis_result.detected_emotions),
                    "confidence_score": analysis_result.confidence_score
                },
                response_time_ms=analysis_result.processing_time_ms
            )
            
            logger.info(f"Successfully processed translation {translation.id}")
            
        except RateLimitExceededError as e:
            # Handle rate limiting
            translation.status = TranslationStatus.FAILED
            translation.error_message = "Rate limit exceeded. Please try again later."
            await self._session.commit()
            
            await self._analytics_service.track_event(
                event_type=EventType.ERROR_OCCURRED,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                error_code="RATE_LIMIT_EXCEEDED",
                error_message=str(e)
            )
            
            logger.warning(f"Rate limit exceeded for translation {translation.id}")
            raise
            
        except ExternalServiceError as e:
            # Handle Claude API errors
            translation.status = TranslationStatus.FAILED
            translation.error_message = "AI service temporarily unavailable. Please try again later."
            await self._session.commit()
            
            await self._analytics_service.track_event(
                event_type=EventType.ERROR_OCCURRED,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                error_code="CLAUDE_API_ERROR", 
                error_message=str(e)
            )
            
            logger.error(f"Claude API error for translation {translation.id}: {e}")
            raise
            
        except Exception as e:
            # Handle unexpected errors
            translation.status = TranslationStatus.FAILED
            translation.error_message = "An unexpected error occurred. Please try again."
            await self._session.commit()
            
            await self._analytics_service.track_event(
                event_type=EventType.ERROR_OCCURRED,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                error_code="TRANSLATION_PROCESSING_ERROR",
                error_message=str(e)
            )
            
            logger.error(f"Unexpected error processing translation {translation.id}: {e}")
            raise ExternalServiceError(
                f"Failed to process emotion translation: {str(e)}",
                service_name="EmotionService"
            )
    
    async def get_user_translations(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        child_id: Optional[UUID] = None
    ) -> List[EmotionTranslation]:
        """Get user's emotion translations with pagination."""
        query = (
            select(EmotionTranslation)
            .where(EmotionTranslation.user_id == user_id)
        )
        
        if child_id:
            query = query.where(EmotionTranslation.child_id == child_id)
        
        query = (
            query
            .order_by(EmotionTranslation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_translation_by_id(
        self, 
        translation_id: UUID
    ) -> Optional[EmotionTranslation]:
        """Get a specific translation by ID."""
        stmt = select(EmotionTranslation).where(EmotionTranslation.id == translation_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_emotion_statistics(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        days_back: int = 30
    ) -> Dict[str, int]:
        """
        Get emotion statistics for a user or specific child.
        
        Args:
            user_id: User's UUID
            child_id: Specific child's UUID (optional)
            days_back: How many days to look back
            
        Returns:
            Dictionary with emotion counts
        """
        # Get completed translations
        translations = await self.get_user_translations(
            user_id=user_id,
            child_id=child_id,
            limit=1000  # Get more for statistics
        )
        
        # Filter by date and completion status
        from datetime import datetime, timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        recent_translations = [
            t for t in translations 
            if (t.created_at >= cutoff_date and 
                t.status == TranslationStatus.COMPLETED and
                t.translated_emotions)
        ]
        
        # Count emotions
        emotion_counts = {}
        for translation in recent_translations:
            for emotion in translation.translated_emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        return emotion_counts
    
    async def retry_failed_translation(
        self, 
        translation_id: UUID
    ) -> EmotionTranslation:
        """Retry a failed translation."""
        translation = await self.get_translation_by_id(translation_id)
        if not translation:
            raise ResourceNotFoundError(f"Translation {translation_id} not found")
        
        if translation.status != TranslationStatus.FAILED:
            raise BusinessLogicError("Can only retry failed translations")
        
        # Get user and child data
        user = await self._user_service.get_user_by_id(translation.user_id)
        if not user:
            raise ResourceNotFoundError(f"User {translation.user_id} not found")
        
        child = None
        if translation.child_id:
            child_stmt = select(Children).where(Children.id == translation.child_id)
            child_result = await self._session.execute(child_stmt)
            child = child_result.scalar_one_or_none()
        
        # Check rate limits again
        await self._user_service.check_daily_limit(translation.user_id)
        
        # Reset translation status and process again
        translation.status = TranslationStatus.PENDING
        translation.error_message = None
        translation.updated_at = datetime.now(timezone.utc)
        
        await self._session.commit()
        
        # Process the translation
        await self._process_translation(translation, user, child)
        
        return translation