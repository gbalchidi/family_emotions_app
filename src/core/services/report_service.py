"""Report service for generating weekly emotion reports."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User, Children
from ..models.emotion import EmotionTranslation, Checkin, WeeklyReport, TranslationStatus
from ..exceptions import ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating and managing emotion reports."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_weekly_report_data(
        self, 
        user_id: UUID, 
        weeks_back: int = 0
    ) -> Dict:
        """
        Get weekly report data for a user.
        
        Args:
            user_id: User UUID
            weeks_back: How many weeks back (0 = current week, 1 = last week)
            
        Returns:
            Dict with report data
        """
        # Calculate week boundaries
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday() + (7 * weeks_back))
        week_end = week_start + timedelta(days=6)
        
        logger.info(f"Generating report for week {week_start} to {week_end}")
        
        # Convert to datetime for database queries
        week_start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        week_end_dt = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Get user and children
        user_stmt = (
            select(User)
            .where(User.id == user_id)
        )
        user_result = await self._session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ResourceNotFoundError(f"User {user_id} not found")
        
        # Get children
        children_stmt = (
            select(Children)
            .where(Children.parent_id == user_id)
        )
        children_result = await self._session.execute(children_stmt)
        children = list(children_result.scalars().all())
        
        # Get emotion translations for the week
        translations_stmt = (
            select(EmotionTranslation)
            .where(
                and_(
                    EmotionTranslation.user_id == user_id,
                    EmotionTranslation.created_at >= week_start_dt,
                    EmotionTranslation.created_at <= week_end_dt,
                    EmotionTranslation.status == TranslationStatus.COMPLETED
                )
            )
        )
        translations_result = await self._session.execute(translations_stmt)
        translations = list(translations_result.scalars().all())
        
        logger.info(f"Found {len(translations)} completed translations for user {user_id} in week {week_start} to {week_end}")
        
        # Also check for ANY translations (regardless of status) for debugging
        all_translations_stmt = (
            select(EmotionTranslation)
            .where(
                and_(
                    EmotionTranslation.user_id == user_id,
                    EmotionTranslation.created_at >= week_start_dt,
                    EmotionTranslation.created_at <= week_end_dt
                )
            )
        )
        all_translations_result = await self._session.execute(all_translations_stmt)
        all_translations = list(all_translations_result.scalars().all())
        
        logger.info(f"Found {len(all_translations)} total translations (any status) for user {user_id}")
        if all_translations:
            for trans in all_translations:
                logger.info(f"Translation {trans.id}: status={trans.status}, created_at={trans.created_at}, emotions={trans.translated_emotions}")
        
        # Get checkins for the week
        checkins_stmt = (
            select(Checkin)
            .where(
                and_(
                    Checkin.user_id == user_id,
                    Checkin.created_at >= week_start_dt,
                    Checkin.created_at <= week_end_dt,
                    Checkin.is_completed == True
                )
            )
        )
        checkins_result = await self._session.execute(checkins_stmt)
        checkins = list(checkins_result.scalars().all())
        
        # Process data
        emotion_counts = {}
        child_activity = {}
        daily_activity = {i: 0 for i in range(7)}  # 0=Monday, 6=Sunday
        
        # Process translations
        for translation in translations:
            if translation.translated_emotions:
                for emotion in translation.translated_emotions:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Count activity per child
            if translation.child_id:
                child_name = next((c.name for c in children if c.id == translation.child_id), "Unknown")
                child_activity[child_name] = child_activity.get(child_name, 0) + 1
            
            # Count daily activity
            weekday = translation.created_at.weekday()
            daily_activity[weekday] += 1
        
        # Calculate mood trends from checkins
        mood_scores = [c.mood_score for c in checkins if c.mood_score is not None]
        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else None
        
        # Generate insights
        insights = []
        if len(translations) > 0:
            top_emotion = max(emotion_counts.items(), key=lambda x: x[1]) if emotion_counts else None
            if top_emotion:
                insights.append(f"Самая частая эмоция: {top_emotion[0]} ({top_emotion[1]} раз)")
        
        if len(translations) >= 5:
            insights.append("Отличная активность! Вы активно анализируете эмоции детей.")
        elif len(translations) >= 2:
            insights.append("Хорошее начало! Продолжайте анализировать эмоции регулярно.")
        else:
            insights.append("Попробуйте анализировать эмоции детей чаще для лучших результатов.")
        
        if avg_mood:
            if avg_mood > 0.3:
                insights.append("Настроение семьи в целом позитивное! 😊")
            elif avg_mood < -0.3:
                insights.append("Возможно, стоит уделить больше внимания эмоциональной поддержке.")
            else:
                insights.append("Эмоциональное состояние стабильное.")
        
        # Generate recommendations
        recommendations = []
        if len(translations) < 3:
            recommendations.append("Попробуйте анализировать эмоции детей каждый день")
        if len(children) > len(child_activity):
            recommendations.append("Уделите внимание эмоциям всех детей равномерно")
        if not checkins:
            recommendations.append("Попробуйте функцию ежедневных проверок настроения")
        
        recommendations.append("Обсуждайте с детьми их эмоции открыто и без осуждения")
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'user_name': user.first_name,
            'children_count': len(children),
            'children_names': [c.name for c in children],
            'translations_count': len(translations),
            'checkins_count': len(checkins),
            'emotion_counts': emotion_counts,
            'child_activity': child_activity,
            'daily_activity': daily_activity,
            'average_mood': avg_mood,
            'insights': insights,
            'recommendations': recommendations
        }
    
    async def format_weekly_report(self, user_id: UUID, weeks_back: int = 0) -> str:
        """Format weekly report as text for Telegram."""
        try:
            data = await self.get_weekly_report_data(user_id, weeks_back)
            
            # Format week period
            week_period = "текущая неделя" if weeks_back == 0 else f"{weeks_back} недел{'я' if weeks_back == 1 else ('и' if weeks_back < 5 else 'ь')} назад"
            
            report = f"""
