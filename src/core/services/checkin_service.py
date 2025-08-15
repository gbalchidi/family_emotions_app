"""Check-in service for Family Emotions App."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from src.core.domain.entities import CheckIn
from src.core.domain.exceptions import CheckInException, RateLimitExceededException
from src.core.domain.value_objects import Age, CheckInQuestion, EmotionContext, MoodScore
from src.core.repositories.interfaces import CheckInRepository, UserRepository
from src.core.services.emotion_translator_service import EmotionTranslatorService

logger = logging.getLogger(__name__)


class CheckInQuestionBank:
    """Bank of check-in questions for different age groups and categories."""
    
    QUESTIONS = {
        "mood": {
            "toddler": [
                CheckInQuestion(
                    text="How are you feeling today? Happy, sad, or angry?",
                    category="mood",
                    age_groups=["toddler"],
                    follow_up_prompts=["Can you show me with your face?", "What made you feel this way?"]
                ),
                CheckInQuestion(
                    text="Are you feeling good or not so good?",
                    category="mood",
                    age_groups=["toddler", "preschooler"]
                )
            ],
            "preschooler": [
                CheckInQuestion(
                    text="What emotion are you feeling right now?",
                    category="mood",
                    age_groups=["preschooler", "early_school"],
                    follow_up_prompts=["Tell me more about that feeling", "When did you start feeling this way?"]
                ),
                CheckInQuestion(
                    text="How would you describe your mood today?",
                    category="mood",
                    age_groups=["preschooler", "early_school", "middle_school"]
                )
            ],
            "early_school": [
                CheckInQuestion(
                    text="On a scale from very sad to very happy, how are you feeling?",
                    category="mood",
                    age_groups=["early_school", "middle_school", "teenager"],
                    follow_up_prompts=["What's contributing to this feeling?", "Has this feeling changed throughout the day?"]
                ),
                CheckInQuestion(
                    text="What three words would describe how you're feeling today?",
                    category="mood",
                    age_groups=["early_school", "middle_school", "teenager"]
                )
            ],
            "middle_school": [
                CheckInQuestion(
                    text="How has your emotional state been lately?",
                    category="mood",
                    age_groups=["middle_school", "teenager"],
                    follow_up_prompts=["What factors are influencing this?", "How does this compare to last week?"]
                )
            ],
            "teenager": [
                CheckInQuestion(
                    text="How are you processing your emotions today?",
                    category="mood",
                    age_groups=["teenager"],
                    follow_up_prompts=["What strategies have been helpful?", "What's been challenging emotionally?"]
                )
            ]
        },
        "behavior": {
            "toddler": [
                CheckInQuestion(
                    text="Were you a good listener today?",
                    category="behavior",
                    age_groups=["toddler", "preschooler"]
                )
            ],
            "preschooler": [
                CheckInQuestion(
                    text="How did you handle big feelings today?",
                    category="behavior",
                    age_groups=["preschooler", "early_school"]
                )
            ],
            "early_school": [
                CheckInQuestion(
                    text="What was challenging for you today, and how did you deal with it?",
                    category="behavior",
                    age_groups=["early_school", "middle_school"]
                )
            ],
            "middle_school": [
                CheckInQuestion(
                    text="How did you manage stress or difficult situations today?",
                    category="behavior",
                    age_groups=["middle_school", "teenager"]
                )
            ]
        },
        "social": {
            "preschooler": [
                CheckInQuestion(
                    text="Who did you play with today?",
                    category="social",
                    age_groups=["preschooler", "early_school"],
                    follow_up_prompts=["How did it make you feel?", "What did you enjoy about playing together?"]
                )
            ],
            "early_school": [
                CheckInQuestion(
                    text="How did you get along with friends and family today?",
                    category="social",
                    age_groups=["early_school", "middle_school"]
                )
            ],
            "middle_school": [
                CheckInQuestion(
                    text="How are your relationships with friends and family going?",
                    category="social",
                    age_groups=["middle_school", "teenager"]
                )
            ]
        }
    }
    
    @classmethod
    def get_appropriate_questions(
        self,
        age: Age,
        category: str = "mood",
        count: int = 1
    ) -> List[CheckInQuestion]:
        """Get appropriate questions for age and category."""
        age_group = age.to_age_group()
        
        # Get questions for this age group and category
        category_questions = self.QUESTIONS.get(category, {})
        
        # Collect all appropriate questions
        appropriate_questions = []
        for group, questions in category_questions.items():
            if group == age_group or age_group in [q.age_groups for q in questions if age_group in q.age_groups]:
                for question in questions:
                    if question.is_appropriate_for_age(age):
                        appropriate_questions.append(question)
        
        # If no specific questions found, use general mood questions
        if not appropriate_questions and category == "mood":
            appropriate_questions = [
                CheckInQuestion(
                    text="How are you feeling today?",
                    category="mood",
                    age_groups=[age_group],
                    follow_up_prompts=["Tell me more about that"]
                )
            ]
        
        return appropriate_questions[:count]


class CheckInService:
    """Service for managing emotional check-ins with children."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        checkin_repository: CheckInRepository,
        emotion_translator_service: EmotionTranslatorService
    ):
        self.user_repository = user_repository
        self.checkin_repository = checkin_repository
        self.emotion_translator_service = emotion_translator_service
        self.question_bank = CheckInQuestionBank()
    
    async def schedule_checkin(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        scheduled_at: Optional[datetime] = None,
        category: str = "mood",
        custom_question: Optional[str] = None
    ) -> CheckIn:
        """
        Schedule a check-in for a user/child.
        
        Args:
            user_id: User ID
            child_id: Optional child ID
            scheduled_at: When to schedule the check-in
            category: Question category (mood, behavior, social)
            custom_question: Custom question text
            
        Returns:
            Scheduled CheckIn entity
        """
        # Get user and check limits
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise CheckInException("User not found")
        
        if not user.can_make_request("checkin"):
            raise RateLimitExceededException("daily")
        
        # Get child context if provided
        age = Age(value=7)  # Default age
        if child_id:
            child = user.get_child(child_id)
            if not child:
                raise CheckInException("Child not found")
            age = child.age
        
        # Generate or use provided question
        if custom_question:
            question = CheckInQuestion(
                text=custom_question,
                category=category,
                age_groups=[age.to_age_group()]
            )
        else:
            questions = self.question_bank.get_appropriate_questions(age, category)
            if not questions:
                raise CheckInException(f"No appropriate questions found for age {age.value}")
            question = questions[0]
        
        # Set default schedule time if not provided
        if not scheduled_at:
            scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        # Create check-in entity
        checkin = CheckIn(
            user_id=user_id,
            child_id=child_id,
            question=question,
            scheduled_at=scheduled_at
        )
        
        # Save check-in
        await self.checkin_repository.save(checkin)
        
        logger.info(f"Scheduled check-in for user {user_id}, child {child_id}")
        return checkin
    
    async def complete_checkin(
        self,
        checkin_id: UUID,
        response_text: str,
        analyze_emotions: bool = True
    ) -> CheckIn:
        """
        Complete a check-in with user response.
        
        Args:
            checkin_id: Check-in ID
            response_text: User's response
            analyze_emotions: Whether to analyze emotions in response
            
        Returns:
            Completed CheckIn entity
        """
        # Get check-in
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInException("Check-in not found")
        
        if checkin.is_completed:
            raise CheckInException("Check-in already completed")
        
        # Analyze emotions if requested
        detected_emotions = []
        mood_score = MoodScore(value=0)
        
        if analyze_emotions and response_text.strip():
            try:
                # Use emotion translator to analyze response
                translation = await self.emotion_translator_service.translate_emotion(
                    user_id=checkin.user_id,
                    message=response_text,
                    child_id=checkin.child_id,
                    use_cache=True
                )
                
                # Extract emotions and mood score
                detected_emotions = [insight.emotion for insight in translation.insights]
                mood_score = translation.mood_score or MoodScore(value=0)
                
            except Exception as e:
                logger.warning(f"Failed to analyze emotions for check-in {checkin_id}: {str(e)}")
                # Continue with empty analysis rather than failing
        
        # Complete the check-in
        checkin.complete(response_text, detected_emotions, mood_score)
        
        # Save updated check-in
        await self.checkin_repository.update(checkin)
        
        logger.info(f"Completed check-in {checkin_id}")
        return checkin
    
    async def get_pending_checkins(self, user_id: UUID) -> List[CheckIn]:
        """Get pending check-ins for a user."""
        return await self.checkin_repository.get_pending(user_id)
    
    async def get_overdue_checkins(self) -> List[CheckIn]:
        """Get all overdue check-ins."""
        return await self.checkin_repository.get_overdue()
    
    async def get_checkin_history(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        days: int = 7,
        completed_only: bool = True
    ) -> List[CheckIn]:
        """Get check-in history for user/child."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        return await self.checkin_repository.get_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            child_id=child_id
        )
    
    async def analyze_checkin_patterns(
        self,
        user_id: UUID,
        child_id: UUID,
        days: int = 30
    ) -> Dict[str, any]:
        """Analyze check-in patterns and trends."""
        checkins = await self.get_checkin_history(
            user_id=user_id,
            child_id=child_id,
            days=days,
            completed_only=True
        )
        
        if not checkins:
            return {
                "total_checkins": 0,
                "completion_rate": 0,
                "average_mood": 0,
                "mood_trend": "insufficient_data",
                "insights": []
            }
        
        # Calculate metrics
        total_checkins = len(checkins)
        completed_checkins = [c for c in checkins if c.is_completed]
        completion_rate = len(completed_checkins) / total_checkins if total_checkins > 0 else 0
        
        # Mood analysis
        mood_scores = [c.mood_score.value for c in completed_checkins if c.mood_score]
        average_mood = float(sum(mood_scores) / len(mood_scores)) if mood_scores else 0
        
        # Trend analysis
        mood_trend = "stable"
        if len(mood_scores) >= 7:
            recent_scores = mood_scores[:min(3, len(mood_scores))]
            older_scores = mood_scores[-min(3, len(mood_scores)):]
            
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            
            if recent_avg > older_avg + 0.2:
                mood_trend = "improving"
            elif recent_avg < older_avg - 0.2:
                mood_trend = "declining"
        
        # Emotion frequency
        emotion_counts = {}
        for checkin in completed_checkins:
            for emotion in checkin.detected_emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Generate insights
        insights = self._generate_checkin_insights(
            completion_rate,
            average_mood,
            mood_trend,
            emotion_counts
        )
        
        return {
            "total_checkins": total_checkins,
            "completed_checkins": len(completed_checkins),
            "completion_rate": completion_rate,
            "average_mood": average_mood,
            "mood_trend": mood_trend,
            "emotion_frequency": emotion_counts,
            "insights": insights
        }
    
    def _generate_checkin_insights(
        self,
        completion_rate: float,
        average_mood: float,
        mood_trend: str,
        emotion_counts: Dict[str, int]
    ) -> List[str]:
        """Generate insights from check-in patterns."""
        insights = []
        
        # Completion rate insights
        if completion_rate < 0.5:
            insights.append("Low check-in completion rate. Consider adjusting timing or question style.")
        elif completion_rate > 0.8:
            insights.append("Excellent check-in engagement! Keep up the consistent routine.")
        
        # Mood insights
        if average_mood < -0.3:
            insights.append("Check-ins show concerning mood patterns. Consider professional support.")
        elif average_mood > 0.3:
            insights.append("Overall mood is positive based on check-ins.")
        
        # Trend insights
        if mood_trend == "improving":
            insights.append("Mood trend is improving over time - great progress!")
        elif mood_trend == "declining":
            insights.append("Mood trend shows decline. Increased support may be helpful.")
        
        # Emotion pattern insights
        if emotion_counts:
            most_common = max(emotion_counts.items(), key=lambda x: x[1])
            insights.append(f"Most frequently expressed emotion: {most_common[0]}")
            
            # Check for concerning emotions
            concerning = ["sadness", "anger", "fear", "anxiety"]
            concerning_count = sum(
                count for emotion, count in emotion_counts.items()
                if emotion.lower() in concerning
            )
            
            if concerning_count > sum(emotion_counts.values()) * 0.6:
                insights.append("High frequency of concerning emotions in check-ins.")
        
        return insights
    
    async def skip_checkin(self, checkin_id: UUID, reason: str = "Skipped by user") -> CheckIn:
        """Skip a check-in."""
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInException("Check-in not found")
        
        checkin.skip(reason)
        await self.checkin_repository.update(checkin)
        
        logger.info(f"Skipped check-in {checkin_id}: {reason}")
        return checkin
    
    async def reschedule_checkin(
        self,
        checkin_id: UUID,
        new_scheduled_at: datetime
    ) -> CheckIn:
        """Reschedule a check-in."""
        checkin = await self.checkin_repository.get_by_id(checkin_id)
        if not checkin:
            raise CheckInException("Check-in not found")
        
        if checkin.is_completed:
            raise CheckInException("Cannot reschedule completed check-in")
        
        checkin.scheduled_at = new_scheduled_at
        await self.checkin_repository.update(checkin)
        
        logger.info(f"Rescheduled check-in {checkin_id} to {new_scheduled_at}")
        return checkin