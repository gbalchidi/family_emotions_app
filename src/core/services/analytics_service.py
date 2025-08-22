"""Analytics service for generating emotional insights and reports."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

from src.core.domain.exceptions import DomainException
from src.core.models.emotion import WeeklyReport
from src.core.repositories.interfaces import (
    CheckInRepository,
    EmotionTranslationRepository,
    UserRepository,
    WeeklyReportRepository
)
# Type import to avoid circular dependency
if TYPE_CHECKING:
    from src.infrastructure.external.claude_service import ClaudeService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and reports."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        checkin_repository: CheckInRepository,
        translation_repository: EmotionTranslationRepository,
        report_repository: WeeklyReportRepository,
        claude_service: "ClaudeService"
    ):
        self.user_repository = user_repository
        self.checkin_repository = checkin_repository
        self.translation_repository = translation_repository
        self.report_repository = report_repository
        self.claude_service = claude_service
    
    async def generate_weekly_report(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        week_start: Optional[datetime] = None
    ) -> WeeklyReport:
        """
        Generate a comprehensive weekly emotional report.
        
        Args:
            user_id: User ID
            child_id: Optional child ID for child-specific report
            week_start: Start of week (defaults to last Monday)
            
        Returns:
            Generated WeeklyReport
        """
        # Get user and check permissions
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise DomainException("User not found")
        
        if not user.subscription_plan.get("weekly_reports", False):
            raise DomainException("Weekly reports not available on current plan")
        
        # Calculate week boundaries
        if not week_start:
            now = datetime.now(timezone.utc)
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Check if report already exists
        existing_report = await self.report_repository.exists_for_week(
            user_id=user_id,
            week_start=week_start,
            child_id=child_id
        )
        
        if existing_report:
            logger.info(f"Weekly report already exists for user {user_id}, week {week_start}")
            return await self.report_repository.get_latest(user_id, child_id)
        
        # Collect data for the week
        checkins = await self.checkin_repository.get_by_date_range(
            user_id=user_id,
            start_date=week_start,
            end_date=week_end,
            child_id=child_id
        )
        
        translations = await self.translation_repository.get_recent(
            user_id=user_id,
            days=7
        )
        
        # Filter translations by child if specified
        if child_id:
            translations = [t for t in translations if t.child_id == child_id]
        
        # Analyze data
        analysis = await self._analyze_weekly_data(checkins, translations)
        
        # Generate AI insights
        ai_insights = await self._generate_ai_insights(checkins, translations, user, child_id)
        
        # Create report
        report = WeeklyReport(
            user_id=user_id,
            child_id=child_id,
            week_start=week_start,
            week_end=week_end,
            summary=analysis["summary"],
            emotion_trends=analysis["emotion_trends"],
            insights=ai_insights["insights"],
            recommendations=ai_insights["recommendations"],
            total_checkins=len(checkins),
            total_translations=len(translations),
            average_mood_score=analysis["average_mood"],
            generated_at=datetime.now(timezone.utc),
            model_version="claude-3-5-sonnet-20241022"
        )
        
        # Save report
        await self.report_repository.save(report)
        
        logger.info(f"Generated weekly report for user {user_id}")
        return report
    
    async def _analyze_weekly_data(
        self,
        checkins: List,
        translations: List
    ) -> Dict[str, any]:
        """Analyze weekly data for patterns and trends."""
        # Emotion frequency analysis
        emotion_counts = {}
        mood_scores = []
        
        # Analyze check-ins
        for checkin in checkins:
            if checkin.is_completed:
                if checkin.mood_score:
                    mood_scores.append(float(checkin.mood_score.value))
                
                for emotion in checkin.detected_emotions:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Analyze translations
        for translation in translations:
            if translation.mood_score:
                mood_scores.append(float(translation.mood_score.value))
            
            for insight in translation.insights:
                emotion = insight.emotion
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Calculate averages and trends
        average_mood = sum(mood_scores) / len(mood_scores) if mood_scores else 0
        
        # Normalize emotion frequencies to percentages
        total_emotions = sum(emotion_counts.values())
        emotion_trends = {
            emotion: count / total_emotions
            for emotion, count in emotion_counts.items()
        } if total_emotions > 0 else {}
        
        # Generate summary
        summary = self._generate_summary(checkins, translations, average_mood, emotion_trends)
        
        return {
            "summary": summary,
            "emotion_trends": emotion_trends,
            "average_mood": average_mood,
            "mood_scores": mood_scores,
            "total_interactions": len(checkins) + len(translations)
        }
    
    def _generate_summary(
        self,
        checkins: List,
        translations: List,
        average_mood: float,
        emotion_trends: Dict[str, float]
    ) -> str:
        """Generate a human-readable summary of the week."""
        total_interactions = len(checkins) + len(translations)
        
        if total_interactions == 0:
            return "No emotional data recorded this week."
        
        # Mood description
        if average_mood > 0.3:
            mood_desc = "predominantly positive"
        elif average_mood < -0.3:
            mood_desc = "predominantly negative"
        else:
            mood_desc = "generally neutral"
        
        # Top emotions
        if emotion_trends:
            top_emotions = sorted(emotion_trends.items(), key=lambda x: x[1], reverse=True)[:3]
            emotion_desc = ", ".join([f"{emotion} ({pct:.1%})" for emotion, pct in top_emotions])
        else:
            emotion_desc = "varied emotions"
        
        summary = (
            f"This week recorded {total_interactions} emotional interactions with {mood_desc} mood patterns. "
            f"The most frequent emotions were: {emotion_desc}."
        )
        
        return summary
    
    async def _generate_ai_insights(
        self,
        checkins: List,
        translations: List,
        user,
        child_id: Optional[UUID]
    ) -> Dict[str, List[str]]:
        """Generate AI-powered insights and recommendations."""
        # Prepare data for AI analysis
        data_summary = {
            "total_checkins": len(checkins),
            "total_translations": len(translations),
            "completed_checkins": len([c for c in checkins if c.is_completed]),
            "mood_scores": [float(c.mood_score.value) for c in checkins if c.mood_score],
            "emotions": []
        }
        
        # Collect emotions from both sources
        all_emotions = []
        for checkin in checkins:
            all_emotions.extend(checkin.detected_emotions)
        
        for translation in translations:
            all_emotions.extend([insight.emotion for insight in translation.insights])
        
        # Count emotions
        emotion_counts = {}
        for emotion in all_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        data_summary["emotions"] = emotion_counts
        
        # Get child context if available
        child_context = ""
        if child_id and user:
            child = user.get_child(child_id)
            if child:
                child_context = f"Child: {child.name}, Age: {child.age.value}, Personality: {', '.join(child.personality_traits)}"
        
        # Generate prompt for AI analysis
        prompt = f"""You are a child psychology expert analyzing a week of emotional data for a family. 

