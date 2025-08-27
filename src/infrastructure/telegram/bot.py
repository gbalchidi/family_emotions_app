"""Main Telegram Bot class for Family Emotions App."""
from __future__ import annotations

import logging
from typing import Dict, Optional
from uuid import uuid4

from telegram.ext import Application, ContextTypes
from telegram import Bot, Update

from .states import ConversationStates, UserContext
from ...core.config import settings
from ...core.services import UserService, FamilyService, AnalyticsService
from ...infrastructure.external import EmotionService

logger = logging.getLogger(__name__)


class FamilyEmotionsBot:
    """Main bot class that coordinates all bot functionality."""
    
    def __init__(
        self,
        user_service: Optional[UserService] = None,
        family_service: Optional[FamilyService] = None,
        emotion_service: Optional[EmotionService] = None,
        analytics_service: Optional[AnalyticsService] = None
    ):
        self.user_service = user_service
        self.family_service = family_service
        self.emotion_service = emotion_service
        self.analytics_service = analytics_service
        
        # User conversation contexts
        self.user_contexts: Dict[int, UserContext] = {}
        
        # Database manager (injected by main app)
        self.db_manager = None
        
        # Create application
        self.application = Application.builder().token(settings.telegram.bot_token).build()
        
        # Setup handlers will be called from setup_handlers function
        
    def get_user_context(self, user_id: int):
        """Get or create user context for conversation state management."""
        if user_id not in self.user_contexts:
            from .states import UserContext
            context = UserContext()
            context.session_id = str(uuid4())
            self.user_contexts[user_id] = context
        
        return self.user_contexts[user_id]
    
    def clear_user_context(self, user_id: int):
        """Clear user context (e.g., on /start or error)."""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
    
    async def get_user_service(self):
        """Get UserService with database session."""
        if not self.db_manager:
            return None
            
        from ...core.services import UserService
        # Get a raw session for the service (it will manage the session lifecycle)
        session = await self.db_manager.get_raw_session()
        return UserService(session)
    
    async def get_or_create_user(self, update: Update) -> Optional[tuple]:
        """
        Get or create user from Telegram update.
        
        Returns:
            Tuple of (User, is_new_user) or None if error
        """
        try:
            telegram_user = update.effective_user
            if not telegram_user:
                return None
            
            if not self.db_manager:
                return None
                
            # Use context manager to ensure session cleanup
            async with self.db_manager.get_session() as session:
                from ...core.services import UserService
                user_service = UserService(session)
                
                # Try to get existing user with children loaded
                user = await user_service.get_user_by_telegram_id(telegram_user.id)
                
                if user:
                    # Make sure relationships are loaded
                    await session.refresh(user)
                    return user, False
                
                # Create new user
                user = await user_service.create_user(
                    telegram_id=telegram_user.id,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    username=telegram_user.username,
                    language_code=telegram_user.language_code or "en"
                )
                
                # Track new user registration (if analytics service available)
                if self.analytics_service:
                    await self.analytics_service.track_event(
                        event_type="user_registration",
                        user_id=user.id,
                        user_telegram_id=user.telegram_id,
                        event_data={
                            "username": user.username,
                            "language": user.language_code,
                            "registration_source": "telegram"
                        }
                    )
                
                logger.info(f"Created new user: {user.id} (Telegram ID: {telegram_user.id})")
                return user, True
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}")
            return None
    
    async def send_typing_action(self, context: ContextTypes.DEFAULT_TYPE):
        """Send typing action to show bot is working."""
        try:
            await context.bot.send_chat_action(
                chat_id=context._chat_id,
                action="typing"
            )
        except Exception as e:
            logger.warning(f"Failed to send typing action: {e}")
    
    async def handle_error(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        error_msg: str = "An error occurred. Please try again."
    ):
        """Handle and log errors, send user-friendly message."""
        try:
            logger.error(f"Bot error: {error_msg}")
            
            # Track error analytics
            user_id = None
            telegram_id = None
            
            if update and update.effective_user:
                telegram_id = update.effective_user.id
                user_result = await self.get_or_create_user(update)
                if user_result:
                    user_id = user_result[0].id
            
            # Track error analytics (if service available)
            if self.analytics_service:
                await self.analytics_service.track_event(
                    event_type="error_occurred",
                    user_id=user_id,
                    user_telegram_id=telegram_id,
                    error_code="BOT_ERROR",
                    error_message=error_msg
                )
            
            # Send error message to user
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ {error_msg}\n\nPlease try again or use /help for assistance.",
                    parse_mode="HTML"
                )
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def format_user_greeting(self, user, is_new_user: bool) -> str:
        """Format greeting message for user."""
        if is_new_user:
            return f"""
👋 <b>Welcome to Family Emotions App, {user.first_name}!</b>

I'm here to help you understand and respond to your child's emotions better.

🌟 <b>What I can do:</b>
• Translate your child's emotional expressions
• Provide age-appropriate response suggestions
• Generate weekly emotional development reports
• Track emotional patterns and growth

📚 <b>Getting Started:</b>
1. Add your children to your family profile
2. Start translating emotions by describing situations
3. Review weekly insights and recommendations

Let's begin by setting up your family profile!

Use the menu below to get started 👇
"""
        else:
            # Get user stats for returning user
            return f"""
👋 <b>Welcome back, {user.first_name}!</b>

What would you like to do today?

📊 <b>Quick Stats:</b>
• Subscription: {user.subscription_status.value.title()}
• Daily requests used: {user.daily_requests_count}
• Children in profile: {len(user.children)}

Use the menu below to continue 👇
"""
    
    async def format_emotion_translation_result(
        self, 
        translation, 
        child_name: str = "your child"
    ) -> str:
        """Format emotion translation results for display."""
        if not translation.translated_emotions:
            from ...core.localization.translator import _
            return f"❌ <b>{_('emotion_translation.limits.translation_failed')}</b>\n\n{_('emotion_translation.limits.translation_failed_description')}"
        
        emotions_text = ", ".join(translation.translated_emotions)
        confidence_text = f"{translation.confidence_score * 100:.0f}%"
        
        result = f"""
🎯 <b>Emotion Analysis Complete</b>

👶 <b>Child:</b> {child_name}
🎭 <b>Detected Emotions:</b> {emotions_text}
📊 <b>Confidence:</b> {confidence_text}

💡 <b>Suggested Responses:</b>
"""
        
        for i, response in enumerate(translation.response_options, 1):
            result += f"\n<b>{i}. {response['title']}</b>\n"
            result += f"<i>{response['text']}</i>\n"
            result += f"<code>Approach: {response['approach']}</code>\n"
        
        result += f"\n⏱️ <i>Processed in {translation.processing_time_ms}ms</i>"
        
        return result
    
    async def format_child_profile(self, child) -> str:
        """Format child profile information."""
        profile = f"""
👶 <b>{child.name}</b>

📅 <b>Age:</b> {child.age} years old
"""
        
        if child.birth_date:
            profile += f"🎂 <b>Birthday:</b> {child.birth_date.strftime('%B %d, %Y')}\n"
        
        if child.gender:
            profile += f"🧬 <b>Gender:</b> {child.gender.title()}\n"
        
        if child.personality_traits:
            profile += f"\n🌟 <b>Personality:</b>\n{child.personality_traits}\n"
        
        if child.interests:
            profile += f"\n🎨 <b>Interests:</b>\n{child.interests}\n"
        
        if child.special_needs:
            profile += f"\n🔍 <b>Special Considerations:</b>\n{child.special_needs}\n"
        
        profile += f"\n📊 <b>Profile created:</b> {child.created_at.strftime('%B %d, %Y')}"
        
        return profile
    
    async def format_usage_stats(self, user) -> str:
        """Format user usage statistics."""
        # Get user activity stats
        stats = await self.analytics_service.get_user_activity_stats(user.id, days=30)
        
        usage_text = f"""
📊 <b>Your Usage Statistics (Last 30 Days)</b>

💳 <b>Subscription:</b> {user.subscription_status.value.title()}
📅 <b>Daily Limit:</b> {user.daily_requests_count}/{'50' if user.subscription_status.value == 'premium' else '5'}

🎯 <b>Translations:</b>
• Total: {stats['translations']['total']}
• Success Rate: {stats['translations']['success_rate']:.1f}%
• Avg Speed: {stats['translations']['avg_processing_time_ms']:.0f}ms

✅ <b>Check-ins:</b>
• Completed: {stats['checkins']['completed']}/{stats['checkins']['total']}
• Completion Rate: {stats['checkins']['completion_rate']:.1f}%
• Average Mood: {stats['checkins']['avg_mood_score']:.1f}/5

📈 <b>Most Active Features:</b>
"""
        
        for event_type, count in list(stats['event_counts'].items())[:3]:
            usage_text += f"• {event_type.replace('_', ' ').title()}: {count}\n"
        
        return usage_text
    
    async def run_polling(self):
        """Start the bot with polling."""
        logger.info("Starting Family Emotions Bot with polling...")
        await self.application.run_polling(
            allowed_updates=["message", "callback_query", "inline_query"]
        )
    
    async def run_webhook(self):
        """Start the bot with webhook."""
        if not settings.telegram.webhook_url:
            raise ValueError("Webhook URL not configured")
            
        logger.info(f"Starting Family Emotions Bot with webhook: {settings.telegram.webhook_url}")
        await self.application.run_webhook(
            listen="0.0.0.0",
            port=8000,
            webhook_url=settings.telegram.webhook_url,
            secret_token=settings.telegram.webhook_secret
        )
    
    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping Family Emotions Bot...")
        self.application.stop()


def create_bot(emotion_analyzer) -> Application:
    """Create and configure the Telegram bot application."""
    from ...application.emotion_analyzer import EmotionAnalyzer
    from ...core.services import UserService, FamilyService, AnalyticsService
    from ...infrastructure.external import EmotionService
    
    # TODO: Get these services from dependency injection container
    # For now, create basic instances - this needs to be properly implemented
    logger.warning("Creating bot with temporary service instances - implement proper DI")
    
    # Create bot application
    application = Application.builder().token(settings.telegram.bot_token).build()
    
    return application


def setup_bot_commands(application: Application, bot_instance=None):
    """Setup bot commands and handlers."""
    from .handlers import setup_handlers
    
    # Store the bot instance in bot_data for handlers to access
    if bot_instance:
        application.bot_data['bot_instance'] = bot_instance
    
    # Setup conversation handlers
    setup_handlers(application)
    
    logger.info("Bot commands and handlers configured successfully")