📊 <b>Еженедельный отчет ({week_period})</b>
📅 {data['week_start'].strftime('%d.%m')} - {data['week_end'].strftime('%d.%m.%Y')}

👋 <b>Привет, {data['user_name']}!</b>

📈 <b>Активность за неделю:</b>
• Анализов эмоций: {data['translations_count']}
• Ежедневных проверок: {data['checkins_count']}
• Детей в семье: {data['children_count']}
"""
            
            # Add children activity
            if data['child_activity']:
                report += "\n👶 <b>Активность по детям:</b>\n"
                for child_name, count in data['child_activity'].items():
                    report += f"• {child_name}: {count} анализов\n"
            
            # Add top emotions
            if data['emotion_counts']:
                report += "\n🎭 <b>Топ эмоций:</b>\n"
                sorted_emotions = sorted(data['emotion_counts'].items(), key=lambda x: x[1], reverse=True)[:5]
                for emotion, count in sorted_emotions:
                    report += f"• {emotion}: {count} раз\n"
            
            # Add mood info
            if data['average_mood'] is not None:
                mood_emoji = "😊" if data['average_mood'] > 0.3 else ("😐" if data['average_mood'] > -0.3 else "😔")
                mood_text = f"{data['average_mood']:.1f}"
                report += f"\n💭 <b>Среднее настроение:</b> {mood_text} {mood_emoji}\n"
            
            # Add insights
            if data['insights']:
                report += "\n💡 <b>Наблюдения:</b>\n"
                for insight in data['insights'][:3]:
                    report += f"• {insight}\n"
            
            # Add recommendations
            if data['recommendations']:
                report += "\n🌟 <b>Рекомендации:</b>\n"
                for rec in data['recommendations'][:3]:
                    report += f"• {rec}\n"
            
            report += f"\n<i>Отчет за период {data['week_start'].strftime('%d.%m')} - {data['week_end'].strftime('%d.%m.%Y')}</i>"
            
            return report
            
        except Exception as e:
            logger.error(f"Error formatting weekly report: {e}")
            return f"""
📊 <b>Еженедельный отчет</b>

❌ <b>Ошибка при генерации отчета</b>

К сожалению, не удалось сгенерировать отчет. Попробуйте позже или обратитесь в поддержку.

<i>Для генерации отчетов нужны данные об анализе эмоций за последние дни.</i>
"""