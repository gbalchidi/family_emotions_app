"""Check-in service for scheduled emotional wellness checks."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta, time
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    Checkin, 
    CheckinType, 
    ResponseType, 
    User, 
    Children,
    WeeklyReport
)
from ..core.services import UserService, AnalyticsService
from ..infrastructure.external import ClaudeService
from ..core.exceptions import ResourceNotFoundError, BusinessLogicError
from ..core.config import settings

logger = logging.getLogger(__name__)


class CheckinService:
    """Service for managing scheduled check-ins and emotional wellness tracking."""
    
    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
        analytics_service: AnalyticsService,
        claude_service: ClaudeService
    ):
        self._session = session
        self._user_service = user_service
        self._analytics_service = analytics_service
        self._claude_service = claude_service
        
        # Age-appropriate questions
        self._questions = {
            "toddler": [  # 0-3 years
                "How was your little one's mood today?",
                "Did they have any big feelings today?",
                "What made them happy today?",
                "Were there any challenging moments?",
                "How did they respond to comfort?"
            ],
            "preschool": [  # 4-5 years
                "How did your child express their feelings today?",
                "What activities brought them joy?",
                "Were there any meltdowns or difficult moments?",
                "How did they interact with others?",
                "What helped them feel better when upset?"
            ],
            "school_age": [  # 6-12 years
                "How was your child's emotional day?",
                "What challenged them today?",
                "What are they excited or worried about?",
                "How did they handle their feelings?",
                "What made them proud today?"
            ],
            "teen": [  # 13+ years
                "How has your teenager been feeling lately?",
                "What's been on their mind recently?",
                "How are they coping with stress?",
                "What support do they seem to need?",
                "Have you noticed any mood changes?"
            ]
        }
    
    async def create_scheduled_checkin(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        checkin_type: CheckinType = CheckinType.DAILY,
        scheduled_at: Optional[datetime] = None
    ) -> Checkin:
        """
        Create a scheduled check-in for a user.
        
        Args:
            user_id: User to send check-in to
            child_id: Specific child for the check-in (optional)
            checkin_type: Type of check-in (daily, weekly, etc.)
            scheduled_at: When to send the check-in
            
        Returns:
            Created Checkin instance
        """
        try:
            # Get user and child data
            user = await self._user_service.get_user_by_id(user_id)
            if not user:
                raise ResourceNotFoundError(f"User {user_id} not found")
            
            child = None
            if child_id:
                child_stmt = select(Children).where(Children.id == child_id)
                child_result = await self._session.execute(child_stmt)
                child = child_result.scalar_one_or_none()
                
                if not child or child.parent_id != user_id:
                    raise ResourceNotFoundError(f"Child {child_id} not found for user")
            
            # Generate appropriate question
            question = await self._generate_question(child, checkin_type)
            
            # Set default scheduled time if not provided
            if not scheduled_at:
                scheduled_at = self._get_next_checkin_time(checkin_type)
            
            # Create check-in
            checkin = Checkin(
                user_id=user_id,
                child_id=child_id,
                checkin_type=checkin_type,
                question=question,
                response_type=ResponseType.TEXT,  # Default, can be changed
                scheduled_at=scheduled_at,
                is_completed=False
            )
            
            self._session.add(checkin)
            await self._session.commit()
            await self._session.refresh(checkin)
            
            logger.info(f"Created scheduled check-in {checkin.id} for user {user_id}")
            return checkin
            
        except Exception as e:
            logger.error(f"Error creating scheduled check-in: {e}")
            raise BusinessLogicError(f"Failed to create check-in: {str(e)}")
    
    async def complete_checkin(
        self,
        checkin_id: UUID,
        response_text: str,
        response_type: ResponseType = ResponseType.TEXT,
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> Checkin:
        """
        Complete a check-in with user response.
        
        Args:
            checkin_id: Check-in to complete
            response_text: User's response
            response_type: Type of response (text, voice, emoji, etc.)
            response_metadata: Additional response metadata
            
        Returns:
            Completed Checkin instance
        """
        try:
            # Get check-in
            checkin_stmt = select(Checkin).where(Checkin.id == checkin_id)
            checkin_result = await self._session.execute(checkin_stmt)
            checkin = checkin_result.scalar_one_or_none()
            
            if not checkin:
                raise ResourceNotFoundError(f"Check-in {checkin_id} not found")
            
            if checkin.is_completed:
                raise BusinessLogicError("Check-in already completed")
            
            # Analyze emotional content of response
            emotion_analysis = await self._analyze_checkin_response(
                response_text, 
                checkin
            )
            
            # Update check-in with response
            checkin.response_text = response_text
            checkin.response_type = response_type
            checkin.response_metadata = response_metadata or {}
            checkin.detected_emotions = emotion_analysis.get("emotions", [])
            checkin.emotion_intensity = emotion_analysis.get("intensity", {})
            checkin.mood_score = emotion_analysis.get("mood_score", 0.0)
            checkin.is_completed = True
            checkin.completed_at = datetime.now(timezone.utc)
            
            await self._session.commit()
            await self._session.refresh(checkin)
            
            # Track completion
            await self._analytics_service.track_event(
                event_type="checkin_completed",
                user_id=checkin.user_id,
                event_data={
                    "checkin_id": str(checkin_id),
                    "checkin_type": checkin.checkin_type.value,
                    "response_type": response_type.value,
                    "mood_score": checkin.mood_score,
                    "emotions_detected": len(checkin.detected_emotions or [])
                }
            )
            
            logger.info(f"Completed check-in {checkin_id}")
            return checkin
            
        except Exception as e:
            logger.error(f"Error completing check-in: {e}")
            raise BusinessLogicError(f"Failed to complete check-in: {str(e)}")
    
    async def get_pending_checkins(
        self, 
        user_id: Optional[UUID] = None,
        before: Optional[datetime] = None
    ) -> List[Checkin]:
        """
        Get pending check-ins that should be sent.
        
        Args:
            user_id: Filter by specific user (optional)
            before: Get check-ins scheduled before this time
            
        Returns:
            List of pending Checkin instances
        """
        if not before:
            before = datetime.now(timezone.utc)
        
        stmt = (
            select(Checkin)
            .where(Checkin.is_completed == False)
            .where(Checkin.scheduled_at <= before)
        )
        
        if user_id:
            stmt = stmt.where(Checkin.user_id == user_id)
        
        stmt = stmt.order_by(Checkin.scheduled_at)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_user_checkins(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        days_back: int = 30,
        limit: int = 50
    ) -> List[Checkin]:
        """Get user's recent check-ins."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        stmt = (
            select(Checkin)
            .where(Checkin.user_id == user_id)
            .where(Checkin.created_at >= cutoff_date)
        )
        
        if child_id:
            stmt = stmt.where(Checkin.child_id == child_id)
        
        stmt = (
            stmt
            .order_by(Checkin.created_at.desc())
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def generate_weekly_report(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        week_start: Optional[datetime] = None
    ) -> WeeklyReport:
        """
        Generate a weekly emotional development report.
        
        Args:
            user_id: User to generate report for
            child_id: Specific child (optional)
            week_start: Start of the week to analyze
            
        Returns:
            Generated WeeklyReport instance
        """
        try:
            if not week_start:
                # Default to start of current week (Monday)
                now = datetime.now(timezone.utc)
                days_since_monday = now.weekday()
                week_start = now - timedelta(days=days_since_monday)
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            week_end = week_start + timedelta(days=7)
            
            # Get data for the week
            checkins = await self._get_week_checkins(user_id, child_id, week_start, week_end)
            translations = await self._get_week_translations(user_id, child_id, week_start, week_end)
            
            # Generate report using Claude
            report_data = await self._generate_report_with_claude(
                user_id, child_id, checkins, translations, week_start, week_end
            )
            
            # Create weekly report record
            report = WeeklyReport(
                user_id=user_id,
                child_id=child_id,
                week_start=week_start,
                week_end=week_end,
                summary=report_data["summary"],
                emotion_trends=report_data["emotion_trends"],
                insights=report_data["insights"],
                recommendations=report_data["recommendations"],
                total_checkins=len(checkins),
                total_translations=len(translations),
                average_mood_score=self._calculate_average_mood(checkins),
                generated_at=datetime.now(timezone.utc),
                model_version="claude-3-5-sonnet"
            )
            
            self._session.add(report)
            await self._session.commit()
            await self._session.refresh(report)
            
            # Track report generation
            await self._analytics_service.track_event(
                event_type="report_generated",
                user_id=user_id,
                event_data={
                    "report_id": str(report.id),
                    "child_id": str(child_id) if child_id else None,
                    "week_start": week_start.isoformat(),
                    "total_checkins": len(checkins),
                    "total_translations": len(translations)
                }
            )
            
            logger.info(f"Generated weekly report {report.id} for user {user_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise BusinessLogicError(f"Failed to generate report: {str(e)}")
    
    async def schedule_daily_checkins(self) -> int:
        """
        Schedule daily check-ins for all active users.
        
        Returns:
            Number of check-ins scheduled
        """
        try:
            # Get all active users
            users_stmt = select(User).where(User.is_active == True)
            users_result = await self._session.execute(users_stmt)
            users = list(users_result.scalars().all())
            
            scheduled_count = 0
            
            for user in users:
                try:
                    # Check if user already has a pending daily check-in
                    existing_stmt = (
                        select(Checkin)
                        .where(Checkin.user_id == user.id)
                        .where(Checkin.checkin_type == CheckinType.DAILY)
                        .where(Checkin.is_completed == False)
                    )
                    
                    existing_result = await self._session.execute(existing_stmt)
                    existing_checkin = existing_result.scalar_one_or_none()
                    
                    if existing_checkin:
                        continue  # User already has pending check-in
                    
                    # Schedule check-in for each child or general check-in
                    if user.children:
                        for child in user.children:
                            await self.create_scheduled_checkin(
                                user_id=user.id,
                                child_id=child.id,
                                checkin_type=CheckinType.DAILY
                            )
                            scheduled_count += 1
                    else:
                        # General check-in for users without children
                        await self.create_scheduled_checkin(
                            user_id=user.id,
                            checkin_type=CheckinType.DAILY
                        )
                        scheduled_count += 1
                
                except Exception as e:
                    logger.error(f"Error scheduling check-in for user {user.id}: {e}")
                    continue
            
            logger.info(f"Scheduled {scheduled_count} daily check-ins")
            return scheduled_count
            
        except Exception as e:
            logger.error(f"Error in schedule_daily_checkins: {e}")
            return 0
    
    async def _generate_question(
        self, 
        child: Optional[Children], 
        checkin_type: CheckinType
    ) -> str:
        """Generate an appropriate question based on child's age and check-in type."""
        if not child:
            return "How are your children doing emotionally today?"
        
        # Determine age category
        if child.age <= 3:
            age_category = "toddler"
        elif child.age <= 5:
            age_category = "preschool"
        elif child.age <= 12:
            age_category = "school_age"
        else:
            age_category = "teen"
        
        # Get questions for age category
        questions = self._questions.get(age_category, self._questions["school_age"])
        
        # Add child's name to question
        question = random.choice(questions)
        if child.name:
            question = question.replace("your child", child.name).replace("they", child.name)
        
        return question
    
    def _get_next_checkin_time(self, checkin_type: CheckinType) -> datetime:
        """Calculate next check-in time based on type and user settings."""
        now = datetime.now(timezone.utc)
        
        if checkin_type == CheckinType.DAILY:
            # Default daily check-in times from settings
            checkin_times = settings.checkin_times
            default_time = checkin_times[0] if checkin_times else "18:00"
            
            # Parse time
            hour, minute = map(int, default_time.split(":"))
            
            # Schedule for today if time hasn't passed, otherwise tomorrow
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled_time <= now:
                scheduled_time += timedelta(days=1)
            
            return scheduled_time
        
        elif checkin_type == CheckinType.WEEKLY:
            # Schedule for configured day of week
            days_until_target = (settings.weekly_report_day - now.weekday()) % 7
            if days_until_target == 0:
                days_until_target = 7  # Next week if today is the target day
            
            return now + timedelta(days=days_until_target)
        
        else:
            # Default to next day for other types
            return now + timedelta(days=1)
    
    async def _analyze_checkin_response(
        self, 
        response_text: str, 
        checkin: Checkin
    ) -> Dict[str, Any]:
        """Analyze emotional content of check-in response."""
        try:
            # Simple sentiment analysis for now
            # In a real implementation, you might use Claude or another service
            
            positive_words = ["happy", "good", "great", "wonderful", "excited", "proud", "joyful"]
            negative_words = ["sad", "angry", "frustrated", "upset", "worried", "scared", "difficult"]
            
            text_lower = response_text.lower()
            
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            # Calculate mood score (-1 to 1)
            if positive_count == 0 and negative_count == 0:
                mood_score = 0.0  # Neutral
            else:
                mood_score = (positive_count - negative_count) / (positive_count + negative_count + 1)
            
            # Convert to 1-5 scale
            mood_score_5 = ((mood_score + 1) / 2) * 4 + 1  # Convert to 1-5 scale
            
            # Detect basic emotions
            detected_emotions = []
            if any(word in text_lower for word in ["happy", "joy", "excited", "proud"]):
                detected_emotions.append("happy")
            if any(word in text_lower for word in ["sad", "disappointed", "down"]):
                detected_emotions.append("sad")
            if any(word in text_lower for word in ["angry", "frustrated", "mad"]):
                detected_emotions.append("angry")
            if any(word in text_lower for word in ["worried", "anxious", "scared"]):
                detected_emotions.append("anxious")
            
            return {
                "emotions": detected_emotions,
                "intensity": {emotion: 0.7 for emotion in detected_emotions},
                "mood_score": mood_score_5
            }
            
        except Exception as e:
            logger.error(f"Error analyzing check-in response: {e}")
            return {
                "emotions": [],
                "intensity": {},
                "mood_score": 3.0  # Neutral default
            }
    
    async def _get_week_checkins(
        self,
        user_id: UUID,
        child_id: Optional[UUID],
        week_start: datetime,
        week_end: datetime
    ) -> List[Checkin]:
        """Get check-ins for a specific week."""
        stmt = (
            select(Checkin)
            .where(Checkin.user_id == user_id)
            .where(Checkin.created_at >= week_start)
            .where(Checkin.created_at < week_end)
            .where(Checkin.is_completed == True)
        )
        
        if child_id:
            stmt = stmt.where(Checkin.child_id == child_id)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_week_translations(
        self,
        user_id: UUID,
        child_id: Optional[UUID],
        week_start: datetime,
        week_end: datetime
    ) -> List:
        """Get emotion translations for a specific week."""
        from ..core.models import EmotionTranslation, TranslationStatus
        
        stmt = (
            select(EmotionTranslation)
            .where(EmotionTranslation.user_id == user_id)
            .where(EmotionTranslation.created_at >= week_start)
            .where(EmotionTranslation.created_at < week_end)
            .where(EmotionTranslation.status == TranslationStatus.COMPLETED)
        )
        
        if child_id:
            stmt = stmt.where(EmotionTranslation.child_id == child_id)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def _generate_report_with_claude(
        self,
        user_id: UUID,
        child_id: Optional[UUID],
        checkins: List[Checkin],
        translations: List,
        week_start: datetime,
        week_end: datetime
    ) -> Dict[str, Any]:
        """Generate report content using Claude API."""
        try:
            # Get child info
            child_name = "your child"
            child_age = 7
            
            if child_id:
                child_stmt = select(Children).where(Children.id == child_id)
                child_result = await self._session.execute(child_stmt)
                child = child_result.scalar_one_or_none()
                if child:
                    child_name = child.name
                    child_age = child.age
            
            # Prepare data summaries
            checkin_data = []
            for checkin in checkins:
                checkin_data.append({
                    "question": checkin.question,
                    "response": checkin.response_text,
                    "mood_score": checkin.mood_score,
                    "emotions": checkin.detected_emotions or [],
                    "date": checkin.completed_at.strftime("%Y-%m-%d") if checkin.completed_at else None
                })
            
            translation_data = []
            for translation in translations:
                translation_data.append({
                    "message": translation.original_message,
                    "emotions": translation.translated_emotions or [],
                    "confidence": translation.confidence_score,
                    "date": translation.created_at.strftime("%Y-%m-%d")
                })
            
            # Use Claude service to generate report
            report = await self._claude_service.generate_weekly_report(
                child_name=child_name,
                child_age=child_age,
                emotion_data=translation_data,
                checkin_data=checkin_data,
                period_start=week_start.strftime("%Y-%m-%d"),
                period_end=week_end.strftime("%Y-%m-%d")
            )
            
            # Calculate emotion trends
            emotion_counts = {}
            for checkin in checkins:
                for emotion in checkin.detected_emotions or []:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            for translation in translations:
                for emotion in translation.translated_emotions or []:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            return {
                "summary": report.get("summary", "Weekly summary not available"),
                "emotion_trends": emotion_counts,
                "insights": [report.get("insights", "No insights available")],
                "recommendations": report.get("recommendations", ["Continue monitoring emotional development"])
            }
            
        except Exception as e:
            logger.error(f"Error generating Claude report: {e}")
            # Fallback to basic report
            return {
                "summary": f"Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}. Completed {len(checkins)} check-ins and {len(translations)} emotion translations.",
                "emotion_trends": {},
                "insights": ["Continue monitoring your child's emotional development."],
                "recommendations": ["Keep using regular check-ins", "Continue emotion translation practice"]
            }
    
    def _calculate_average_mood(self, checkins: List[Checkin]) -> Optional[float]:
        """Calculate average mood score from check-ins."""
        mood_scores = [c.mood_score for c in checkins if c.mood_score is not None]
        return sum(mood_scores) / len(mood_scores) if mood_scores else None