CONTEXT:
{child_context}
User language: {user.language_code if user else 'en'}

DATA SUMMARY:
- Total check-ins: {data_summary['total_checkins']}
- Total emotion translations: {data_summary['total_translations']}
- Completed interactions: {data_summary['completed_checkins']}
- Mood scores this week: {data_summary['mood_scores']}
- Emotion frequencies: {json.dumps(data_summary['emotions'], indent=2)}

TASK:
Provide professional insights and recommendations in JSON format:

{{
    "insights": [
        "Key observation about emotional patterns",
        "Notable trends or changes",
        "Areas of strength or concern"
    ],
    "recommendations": [
        "Specific actionable recommendation for parents",
        "Suggested activities or approaches",
        "When to seek additional support if needed"
    ]
}}

Focus on:
1. Age-appropriate developmental insights
2. Practical parenting strategies
3. Emotional regulation support
4. Family connection opportunities
5. Warning signs that may need attention

Be supportive, evidence-based, and actionable in your recommendations."""
        
        try:
            # Call Claude API
            response = await self.claude_service.generate_completion(
                prompt=prompt,
                max_tokens=800,
                temperature=0.4
            )
            
            # Parse JSON response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                ai_analysis = json.loads(json_str)
                return {
                    "insights": ai_analysis.get("insights", []),
                    "recommendations": ai_analysis.get("recommendations", [])
                }
        
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
        
        # Fallback insights if AI fails
        return {
            "insights": [
                f"Recorded {len(checkins)} check-ins and {len(translations)} emotion translations this week",
                "Consistent emotional tracking helps build awareness and connection",
                "Regular patterns are emerging in emotional expression"
            ],
            "recommendations": [
                "Continue regular check-ins to maintain emotional awareness",
                "Celebrate positive emotional moments with your child",
                "Create safe spaces for expressing difficult feelings"
            ]
        }
    
    async def get_emotion_trends(
        self,
        user_id: UUID,
        child_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, any]:
        """Get emotion trends over specified period."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get data
        checkins = await self.checkin_repository.get_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            child_id=child_id
        )
        
        translations = await self.translation_repository.get_recent(
            user_id=user_id,
            days=days
        )
        
        if child_id:
            translations = [t for t in translations if t.child_id == child_id]
        
        # Analyze trends by day
        daily_data = {}
        
        # Process check-ins
        for checkin in checkins:
            if checkin.is_completed:
                day = checkin.completed_at.date() if checkin.completed_at else checkin.scheduled_at.date()
                if day not in daily_data:
                    daily_data[day] = {"mood_scores": [], "emotions": []}
                
                if checkin.mood_score:
                    daily_data[day]["mood_scores"].append(float(checkin.mood_score.value))
                daily_data[day]["emotions"].extend(checkin.detected_emotions)
        
        # Process translations
        for translation in translations:
            day = translation.created_at.date()
            if day not in daily_data:
                daily_data[day] = {"mood_scores": [], "emotions": []}
            
            if translation.mood_score:
                daily_data[day]["mood_scores"].append(float(translation.mood_score.value))
            daily_data[day]["emotions"].extend([insight.emotion for insight in translation.insights])
        
        # Calculate daily averages
        trend_data = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            avg_mood = sum(data["mood_scores"]) / len(data["mood_scores"]) if data["mood_scores"] else 0
            
            # Count emotions for this day
            emotion_counts = {}
            for emotion in data["emotions"]:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            trend_data.append({
                "date": day.isoformat(),
                "average_mood": avg_mood,
                "emotion_counts": emotion_counts,
                "total_interactions": len(data["mood_scores"]) + len(data["emotions"])
            })
        
        return {
            "period_days": days,
            "daily_trends": trend_data,
            "total_days_with_data": len(daily_data),
            "overall_mood_trend": self._calculate_mood_trend(trend_data)
        }
    
    def _calculate_mood_trend(self, trend_data: List[Dict]) -> str:
        """Calculate overall mood trend direction."""
        if len(trend_data) < 3:
            return "insufficient_data"
        
        # Compare first third vs last third
        third = len(trend_data) // 3
        early_scores = [d["average_mood"] for d in trend_data[:third] if d["average_mood"] != 0]
        late_scores = [d["average_mood"] for d in trend_data[-third:] if d["average_mood"] != 0]
        
        if not early_scores or not late_scores:
            return "insufficient_data"
        
        early_avg = sum(early_scores) / len(early_scores)
        late_avg = sum(late_scores) / len(late_scores)
        
        if late_avg > early_avg + 0.2:
            return "improving"
        elif late_avg < early_avg - 0.2:
            return "declining"
        else:
            return "stable"
    
    async def get_family_overview(self, user_id: UUID) -> Dict[str, any]:
        """Get overall family emotional overview."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise DomainException("User not found")
        
        # Get data for all children
        family_data = {
            "user_id": str(user_id),
            "total_children": len(user.children),
            "children": []
        }
        
        for child in user.children:
            # Get child's recent data
            child_trends = await self.get_emotion_trends(
                user_id=user_id,
                child_id=child.id,
                days=7
            )
            
            child_data = {
                "child_id": str(child.id),
                "name": child.name,
                "age": child.age.value,
                "recent_mood_trend": child_trends["overall_mood_trend"],
                "days_with_data": child_trends["total_days_with_data"]
            }
            
            family_data["children"].append(child_data)
        
        return family_data